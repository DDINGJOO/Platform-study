# analysis

## 결론
- H2(에이전트에서 reset-all 뒤 훅이 사라지고 복구되지 않음): **버그, 수정함.**
- H1(Sinks): 연산자 없이 직접 subscribe 하면 컨텍스트가 안 붙는 것은 재현됐지만 계측 설계상의 한계로 보고 고치지 않음. 이슈 보고 여부는 사람이 결정.
- H3(여러 operator 인스턴스의 strategy 잔존): 기계적으로 재현, 영향 작아 고치지 않음.

## H2 원인
- `javaagent/.../HooksInstrumentation.java`: `isTypeInitializer().or(named("resetOnEachOperator"))` 에 `ResetOnEachOperatorAdvice` 를 달고, 메서드 끝에서 `ContextPropagationOperator.builder()...build().registerOnEachOperator()` 를 부른다. 의도는 앱이 훅을 지워도(`Hooks.resetOnEachOperator()`) 다시 설치하는 것이다.
- `library/.../ContextPropagationOperator.java` 의 `registerOnEachOperator()` 는 `if (enabled) return;` 으로 시작한다. `enabled` 는 static 이고 이 클래스의 `register`/`reset` 만 바꾼다. 앱이 Reactor 의 `Hooks.resetOnEachOperator()` 를 직접 부르면 Reactor 안에서 훅이 지워지지만 `enabled` 는 true 로 남아서 위 재등록이 무시된다.
- 키 있는 `Hooks.resetOnEachOperator(String)` 에도 같은 advice 가 붙어 있었다(`named("resetOnEachOperator")` 가 오버로드를 가리지 않음). 우리 훅을 라이브러리 `ContextPropagationOperator.resetOnEachOperator()` 로 제거하는 경로에서는 `enabled` 가 true 인 채 재진입하여 no-op 이라 의도대로 동작하고 있었다.
- Reactor 쪽 근거: Reactor 의 `Hooks.resetOnEachOperator()` 가 모든 onEachOperator 훅을 지운다는 점은 탐색 테스트 결과(reset-all 후 컨텍스트 소실)로만 확인했다. Reactor 소스·문서는 직접 열어 보지 않았다(확인 안 함).

## 수정
- 인자 0개인 `resetOnEachOperator` 에만 새 advice(`ResetAllOnEachOperatorAdvice`)를 단다. 거기서 operator 의 `resetOnEachOperator()` 로 `enabled` 를 내리고(키 있는 reset 호출, strategy 해제, scheduler 훅 해제 포함) 바로 `registerOnEachOperator()` 로 다시 설치한다.
- 기존 advice 는 type initializer 와 키 있는 오버로드에만 남긴다(동작 변화 없음).
- 새 공개 API 없음. 라이브러리 코드 변경 없음.
- 고려한 대안과 버린 이유:
  - `registerOnEachOperator()` 의 `enabled` 가드 제거: Reactor 훅과 scheduler 훅은 키로 교체되어 멱등이지만 `AsyncOperationEndStrategies.registerStrategy` 는 리스트에 계속 추가(`CopyOnWriteArrayList.add`)하고, type initializer advice 가 `Flux`/`Mono`/`Hooks` 에서 여러 번 호출되므로 strategy 가 쌓인다.
  - 라이브러리에 "훅이 지워짐" 을 알리는 public 메서드 추가: 공개 alpha API 를 늘려야 해서 피함.
- 알려진 한계: reset-all 때 advice 가 만든 operator 인스턴스는 최초 등록 인스턴스와 다르므로 이전 인스턴스의 strategy 는 레지스트리에 남는다. 에이전트의 `WeakRefAsyncOperationEndStrategies` 는 약한 참조라 이전 strategy 는 `Lifter` 가 사라지면 수거될 것으로 예상하지만, 실제 수거는 확인 안 함(`WeakRefAsyncOperationEndStrategies` 구현을 읽지 않음).
- 함정(기록용): `inline = false` advice 가 바깥 클래스의 private static 메서드를 부르면 `LinkageError`(loader constraint violation). advice 는 자체 완결이어야 한다.

## H1 근거
- `logs/01-explore-sinks-v34.log`. 표는 `repro.md`.
- 가설일 뿐인 원인: `Sinks` 의 `asFlux()`/`asMono()` 결과는 `onAssembly` 를 거치지 않아 `Hooks.onEachOperator` lift 대상이 아니다. Reactor 소스로 확인하지 않았다.
- 대안(시도 안 함): `Hooks.onLastOperator` 로 subscribe 지점에서 래핑. 모든 체인에 래핑이 하나 더 붙는 설계 변경이라 메인테이너 합의 없이 고치지 않음.
- 위 결과가 "의도된 동작" 인지는 메인테이너 의견을 못 들었다(확인 안 함).

## H3 근거
- `logs/03-explore-multi-instance.log`: A.register 후 B(미등록).reset 을 부르면 훅은 지워지는데(코드상) A 의 strategy 는 `AsyncOperationEndStrategies` 에 남아 `resolveStrategy(Mono.class)` 가 계속 non-null.
- 원인: `enabled`/훅 키는 static 인데 strategy 는 인스턴스 필드(`asyncOperationEndStrategy`)라 `unregisterStrategy` 가 호출한 인스턴스의 것만 지운다.
- 이번에 고치지 않은 이유: 오용(등록하지 않은 인스턴스에서 reset)이 필요하고 영향이 `@WithSpan` 이 `Mono`/`Flux` 를 반환할 때 strategy 가 남는 정도다. 별도 PR 거리로 남김.

## #20643 과의 관계 (읽기만)
- `logs/04-pr20643.diff`. `HooksInstrumentation`, `registerOnEachOperator`/`resetOnEachOperator` 본문, `enabled` 가드, Sinks 를 건드리지 않는다. H1·H2·H3 어느 것도 해결하지 않고, 내 수정은 그 PR 이 바꾸는 파일과 겹치지 않는다. 같은 모듈이라 리베이스 충돌은 없을 것으로 예상하지만 병합을 시도하지는 않았다.
