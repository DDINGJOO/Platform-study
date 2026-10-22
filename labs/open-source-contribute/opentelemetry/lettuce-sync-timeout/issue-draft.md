이슈: https://github.com/open-telemetry/opentelemetry-java-instrumentation/issues/20847 (2026-10-22, 사용자가 웹 양식으로 제출, 라벨 bug·needs triage 붙음. API 로 먼저 만든 #20846 은 닫힘)

# 이슈 초안 (미제출. 승인 전에 올리지 않는다)

저장소: open-telemetry/opentelemetry-java-instrumentation. 이슈 템플릿(bug report) 적용 여부는 제출 직전에 웹 양식으로 확인한다(확인 안 함).

## Title
Lettuce (Java agent, 5.1+): command timeout via the sync API is recorded as a successful span on main; it was an error in 2.32.0

## Body

**Describe the bug**

When a command sent through the Lettuce **synchronous** API hits the client-side timeout, the application receives `io.lettuce.core.RedisCommandTimeoutException`, but the Java agent ends the span with status `UNSET` and no `error.type`/exception event.

On 2.32.0 the same call is recorded as an error (`ERROR` status plus an `exception` event) when a recent Lettuce version is used.

The Lettuce sync API does not complete the command with the timeout exception. On timeout it cancels the command and only throws `RedisCommandTimeoutException` to the caller (`Futures.awaitOrCancel`: `cmd.cancel(true); throw ExceptionFactory.createTimeoutException(...)`). The command future therefore completes with `CancellationException`. `EndCommandAsyncBiFunction.end` (lettuce-5.0 javaagent) treats `CancellationException` as "not an error":

https://github.com/open-telemetry/opentelemetry-java-instrumentation/blob/079a5af0e2f57d36527bdb7df8d65596ac013475/instrumentation/lettuce/lettuce-5.0/javaagent/src/main/java/io/opentelemetry/javaagent/instrumentation/lettuce/v5_0/EndCommandAsyncBiFunction.java#L47-L52

Since #20533 removed the Lettuce 5.1 javaagent module, Lettuce 5.1+ goes through this code path instead of the `OpenTelemetryTracing` path used by the 5.1 module on 2.x, which reports the cancellation as an error.

**Steps to reproduce**

Test added to `LettuceSyncClientTest` in `lettuce-5.0/javaagent` (Testcontainers Redis, as in the existing tests):

```java
@Test
void syncCommandTimeoutIsRecordedAsError() {
  StatefulRedisConnection<String, String> timeoutConnection = redisClient.connect();
  testing.waitForTraces(connectionTelemetryEnabled() ? 1 : 0);
  testing.clearData();
  timeoutConnection.setTimeout(Duration.ofMillis(300));

  Throwable thrown =
      catchThrowable(() -> timeoutConnection.sync().blpop(2, "TIMEOUT_LIST"));
  timeoutConnection.close();

  assertThat(thrown).isInstanceOf(RedisCommandTimeoutException.class);
  testing.waitAndAssertTraces(
      trace ->
          trace.hasSpansSatisfyingExactly(
              span -> span.hasKind(SpanKind.CLIENT).hasStatus(StatusData.error())));
}
```

Run with `./gradlew :instrumentation:lettuce:lettuce-5.0:javaagent:lettuce65Test -PtestLatestDeps=true --tests '*LettuceSyncClientTest.syncCommandTimeoutIsRecordedAsError'`.

The same test with `TimeoutOptions.enabled(Duration.ofMillis(100))` on the client options (instead of `setTimeout`) behaves identically with the latest Lettuce, because the sync wait uses the same timeout and cancels first.

**Actual / expected behavior**

| | main (079a5af0e2) | v2.32.0 |
|---|---|---|
| Java agent, latest Lettuce, sync timeout | `UNSET`, no `error.type`, no exception event | `ERROR`, `exception` event |
| Java agent, Lettuce 5.1.x | `UNSET` (same on 2.32.0) | `UNSET` |
| standalone library, latest Lettuce | `ERROR`, `error.type=java.util.concurrent.CancellationException` | `ERROR`, `exception` event |

Expected: a client-side timeout that surfaces to the caller as `RedisCommandTimeoutException` is a failed operation, so the span (and the `db.client.operation.duration` metric) should carry the error status and an `error.type`.

I found that cancellation being non-error is intentional for reactive subscription cancellation (`LettuceReactiveClientTest.testCommandCancelOnMonoPublisher`, `lettuce.command.cancelled`), so this may be a question of how to tell a sync timeout apart from a user-initiated cancel. I did not look into how.

**Additional notes**

- The standalone library on latest Lettuce reports `error.type=java.util.concurrent.CancellationException` for the same timeout instead of `RedisCommandTimeoutException`, which hides the cause.
- With Lettuce 5.1.0 the Tracing SPI does not hand over the exception when a command is cancelled, so the span is `UNSET` there on 2.x as well. That is unrelated to this report.
- I did not check Lettuce 4.x or reactive/async timeouts through the agent. I did not run 2.32.0 with the v3 preview flag.

**Environment**

main at 079a5af0e2 and v2.32.0, JDK 25, Testcontainers `redis:6.2.3-alpine`, Lettuce: latest resolved by `-PtestLatestDeps=true` (exact version not recorded)

## 한국어 번역(사용자 확인용)
제목: Lettuce(Java 에이전트, 5.1+): sync API 명령 타임아웃이 main 에서 성공 span 으로 기록된다. 2.32.0 에서는 에러였다.
요지: sync API 로 보낸 명령이 클라이언트 타임아웃에 걸리면 호출자는 `RedisCommandTimeoutException` 을 받지만, 에이전트는 span 을 UNSET 으로 끝낸다(에러 타입·예외 이벤트 없음). 원인은 Lettuce sync 프록시가 타임아웃 때 명령을 취소(`CancellationException`)하고 예외는 호출자에게만 던지는데, `EndCommandAsyncBiFunction` 이 취소를 에러가 아니라고 보기 때문이다. #20533 로 5.1 에이전트 모듈이 사라지면서 5.1+ 가 이 경로를 타게 됐고, 2.x 의 5.1 모듈은 취소를 에러로 기록했다. 리액티브 취소를 에러로 안 보는 것은 의도된 설계라서 sync 타임아웃을 구분할 방법을 묻는 형태다. 재현 테스트와 표를 첨부.
