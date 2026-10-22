# OpenTelemetry Java Instrumentation 재현 기록 (2026-10-22)

저장소: open-telemetry/opentelemetry-java-instrumentation, `git clone --filter=blob:none` 후 머지 커밋마다 checkout.
PR 4건 모두 gh 로 확인한 결과 MERGED.

| PR | 머지 커밋 | 머지 시각 (UTC) |
|---|---|---|
| #20658 | 811c17a4f2 | 2026-10-19 07:20:23 |
| #20659 | 2d0957e0bd | 2026-10-20 07:11:37 |
| #20660 | c0a9e91262 | 2026-10-19 14:28:18 |
| #20661 | b1fcd7954b | 2026-10-19 07:00:57 |

## 환경

- macOS, 메모리 8GB. 다른 Gradle 빌드와 동시 실행.
- Gradle 9.8.1 (wrapper), 런처 JDK: Amazon Corretto 21.0.11.
- 프로젝트 toolchain: `otel.java-conventions` 의 `repositoryDefaultJavaToolchainVersion` = 25 (CI 의 `.java-version` 도 25). 컴파일과 테스트 JVM 은 toolchain 에 따라 JDK 25.
- 공통 옵션: `--no-daemon --max-workers=2 -Dorg.gradle.jvmargs=-Xmx2g`
- 공통 접두: `JAVA_HOME=<corretto-21> ./gradlew ...`
- 본 코드 되돌리기: `git checkout <머지커밋>^1 -- <본 코드 경로>` (테스트는 머지 커밋 상태 유지)

## #20660 JDBC address= URL (머지 커밋 c0a9e91262)

```
:instrumentation:jdbc:library:test --tests '*JdbcConnectionUrlParserTest*'
```
- (1) 머지 커밋: 304 tests, 0 failed, BUILD SUCCESSFUL in 19m 4s (첫 실행이라 빌드 플러그인 컴파일과 의존성 내려받기 포함).
- (2) `MysqlUrlParser.java` 만 직전 커밋으로 되돌림: 304 tests, 5 failed, BUILD FAILED in 8s.
  - mysql `jdbc:mysql://address=(host=mdb.host)(port=33)/mdbdb`: expected `DbServerTarget{address=mdb.host, port=33}` but was `null`
  - mysql `.../mdb%2ddb` 도 같은 실패
  - mysql `jdbc:mysql://address=(host=mdb.host)/mdbdb?password=(port=33)`: expected `DbServerTarget{address=mdb.host, port=null}` but was `null` (서브프로토콜 없는 형식이라 호스트 자체를 읽지 못함)
  - mysql `jdbc:mysql:replication://address=(host=mdb.host)/mdbdb?password=(port=33)`: expected `port=null` but was `DbServerTarget{address=mdb.host, port=33}` (구버전이 쿼리 값의 port 를 읽음)
  - mariadb `jdbc:mariadb://address=(host=mdb.host)(port=33)/mdbdb`: expected port=33 but was null

## #20659 Reactor Flux 수요 전달 (머지 커밋 2d0957e0bd)

```
:instrumentation:reactor:reactor-3.1:library:test --tests '*ReactorCoreTest*'
```
- (1) 머지 커밋: 36 tests, 0 failed, BUILD SUCCESSFUL in 1m 54s.
- (2) `ContextPropagationOperator.java` 만 되돌림: 36 tests, 1 failed (`fluxPassesDownstreamDemandToSource`), 11s.
  ```
  Expecting actual:
    [32L]
  to contain exactly (and in same order):
    [1L]
  ```

## #20661 Lettuce 클라이언트 오류 (머지 커밋 b1fcd7954b)

```
:instrumentation:lettuce:lettuce-5.1:library:test --tests '*LettuceAsyncClientTest*' --tests '*LettuceDbAttributesGetterTest*'
```
Redis 컨테이너는 Testcontainers (`redis:6.2.3-alpine`), Docker 사용.
- (1) 머지 커밋, 기본 의존성(Lettuce 5.1.0): 9 + 2 tests, 0 failed, 1m 8s (컨테이너 이미지 내려받기 포함).
- (2) 본 코드 5개 파일(`library/src/main` 전체)과 `LettuceDbAttributesGetterTest` 를 직전 커밋으로 되돌림(후자는 리팩터링으로 `LettuceResponse.fromErrorMessage` 를 쓰게 바뀌어서 같이 되돌려야 컴파일됨. 회귀 테스트는 `AbstractLettuceAsyncClientTest` 에 있고 그대로 둠). 기본 의존성(5.1.0)에서는 **통과**한다(9s). 5.1 은 타임아웃 메시지에 명령 이름이 없어서 버그가 드러나지 않음. PR 본문의 "Lettuce 6.6+" 와 일치.
- (3) 같은 되돌린 상태에 `-PtestLatestDeps=true`: 11 tests, 1 failed, 44s.
  ```
  LettuceAsyncClientTest > testCommandTimeoutDoesNotReportRedisErrorType() FAILED
    [STRING attribute 'error.type']
    expected: "io.lettuce.core.RedisCommandTimeoutException"
     but was: "BLPOP."
  ```
  이 실행에서 Gradle 캐시에 lettuce-core 7.9.0.RELEASE 가 새로 내려받아졌다(파일 시각 10:45).
- (4) 머지 커밋 복원 후 `-PtestLatestDeps=true`: 11 tests, 0 failed, 9s.

## #20658 Spring Kafka async acks 중복 스팬 (머지 커밋 811c17a4f2)

```
:instrumentation:spring:spring-kafka-2.7:javaagent:testAsyncAcks
```
`MockConsumer` 사용, Docker 불필요. 기본 의존성(spring-kafka 2.8.0, 이 스위트의 baseline)만 실행. latest deps 는 실행하지 않음.
- (1) 머지 커밋: SpringKafkaAsyncAcksTest 2 tests (`batchListener=false/true`), 0 failed, BUILD SUCCESSFUL in 1m 23s.
- (2) `ListenerConsumerInstrumentation.java` 만 되돌림: 2 tests, 2 failed, 9s.
  ```
  java.lang.AssertionError:
  Expecting empty but was: [TestSpanData{name=process orders, kind=CONSUMER, ... instrumentationScopeInfo=InstrumentationScopeInfo{name=io.opentelemetry.kafka-clients-0.11 ...
  at SpringKafkaAsyncAcksTest.doesNotCreateClientProcessSpansWhenAcksAreAsync(SpringKafkaAsyncAcksTest.java:86)
  ```

## 하지 못한 것

- #20658 의 PR 본문 실험("Spring Boot 앱, 레코드 3건에 process 스팬 6개")은 재현하지 않았다. 앱·브로커가 필요하고 원장에도 앱 코드가 없다.
- #20658 의 latest deps 스위트, #20659 의 다른 Reactor 버전, #20661 의 Lettuce 중간 버전은 돌리지 않았다.
- #20660 의 PR 본문 `localhost:3306` 관찰(기본 semconv)은 재현하지 않았다. 파서 단위 테스트의 `null` 만 확인했다.

저장소 사본은 확인 후 삭제했다.
