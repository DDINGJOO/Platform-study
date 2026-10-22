### Describe the bug

When a command sent through the Lettuce **synchronous** API hits the client-side timeout, the application receives `io.lettuce.core.RedisCommandTimeoutException`, but the Java agent ends the span with status `UNSET` and no `error.type`/exception event.

On 2.32.0 the same call is recorded as an error (`ERROR` status plus an `exception` event) when a recent Lettuce version is used.

The Lettuce sync API does not complete the command with the timeout exception. On timeout it cancels the command and only throws `RedisCommandTimeoutException` to the caller (`Futures.awaitOrCancel`: `cmd.cancel(true); throw ExceptionFactory.createTimeoutException(...)`). The command future therefore completes with `CancellationException`. `EndCommandAsyncBiFunction.end` (lettuce-5.0 javaagent) treats `CancellationException` as "not an error":

https://github.com/open-telemetry/opentelemetry-java-instrumentation/blob/079a5af0e2f57d36527bdb7df8d65596ac013475/instrumentation/lettuce/lettuce-5.0/javaagent/src/main/java/io/opentelemetry/javaagent/instrumentation/lettuce/v5_0/EndCommandAsyncBiFunction.java#L47-L52

Since #20533 removed the Lettuce 5.1 javaagent module, Lettuce 5.1+ goes through this code path instead of the `OpenTelemetryTracing` path used by the 5.1 module on 2.x, which reports the cancellation as an error.

### Steps to reproduce

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

### Expected behavior

A client-side timeout that surfaces to the caller as `RedisCommandTimeoutException` is a failed operation, so the span (and the `db.client.operation.duration` metric) should carry the error status and an `error.type`, as it did on 2.32.0.

### Actual behavior

| | main (079a5af0e2) | v2.32.0 |
|---|---|---|
| Java agent, latest Lettuce, sync timeout | `UNSET`, no `error.type`, no exception event | `ERROR`, `exception` event |
| Java agent, Lettuce 5.1.x | `UNSET` (same on 2.32.0) | `UNSET` |
| standalone library, latest Lettuce | `ERROR`, `error.type=java.util.concurrent.CancellationException` | `ERROR`, `exception` event |

### Javaagent or library instrumentation version

main (079a5af0e2); regression compared to v2.32.0

### Environment

main at 079a5af0e2 and v2.32.0, JDK 25, Testcontainers `redis:6.2.3-alpine`, Lettuce: latest resolved by `-PtestLatestDeps=true` (exact version not recorded)

### Additional context

I found that cancellation being non-error is intentional for reactive subscription cancellation (`LettuceReactiveClientTest.testCommandCancelOnMonoPublisher`, `lettuce.command.cancelled`), so this may be a question of how to tell a sync timeout apart from a user-initiated cancel. I will open a PR with a proposal.

- The standalone library on latest Lettuce reports `error.type=java.util.concurrent.CancellationException` for the same timeout instead of `RedisCommandTimeoutException`, which hides the cause.
- With Lettuce 5.1.0 the Tracing SPI does not hand over the exception when a command is cancelled, so the span is `UNSET` there on 2.x as well. That is unrelated to this report.
- I did not check Lettuce 4.x or reactive/async timeouts through the agent. I did not run 2.32.0 with the v3 preview flag.
