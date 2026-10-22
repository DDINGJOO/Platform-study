# analysis: 왜 sync 타임아웃이 성공 span 이 되는가

기준: main `079a5af0e2`(2026-10-22), 비교 `v2.32.0`(`1b8644f8eb`). 확인하지 않은 것은 "확인 안 함".

## 한 줄 원인
Lettuce 의 sync 프록시는 타임아웃이 나면 명령을 `cancel(true)` 하고 `RedisCommandTimeoutException` 을 호출자에게만 던진다(Lettuce `Futures.awaitOrCancel`, main 소스를 읽음. 어느 릴리스부터인지는 확인 안 함). 명령 future 가 보는 것은 `CancellationException` 이다. javaagent 의 `lettuce-5.0` 모듈은 `CancellationException` 을 "에러 아님" 으로 보고 `throwable = null` 로 span 을 끝낸다. 3.0(main) 에서는 5.1+ 도 이 모듈이 맡는다.

## 코드 위치
- `instrumentation/lettuce/lettuce-5.0/javaagent/src/main/java/io/opentelemetry/javaagent/instrumentation/lettuce/v5_0/EndCommandAsyncBiFunction.java:47-52` — `if (throwable instanceof CancellationException) { ... throwable = null; }` 후 `instrumenter().end(context, command, null, throwable)`. 주석 "and don't report this as an error". `git blame`: 2021-05-31 `7d46c336b0` (#3125 Update lettuce-5.0 to Instrumenter API).
- 같은 처리: `LettuceBatchContext.java:119-124`(배치), `EndConnectAsyncBiFunction.java:42`, `LettuceMasterSlaveInstrumentation.java:129`.
- span 종료 연결: `LettuceEndpointInstrumentation.java:91` `asyncCommand.handleAsync(new EndCommandAsyncBiFunction<>(context, command))`(#19055 배치 지원, 2026-06-25 에서 span 시작이 `DefaultEndpoint.write` 로 옮겨진 구조).
- 비교: 2.32.0 의 5.1+ 에이전트(`lettuce-5.1/javaagent`)는 라이브러리의 `OpenTelemetryTracing` 을 `ClientResources` 에 넣는 방식이었다. 6.0+ 에서는 `CompleteableCommand.onComplete((o, throwable)...)` 가 `CancellationException` 을 그대로 `instrumenter.end` 에 넘겨 에러가 된다(main 의 `OpenTelemetryTracing.java:210-218, 299-310`, 라이브러리 최신 의존성 결과 05: `error.type=CancellationException`).
- 5.1.0 에서의 UNSET: 5.1.0 Tracing SPI 는 취소 때 예외 없이 `finish()` 만 부르므로 라이브러리와 2.x 에이전트 모두 UNSET(07, 12 로그). 이건 3.0 이전부터 있던 한계다.

## 회귀 커밋 후보
- **`790251c3a5` Remove Lettuce 5.1 javaagent module (#20533, 2026-10-13)**: `lettuce-5.1/javaagent` 삭제, `lettuce-5.0` 이 5.0+ 전부 담당. 2.32.0 에서도 `LettuceInstrumentationModule`(5.1) 이 `isV3Preview()` 일 때 꺼지고 5.0 모듈이 5.1+ 를 맡는 구조였으므로, 이 커밋은 "3.0 에서 그 구성이 기본이 됨" 을 확정한 것이다.
- 후보 이력 보강: `5eea4918e5`(#20305, 2026-10-02, v3-preview 활성 선택자 정렬), `d5ebfa2513`(#19055, 2026-06-25, 배치 span, span 시작 위치 이동). 실제로 어느 시점에 v3-preview 모드에서 같은 결과가 처음 나타났는지는 bisect 하지 않았다(확인 안 함). 2.32.0 을 `-Dotel.instrumentation.common.v3-preview=true` 로 돌려 보는 것은 안 했다(플래그 이름 확인 안 함).
- 전체 bisect 는 하지 않았다. 테스트 한 번이 마이너 컴파일 포함 1~12분이라 후보를 이력으로만 좁혔다.

## 의도된 변경인가
- "`CancellationException` 은 에러가 아니다" 는 **의도된 설계**다. 근거: 주석 "and don't report this as an error", 3개 위치에 반복, 리액티브 구독 취소 테스트 `LettuceReactiveClientTest.testCommandCancelOnMonoPublisher`(255행)·`testCommandCancelAfter2OnFluxPublisher`(387행, 실험적 속성 `lettuce.command.cancelled`)가 동작을 고정.
- 그러나 sync 타임아웃은 그 설계가 겨냥한 상황(사용자의 구독 취소)이 아니다. 호출자는 `RedisCommandTimeoutException` 을 받는다. 같은 호출이 2.32.0 최신 Lettuce 에서는 에러, 라이브러리에서는 에러(최신)다.
- #20533 의 breaking-change 문서(PR 본문, `CHANGELOG.md:123-128`)는 계측 스코프 이름, 인코딩 이벤트, 설정 키만 적고 에러 상태 변화는 언급하지 않았다. 에이전트의 sync 타임아웃 테스트는 없다.
- 판단: **취소를 에러가 아니라고 본 설계는 의도, 그것이 sync 타임아웃에까지 적용돼 최신 Lettuce 에서 2.x 대비 동작이 바뀐 것은 의도가 확인되지 않은 부작용**. 유지보수자가 "취소는 에러가 아니다" 로 의도했다고 답할 가능성이 남아 있어, 이슈는 "버그 보고 + 설계 질문" 으로 쓴다. 단정하지 않는다.

## 수정 방향(이슈에 제안 수준으로만)
- `CancellationException` 면제를 sync 타임아웃과 구분할 방법이 에이전트 쪽에 있는지 확인 안 함. 후보: sync 프록시(`FutureSyncInvocationHandler`/`Futures.awaitOrCancel`) 경로에서 던져지는 `RedisCommandTimeoutException` 을 관찰, 또는 취소를 면제하지 않기. 어느 쪽이 리액티브 취소 테스트와 맞는지는 시험 안 함.
- 부수 문제: 라이브러리(최신)는 `error.type=java.util.concurrent.CancellationException` 로 기록한다. 사용자 관점의 실패 원인은 timeout 이다.
