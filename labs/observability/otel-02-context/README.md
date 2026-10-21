# OTel 2편: Context 소스 확인 기록

블로그 원고의 공개 소스와 캡처 범위를 기록한다. 이 디렉터리는 소스 확인 근거이며 실행 실험이나 성능 측정 결과를 담지 않는다. 별도 런타임 실험은 `../otel-runtime-probes/`에서 관리하고, 실제 결과를 확인한 경우에만 본문에 인용한다.

- 저장소: `open-telemetry/opentelemetry-java`
- 태그: `v1.67.0`
- 커밋: `b4b3a1b354425c3f1411173c0e48cb24a1cba224`
- 문서 확인일: 2026-10-21
- 소스 라이선스: Apache-2.0. Context.java는 파일 헤더에 gRPC 기여의 라이선스 고지도 포함한다.
- 원본 소스는 읽기 전용으로 취급했다. 캡처는 원문을 변경하지 않은 로컬 코드 뷰어 렌더링이며 GitHub 화면 캡처가 아니다.

## 확인한 코드

| 원본 | 확인 내용 |
|---|---|
| Context.java 90~94행 | 현재 저장소에 값이 없으면 root를 사용한다. |
| Context.java 108~143행 | taskWrapping은 execute/submit 호출 시점의 현재 문맥을 확보한다. Context 인스턴스의 wrap과 캡처 시점이 다르다. |
| Context.java 230~245행 | makeCurrent는 attach를 호출한다. wrap은 반환한 Runnable의 실행 범위에서 부착과 Scope close를 처리한다. |
| ArrayBasedContext.java 54~85행 | 기본 Context는 동일성으로 키를 찾고, 변경 시 배열 복제·확장으로 갱신 결과를 만든다. 같은 키에 같은 값 객체면 기존 객체를 반환한다. |
| ThreadLocalContextStorage.java 17~35행 | 기본 저장소의 현재 값을 읽고 새 값을 설정하며, 복원할 이전 값을 ScopeImpl에 보관한다. |
| ThreadLocalContextStorage.java 47~58행 | 미종료 Scope이고 현재 값이 부착했던 값과 같은 경우 이전 값을 복원한다. 잘못된 순서에서는 그대로 복원하지 않는다. |
| ContextStorage.java 75~80행 | defaultStorage가 ThreadLocalContextStorage를 반환한다. 다른 저장소·wrapper 사용 가능성은 별개다. |
| LazyStorage.java 78~121행 | 저장소 초기화 시 provider 선택, 엄격 검사와 wrapper 적용을 한다. provider가 없으면 기본 저장소를 사용한다. |
| CurrentContextExecutorService.java 23~66행 | submit/execute에서 현재 Context를 읽고 작업을 감싼다. |
| CurrentContextScheduledExecutorService.java 23~42행 | 일회성 예약은 감싸지만 fixed-rate/fixed-delay 반복 예약은 원래 command를 위임한다. |

캡처 명세와 원본 파일 SHA-256은 [source-manifest.json](source-manifest.json)에 있다. 공통 캡처 도구는 시리즈 통합 담당자가 `posts/CS/Observability/otel/images/02`를 출력 디렉터리로 지정해 실행한다. `threadlocal-scope.png`는 부착 부분만 보여 준다. 복원 설명은 이미지 밖의 별도 원문인 [ThreadLocalContextStorage.java 47~58행](https://github.com/open-telemetry/opentelemetry-java/blob/b4b3a1b354425c3f1411173c0e48cb24a1cba224/context/src/main/java/io/opentelemetry/context/ThreadLocalContextStorage.java#L47-L58)으로 확인했다.

## 문서

- [Context 사양](https://opentelemetry.io/docs/specs/otel/context/): 불변성, attach와 detach의 대응 관계.
- [Java Context API](https://opentelemetry.io/docs/languages/java/api/#context-api): ContextStorage의 기본 구현 및 ContextPropagators와의 구분.
- [Java Span API](https://opentelemetry.io/docs/languages/java/api/#span): 명시적으로 재지정하지 않은 새 스팬의 부모 선택.
- [Reactor Context](https://projectreactor.io/docs/core/release/reference/advancedFeatures/context.html): 각 Subscriber에 연결되는 불변 문맥, 구독 시점과 downstream→upstream 전달. 2026-10-21 조회 시 Reference Guide 3.8.7.
- [Reactor Context-Propagation](https://projectreactor.io/docs/core/release/reference/advanced-contextPropagation.html): 등록한 accessor와 문맥의 값을 기준으로 한 ThreadLocal 연동, 제한 모드와 자동 모드의 구분 및 성능 영향.
- [Go context](https://pkg.go.dev/context): 첫 인자 명시적 전달, 취소·deadline 계약, 여러 goroutine에서의 동시 사용. Java Scope close와 Go cancel을 동일한 정리 동작으로 취급하지 않는다.
- [OTel Go 계측](https://opentelemetry.io/docs/languages/go/instrumentation/#creating-spans): 표준 Context와 OTel 계측의 조합. Go Context를 OTel의 전체 대체품으로 설명하지 않는다.

## 확인하지 않은 것

- 이 원고의 설명용 Java/Reactor/Go 예제 전체를 컴파일·실행하지 않았다.
- Java 에이전트, Reactor, Kotlin coroutine, HTTP 헤더 전파 구현을 재현하지 않았다.
- 소스 독해로 관찰한 동작을 모든 비동기 프레임워크의 자동 전파 보장으로 확대하지 않는다.
- 로컬 PNG 상대 경로는 발행 시 이미지 업로드 처리가 필요하다. 업로더 sync나 공개 발행은 실행하지 않았다.

## 별도 실행 기록을 반영한 범위

원고 8장에는 [공통 실험 코드](../otel-runtime-probes/RuntimeProbes.java), [실제 표준 출력](../otel-runtime-probes/actual.txt), [검증 기록](../otel-runtime-probes/validation.json)을 직접 대조해 컨텍스트 실험만 인용했다.

- 공개 Maven 1.67.0 아티팩트, JAR SHA-256 검증, OpenJDK 25.0.3, javac `--release 11`.
- 단일 작업 스레드에 `worker-baseline`을 유지한다. 별도 문맥에서 만든 wrapped Runnable이 `captured`를 읽고 의도한 예외를 던진 다음, 같은 스레드 객체에서 baseline 복원을 확인한다. 호출 스레드의 원래 Context 객체 복원도 검사한다.
- Context 실험은 별도 JVM 다섯 번에서 종료 코드 0, 출력 동일, 표준 오류 없음으로 기록됐다.
- 원고는 `actual.txt`의 Context 부분 일곱 줄만 그대로 인용한다. Scope 오사용, taskWrapping 전체 overload, 스팬 부모·자식 관계, 네트워크 전파, Reactor·Go 실행을 검증한 실험으로 확대하지 않는다.
