# journal: Kafka 실패 span 의 partition/offset -1

작업 시각은 모두 KST(로컬) 2026-10-22. 확인하지 않은 것은 "확인 안 함" 으로 표시한다.

## 16:39 클론, JDK, 중복 검색
- 명령: `git clone --filter=blob:none https://github.com/open-telemetry/opentelemetry-java-instrumentation.git otel-kafka` (scratchpad/otel-kafka)
- 출력 핵심: `git log -1` = `4c54b89cba6e5e2fad3be1cb3ad1a6203f99dc30 2026-10-22 09:54:24 +0300 Ignore nested defineClass calls for the same class (#20804)`
- `.java-version` = `25`. `/usr/libexec/java_home -V` 에 25.0.4(Homebrew) 있음. 기본값은 26.0.1 이라 Gradle 실행 때 JAVA_HOME 을 25 로 지정한다. (CONTRIBUTING: "requires Java 25")
- 중복 검색(읽기만): `gh search issues|prs --repo open-telemetry/opentelemetry-java-instrumentation "<query>"` 를 질의 3개로 실행.
  질의: `kafka offset -1 span`, `kafka partition offset failed send span`, `kafka unknown offset`. 결과는 이슈/PR 모두 `[]`.
  - 판단: 검색어가 좁아서 `[]` 일 수 있다. 아래 16:4x 에서 더 넓은 질의로 한 번 더 확인한다.

## 16:40 AGENTS.md / CONTRIBUTING.md 규칙
- AGENTS.md: PR 본문에 Summary/Details/Testing 헤딩 금지, 하드랩 금지. Gradle 은 `--rerun-tasks` 금지, 출력을 tail/grep 으로 파이프 금지(종료 코드가 가려짐), 타임아웃 0.
- 지시받은 "Gradle 출력은 파일로 리다이렉트" 와 AGENTS.md 의 "파이프 금지" 는 충돌하지 않는다. 리다이렉트만 하고 종료 코드를 `$?` 로 기록한다.
- `.github/agents/knowledge/README.md` 를 읽었다. 관련 문서: `semconv-conformance.md`, `testing-general-patterns.md`. 

## 16:41 코드 위치 탐색
- 명령: `grep -rn -E 'offset\(\)|partition\(\)|OFFSET|PARTITION' instrumentation/kafka --include='*.java'`
- 첫 의심: producer 콜백의 RecordMetadata 인지 consumer 인지 모름. consumer 쪽은 `KafkaConsumerAttributesExtractor` 가 `record.partition()/offset()` 을 쓰는데 ConsumerRecord 는 항상 실제 값이므로 후보에서 약하다.
- producer 쪽 후보: `KafkaProducerAttributesExtractor.onEnd` 가 `recordMetadata != null` 이면 무조건 `partition`, `offset` 을 기록 (파일: instrumentation/kafka/kafka-clients/kafka-clients-common-0.11/library/src/main/java/io/opentelemetry/instrumentation/kafkaclients/common/v0_11/internal/KafkaProducerAttributesExtractor.java:50-54).
- 호출 경로 두 개 확인: javaagent `ProducerCallback.onCompletion`(kafka-clients-0.11/javaagent), 라이브러리 `KafkaProducerTelemetry.ProducerCallback.onCompletion`(kafka-clients-2.6/library). 둘 다 `metadata` 를 그대로 `end()` 에 넘김.
- interceptor 경로(`OpenTelemetryProducerInterceptor.onAcknowledgement`)는 비어 있어(`{}`) span 을 끝내지 않는다. 이 경로는 해당 없음.
- 가설: Kafka 가 실패 시 `callback.onCompletion(null, e)` 가 아니라 -1 로 채운 RecordMetadata 를 넘겨서 `!= null` 검사가 소용없을 것.

## 16:43 Kafka 클라이언트 소스 확인 (가설 검증)
- 명령: `curl -sL https://raw.githubusercontent.com/apache/kafka/{2.6.0,trunk}/clients/src/main/java/org/apache/kafka/clients/producer/{KafkaProducer,RecordMetadata}.java` (scratchpad/kafka-src/)
- trunk `KafkaProducer.java` AppendCallbacks.onCompletion:
  `if (metadata == null) { metadata = new RecordMetadata(topicPartition(), -1, -1, RecordBatch.NO_TIMESTAMP, -1, -1); }` 후 사용자 콜백 호출.
- trunk doSend 의 `catch (ApiException e)`: `RecordMetadata nullMetadata = new RecordMetadata(tp, -1, -1, RecordBatch.NO_TIMESTAMP, -1, -1); callback.onCompletion(nullMetadata, e);`
- 2.6.0 `InterceptorCallback.onCompletion`: `metadata = metadata != null ? metadata : new RecordMetadata(tp, -1, -1, RecordBatch.NO_TIMESTAMP, -1L, -1, -1);`
- 가설 확인: 실패 시 metadata 는 null 이 아니라 offset=-1 인 객체다. partition 은 TopicPartition 의 값이라 파티션이 정해지기 전에 실패하면 `RecordMetadata.UNKNOWN_PARTITION`(-1), 정해진 뒤 실패(예: 레코드 크기 초과)면 실제 값이다. 즉 "둘 다 -1" 은 파티션 배정 전 실패(예: 메타데이터 대기 타임아웃)에서만이고, offset 은 모든 실패에서 -1 이다.
- 주의: common 모듈은 kafka-clients 0.11.0.0 에 대해 컴파일한다(`kafka-clients-common-0.11/library/build.gradle.kts`: `compileOnly("org.apache.kafka:kafka-clients:0.11.0.0")`). `RecordMetadata.hasOffset()` 은 2.6.0 에는 있으나 0.11 에 있는지 확인 안 함. 그래서 `offset() >= 0` / `partition() >= 0` 비교로 수정하는 편이 안전하다.

## 16:42 중복 재검색 (더 넓은 질의)
- 질의: `kafka producer partition -1`, `kafka RecordMetadata offset`, `kafka send failure attributes`, `kafka partition.id unknown`, `RecordMetadata`, `KafkaProducerAttributesExtractor`, `kafka offset` (issues/prs 각각). 출력 전체: `logs/00-duplicate-search.log`.
- 관련 후보: 이슈 #18289 "OpenTelemetryProducerInterceptor can't record any broker errors"(closed), PR #17785 "Add stable messaging.kafka.offset attribute via SemconvStability (Fixes #15723)"(merged), PR #19504, #20388 등. 제목만 봤고 본문은 읽지 않았다(확인 안 함).
- 판단: 실패 span 의 -1 값을 다룬 이슈·PR 은 찾지 못했다. 이슈 검색 쪽 `gh search` 는 모든 단어가 일치해야 해서 놓쳤을 가능성은 남는다.

## 16:42 테스트 작성 (첫 시도: 실제 KafkaProducer)
- 기존 `WrapperSendExceptionTest`(kafka-clients-2.6/library) 에 테스트 추가. 첫 시도는 브로커 없는 실제 `KafkaProducer`(bootstrap `localhost:1`, `max.block.ms=500`)로 메타데이터 대기 타임아웃을 일으켜 "파티션 배정 전 실패" 를 만드는 것. 소스는 `logs/03-attempt-realproducer-test-source.java.txt`.
- 같은 파일에 mock `Producer` 로 콜백에 `RecordMetadata(partition 3, offset -1)` 을 넘기는 테스트도 추가.
- 이때 `MESSAGING_KAFKA_OFFSET` import 를 쓰지 않아 지우려고 `sed -i '/…/d'` 를 썼으나 macOS(BSD) sed 는 `-i` 뒤에 확장자 인자를 요구해서 실패했다. 이후 python 으로 지움.

## 16:42~16:54 첫 Gradle 실행: 테스트까지 못 감
- 명령: `JAVA_HOME=<25.0.4> ./gradlew --no-daemon --max-workers=2 -Dorg.gradle.jvmargs=-Xmx2g :instrumentation:kafka:kafka-clients:kafka-clients-2.6:library:test --tests '*WrapperSendExceptionTest' > logs/01-build-aborted-werror.log 2>&1`
- 결과: `exit=1 elapsed=700s`(11분 38초). 의존성 내려받기와 컴파일 시간이 대부분.
- 핵심 출력: `> Task :instrumentation-api:compileJava FAILED`, `InstrumenterBuilder.java:53: warning: [UnusedVariable] The field 'logger' is never read.`, `error: warnings found and -Werror specified`.
- 내 변경과 무관. main 4c54b89 의 `InstrumenterBuilder.logger` 가 안 쓰이는데 `-Werror` 라서 로컬 빌드가 깨진다. 왜 upstream CI 가 통과하는지는 확인 안 함.
- 대응: `conventions/src/main/kotlin/otel.java-conventions.gradle.kts:88-91` 에 `System.getProperty("dev") != "true"` 일 때만 `-Werror` 를 거는 장치가 있어서, 이후 모든 Gradle 명령에 `-Ddev=true` 를 붙였다. 소스는 건드리지 않았다.

## 16:54 두 번째 실행: 테스트 컴파일 오류
- 명령: 위와 같고 `-Ddev=true` 추가. 로그 `logs/02-compile-error-test-ctor.log`.
- 출력: `WrapperSendExceptionTest.java:130: error: constructor RecordMetadata in class RecordMetadata cannot be applied to given types;` (`> Task ...:compileTestJava FAILED`, 47초)
- 틀린 점: kafka-clients 2.6.0 의 `RecordMetadata` 생성자는 인자 7개(`..., Long checksum, int keySize, int valueSize`). trunk 와 시그니처가 달라서 6개로 썼다. 2.6.0 의 `InterceptorCallback` 이 `new RecordMetadata(tp, -1, -1, NO_TIMESTAMP, -1L, -1, -1)` 로 쓰는 것을 따라 고쳤다.

## 16:55 세 번째 실행: 수정 전 코드, 실제 producer 테스트의 틀린 예측
- 로그/XML: `logs/03-attempt-realproducer-before.log`, `logs/03-attempt-realproducer-before-TEST-WrapperSendExceptionTest.xml`. `3 tests completed, 2 failed`.
- 예측은 "실제 producer 의 타임아웃 실패 span 에 `partition.id=-1`, `offset=-1` 이 찍힌다" 였다. 틀렸다. span 속성은 `messaging.system, operation.type, message.key, error.type, messaging.client.id, destination.name, operation.name` 이고 offset/partition 은 없었다. 실패한 이유는 내 기대값에서 `messaging.client.id` 를 빠뜨렸기 때문.
- 원인 확인: kafka-clients 2.6.0 `KafkaProducer.doSend` 의 `catch (ApiException e)` 가 `callback.onCompletion(null, e)` 를 호출한다(KafkaProducer.java:964-967, 2.6.0). 즉 2.6.0 에서 파티션 배정 전 실패(메타데이터 타임아웃)는 metadata 가 null 이라 이 버그를 건드리지 않는다. trunk 는 같은 위치에서 `nullMetadata = new RecordMetadata(tp, -1, -1, ...)` 를 넘긴다(trunk KafkaProducer.java:1257-1260). 버전에 따라 동작이 다르다.
- 결정: 실제 producer 테스트는 버전 의존이라 버리고, 콜백 인자를 Kafka 클라이언트가 넘기는 모양(partition -1/offset -1)으로 직접 만든 mock 테스트로 바꾼다. 실제 최신 kafka-clients 로 이 실패를 재현하는 것은 하지 않았다(확인 안 함).
- mock 테스트에서 이미 보인 로그: `messaging.kafka.offset=-1, messaging.destination.partition.id=3` 가 기록됨(3번째 실행의 두 번째 테스트).

## 16:56 네 번째 실행: 수정 전 코드, 최종 테스트 (재현 성공)
- 명령: `./gradlew --no-daemon --max-workers=2 -Dorg.gradle.jvmargs=-Xmx2g -Ddev=true :instrumentation:kafka:kafka-clients:kafka-clients-2.6:library:test --tests '*WrapperSendExceptionTest' > logs/04-before-fail.log 2>&1` (JAVA_HOME=25.0.4)
- 결과: `exit=1 elapsed=28s`, `3 tests completed, 2 failed`, `BUILD FAILED in 28s`. XML: `logs/04-before-fail-TEST-WrapperSendExceptionTest.xml`(`tests="3" failures="2"`).
- 실패한 두 테스트: `producerSpanHasNoPartitionAndOffsetWhenSendFailsBeforePartitionAssigned()`, `producerSpanKeepsPartitionButNotOffsetWhenSendFailsAfterPartitionAssigned()`. 기존 `producerSpanEndedWhenSendThrowsSynchronously()` 는 통과.
- span 속성 출력(XML system-out): 파티션 3 경우 `messaging.kafka.offset=-1, messaging.destination.partition.id=3`, 파티션 미배정 경우 `messaging.kafka.offset=-1, messaging.destination.partition.id=-1`.

## 16:57 수정
- `KafkaProducerAttributesExtractor.onEnd`: `recordMetadata.partition() >= 0` 일 때만 `messaging.destination.partition.id`, `recordMetadata.offset() >= 0` 일 때만 `messaging.kafka.offset` 를 기록.
- 처음에 `hasOffset()` 을 쓰려 했지만 이 모듈은 kafka-clients 0.11.0.0 에 컴파일하고(`compileOnly("org.apache.kafka:kafka-clients:0.11.0.0")`) 0.11 에 이 메서드가 있는지 확인하지 못해 비교 연산으로 했다.
- 파티션도 같이 거른 이유: `RecordMetadata.UNKNOWN_PARTITION = -1` 이고 Kafka 가 실패 때 파티션 미배정이면 이 값을 쓴다. 단 offset 만 -1 인 경우(파티션은 실제 값)는 파티션은 유지한다.

## 16:57 수정 후 통과
- 명령: 04 와 동일. 로그 `logs/05-after-pass.log`, XML `logs/05-after-pass-TEST-WrapperSendExceptionTest.xml`.
- 결과: `exit=0 elapsed=7s`, `BUILD SUCCESSFUL in 6s`, XML `tests="3" failures="0" skipped="0"`.
- `:kafka-clients-common-0.11:library:compileJava` 가 실제로 다시 실행된 것을 로그로 확인(UP-TO-DATE 아님), `...library:test` 도 실행됨.

## 16:58 본 코드만 되돌림
- 방법: `git checkout -- <KafkaProducerAttributesExtractor.java>` 로 본 코드만 원복(테스트 파일은 유지), 실행 후 사본(`scratchpad/KafkaProducerAttributesExtractor.fixed.java`)으로 복원.
- 결과: 로그 `logs/06-revert-fail.log`, XML `logs/06-revert-fail-TEST-WrapperSendExceptionTest.xml`. `exit=1 elapsed=27s`, `3 tests completed, 2 failed`. 04 와 같은 두 테스트가 실패. 복원 후 `git status` 로 두 파일이 수정 상태임을 확인.

## 16:58 spotlessApply 와 모듈 테스트
- 첫 시도는 셸 변수 `G="./gradlew ..."` 를 zsh 에서 `$G` 로 호출해 `exit=127`(Gradle 이 실행조차 안 됨, `elapsed=0s`)이었다. zsh 는 변수를 단어 분리하지 않는다. 이 시도는 로그 파일이 의미 없어서 덮어썼다. bash 스크립트(`scratchpad/run-verify.sh`, `run-agent.sh`)로 다시 실행.
- 명령: `$K:kafka-clients-common-0.11:library:spotlessApply $K:kafka-clients-2.6:library:spotlessApply` (K=`:instrumentation:kafka:kafka-clients`). 결과 `spotless exit=0 elapsed=28s`(`logs/07-spotless.log`). 파일 변경 없음(이미 포맷 준수).
- 라이브러리 모듈: `$K:kafka-clients-2.6:library:{test,testReceiveTelemetry,testExperimental,testRegression} --continue` → `exit=0 elapsed=71s`, `BUILD SUCCESSFUL in 1m 10s` (`logs/08-module-tests-library.log`). XML 합계: test 6(skipped 1), testReceiveTelemetry 3, testExperimental 2, testRegression 22(skipped 1), 실패 0. Docker(testcontainers) 사용.
- javaagent: `$K:kafka-clients-0.11:javaagent:test $K:kafka-clients-0.11:javaagent-unit-tests:test --continue` → `exit=0 elapsed=92s` (`logs/09-module-tests-javaagent.log`). javaagent 23 tests(skipped 5), unit-tests 35, 실패 0.
- 확인 안 함: kafka-clients-2.6 의 `latestDepTest`, kafka-streams, kafka-connect 모듈 테스트, 전체 `check`.

## 17:03 커밋
- 브랜치 `kafka-failed-span-unknown-offset`(로컬), 커밋 `40f77f5c53ea227e0f4832dfeb5bac4ca2434c65`. 작성자·커밋터 모두 `DDINGJOO <173995233+DDINGJOO@users.noreply.github.com>`, 트레일러 `Assisted-by: Claude Opus 5.5`. 푸시·PR 생성 없음.
- 최종 diff: `patch.diff`(`git diff main`).
- 참고: 시스템에서 제안한 `Co-Authored-By` 줄은 저장소 정책(Assisted-by)과 지시를 따라 넣지 않았다.

## 2026-10-22 결정: 제출 보류

- 수정과 검증은 끝났지만 PR 을 올리지 않기로 했다.
- 이유: -1 은 kafka-clients 가 "알 수 없음" 을 표시하려고 일부러 쓰는 값이다. 계측이 그 값을 그대로 옮기는 것도 의도된 동작일 수 있다. span 상태(ERROR)와 `error.type` 이 이미 실패를 알려 주므로 -1 을 지워서 얻는 것은 데이터 품질 정도이고, 시맨틱 컨벤션에도 -1 을 생략하라는 명시가 없다. 앞서 머지된 4건(명백한 오동작)과 성격이 달라 설득력이 약하다고 판단했다.
- 남긴 것: 로컬 브랜치 `kafka-failed-span-unknown-offset`(커밋 40f77f5c53), patch.diff, pr-draft.md.
- 다시 열 조건: `acks=0` 성공 경로에서도 offset -1 이 기록되는지 확인되면(정상 동작에서 -1 이 남는다면) 근거가 달라진다. 확인 안 함. 또는 메인테이너가 같은 문제를 이슈로 다루면.
