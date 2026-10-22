# 재현 기록

기준: open-telemetry/opentelemetry-java-instrumentation main `4c54b89cba6e5e2fad3be1cb3ad1a6203f99dc30` (2026-10-22). JDK 25.0.4 (`.java-version` = 25), Gradle 9.8.2.

## 공통 명령

```
JAVA_HOME=/opt/homebrew/Cellar/openjdk@25/25.0.4/libexec/openjdk.jdk/Contents/Home \
./gradlew --no-daemon --max-workers=2 -Dorg.gradle.jvmargs=-Xmx2g -Ddev=true \
  :instrumentation:kafka:kafka-clients:kafka-clients-2.6:library:test --tests '*WrapperSendExceptionTest' \
  > logs/<번호>-<이름>.log 2>&1
```

`-Ddev=true` 가 필요한 이유: main 의 `instrumentation-api/.../InstrumenterBuilder.java:53` 에 안 쓰이는 `logger` 필드가 있고 `-Werror` 때문에 로컬 `compileJava` 가 실패한다(`logs/01-build-aborted-werror.log`). `conventions/src/main/kotlin/otel.java-conventions.gradle.kts:88-91` 가 `dev=true` 일 때 `-Werror` 를 끈다. 내 변경과 무관하며 upstream CI 가 왜 통과하는지는 확인 안 함.

## 결과 요약

| 단계 | 코드 상태 | 결과 | 걸린 시간 | 로그 / XML |
|---|---|---|---|---|
| 수정 전 | 테스트만 추가, 본 코드 원본 | 3개 중 2개 실패(`BUILD FAILED`, exit=1) | 28s (JUnit 20.8s) | `logs/04-before-fail.log`, `logs/04-before-fail-TEST-WrapperSendExceptionTest.xml` |
| 수정 후 | 본 코드 수정 | 3개 통과(`BUILD SUCCESSFUL`, exit=0) | 7s (JUnit 0.95s) | `logs/05-after-pass.log`, `logs/05-after-pass-TEST-WrapperSendExceptionTest.xml` |
| 본 코드만 되돌림 | 테스트 유지, 본 코드 원복 | 3개 중 2개 실패(exit=1) | 27s (JUnit 20.8s) | `logs/06-revert-fail.log`, `logs/06-revert-fail-TEST-WrapperSendExceptionTest.xml` |

JUnit 시간이 20초대인 것은 첫 테스트의 Mockito/OTel 초기화 때문으로 보이나 원인은 확인 안 함. 실패한 두 테스트는 `producerSpanHasNoPartitionAndOffsetWhenSendFailsBeforePartitionAssigned()` 와 `producerSpanKeepsPartitionButNotOffsetWhenSendFailsAfterPartitionAssigned()`. 기존 `producerSpanEndedWhenSendThrowsSynchronously()` 는 세 경우 모두 통과.

## 수정 전 실패의 핵심 출력

JUnit XML(`04-before-fail-...xml`) 의 span 속성 로그에서:

- 파티션 미배정 경우: `messaging.kafka.offset=-1`, `messaging.destination.partition.id=-1`
- 파티션 3 경우: `messaging.kafka.offset=-1`, `messaging.destination.partition.id=3`

실패 메시지(파티션 3 테스트):

```
Expecting actual:
  [messaging.kafka.offset, messaging.destination.partition.id, messaging.system, messaging.operation.type,
   messaging.kafka.message.key, error.type, messaging.destination.name, messaging.operation.name]
to contain exactly in any order:
  [messaging.destination.partition.id, messaging.system, ...]
but the following elements were unexpected:
  [messaging.kafka.offset]
```

## 모듈 테스트 (수정 후, 같은 `-Ddev=true`)

| 대상 | 개수 | 결과 | 시간 | 로그 |
|---|---|---|---|---|
| kafka-clients-2.6 library `test` / `testReceiveTelemetry` / `testExperimental` / `testRegression` | 6(skip 1) / 3 / 2 / 22(skip 1) | 실패 0, `BUILD SUCCESSFUL` | 1m 10s (전체 71s) | `logs/08-module-tests-library.log` |
| kafka-clients-0.11 `javaagent:test` | 23(skip 5) | 실패 0 | 92s(unit-tests 포함) | `logs/09-module-tests-javaagent.log` |
| kafka-clients-0.11 `javaagent-unit-tests:test` | 35 | 실패 0 | 위와 함께 | 위와 같음 |

개수는 `logs/module-xml/` 의 JUnit XML 합계. `spotlessApply`(common-0.11 library, 2.6 library): `exit=0`, 27s, 파일 변경 없음(`logs/07-spotless.log`).

확인 안 함: `latestDepTest`, kafka-streams / kafka-connect 모듈, 전체 `check`, 실제 브로커(Testcontainers)에서 실패를 일으켜 보는 end-to-end 재현.

## 재현 시 헛디딘 부분

- 첫 시도의 브로커 없는 실제 `KafkaProducer` 테스트는 kafka-clients 2.6.0 에서 재현되지 않았다(early failure 때 콜백에 `null` 이 전달됨). 자세한 내용은 `journal.md` 16:55 항목과 `analysis.md`.
