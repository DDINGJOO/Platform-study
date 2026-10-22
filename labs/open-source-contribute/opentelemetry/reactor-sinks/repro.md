# repro: Hooks.resetOnEachOperator() 뒤 Reactor 컨텍스트 전파가 사라진다 (javaagent)

환경: main `079a5af0e2`, JDK 25.0.4, Gradle `--no-daemon --max-workers=2 -Dorg.gradle.jvmargs=-Xmx2g -Ddev=true`. 기본 의존성(reactor-core 3.1.0.RELEASE, javaagent `test`).

## 재현 방법
에이전트가 붙은 JVM 에서 앱 코드가 `Hooks.resetOnEachOperator()` 를 부른 뒤, 외부 구동 publisher(`Flux.create`)에 subscribe 시점 컨텍스트가 전달되는지 본다. 훅이 살아 있으면 구독 콜백에서 subscribe 시점의 컨텍스트 키가 보이고, 없으면 `null`.

## 수정 전 (본 코드 main)
- 탐색 테스트: baseline `subscribe-time`, 무관한 키 reset 후 `subscribe-time`, reset-all 후 `null` (`logs/02-explore-hooks-reset.log`, 9s).
- 회귀 테스트 `HooksResetTest`: `exit=1 elapsed=29s`, 2개 중 1개 실패(`contextIsPropagatedAfterResettingAllOnEachOperatorHooks`). `logs/05-before-fail.log`, `logs/05-before-fail-TEST-HooksResetTest.xml`.

## 수정 후
- `HooksResetTest`: `exit=0 elapsed=10s`, `tests="2" failures="0"`. `logs/06-after-pass.log`, `logs/06-after-pass-TEST-HooksResetTest.xml`.
- 첫 수정 시도(바깥 클래스의 private 헬퍼 공유)는 `LinkageError` 로 3개 전부 실패. `logs/06a-after-attempt1-linkageerror.log`.

## 본 코드만 되돌림 (테스트 유지)
- `exit=1 elapsed=8s`, 2개 중 1개 실패(같은 테스트). `logs/07-revert-fail.log`, `logs/07-revert-fail-TEST-HooksResetTest.xml`.

## 관련 모듈 테스트 (수정 후)
`:instrumentation:reactor:reactor-3.1:` `javaagent:test`, `javaagent:testInitialization`, `javaagent:version34Test`, `library:test` + `javaagent:spotlessApply`: `exit=0 elapsed=38s`. 실패 0.

| 소스셋 | tests | skipped | failures |
|---|---|---|---|
| javaagent test | 59 | 0 | 0 |
| javaagent testInitialization | 1 | 0 | 0 |
| javaagent version34Test | 3 | 0 | 0 |
| library test | 60 | 1 | 0 |

`logs/08-module-tests.log`, `logs/08-junit-xml/`. 최신 의존성(`-PtestLatestDeps=true`)으로 `HooksResetTest`, `testInitialization`: 통과(`logs/09-latestdeps.log`, 74s). 해석된 reactor-core 버전은 확인 안 함.

## 확인 안 함
전체 `check`, 다른 모듈 테스트, muzzle, 실제 앱에서의 동작.

---

# repro: Sinks (버그로 보지 않음)

환경: javaagent `version34Test`, reactor-core 3.4.0, 같은 JDK/Gradle 옵션.

| 구성 | 구독 콜백이 본 subscribe 시점 컨텍스트 |
|---|---|
| `Sinks.many().unicast().asFlux().subscribe(l)` | 없음(null) |
| `... .asFlux().map(..).subscribe(l)` | 있음 |
| `... .asFlux().doOnNext(..).subscribe(l)` | 있음 |
| `Sinks.one().asMono().subscribe(l)` | 없음(null) |
| `Sinks.one().asMono().map(..).subscribe(l)` | 있음 |
| `Flux.create(..).subscribe(l)` (대조군) | 있음 |

`logs/01-explore-sinks-v34.log`(51s), 소스 `logs/01-SinksExploreTest.java.txt`.
