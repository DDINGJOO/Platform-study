# 원인 분석

기준 main 커밋: `4c54b89cba6e5e2fad3be1cb3ad1a6203f99dc30` ("Ignore nested defineClass calls for the same class (#20804)", 2026-10-22).

## 어느 경로인가

producer 쪽이다. consumer 쪽(`KafkaConsumerAttributesExtractor`, `KafkaBatchRecordAttributes`)은 `ConsumerRecord` 의 `partition()/offset()` 을 쓰고 이 값은 항상 실제 값이라 해당 없음(코드를 읽어서만 판단, 별도 실행 확인 안 함).

## 원인 위치

`instrumentation/kafka/kafka-clients/kafka-clients-common-0.11/library/src/main/java/io/opentelemetry/instrumentation/kafkaclients/common/v0_11/internal/KafkaProducerAttributesExtractor.java:50-54` (`onEnd`):

```java
if (recordMetadata != null) {
  attributes.put(MESSAGING_DESTINATION_PARTITION_ID, String.valueOf(recordMetadata.partition()));
  attributes.put(MESSAGING_KAFKA_OFFSET, recordMetadata.offset());
}
```

`recordMetadata != null` 만 검사하고 값이 유효한지는 보지 않는다. 이 추출기에 metadata 를 넘기는 곳은 둘이고, 둘 다 콜백 인자를 그대로 전달한다.

- javaagent: `instrumentation/kafka/kafka-clients/kafka-clients-0.11/javaagent/src/main/java/io/opentelemetry/javaagent/instrumentation/kafkaclients/v0_11/ProducerCallback.java:35-36` (`producerInstrumenter().end(context, request, metadata, exception)`)
- 라이브러리 계측: `instrumentation/kafka/kafka-clients/kafka-clients-2.6/library/src/main/java/io/opentelemetry/instrumentation/kafkaclients/v2_6/internal/KafkaProducerTelemetry.java:126-127`

`OpenTelemetryProducerInterceptor.onAcknowledgement` 은 본문이 비어 있어(`{}`) span 을 끝내지 않으므로 해당 없음.

## Kafka 클라이언트의 동작 (근거)

실패해도 콜백에는 `null` 이 아니라 `-1` 로 채운 `RecordMetadata` 가 전달된다. 그래서 `!= null` 검사가 소용없다. (클라이언트 소스는 raw.githubusercontent.com 에서 받아 읽음, 사본 `scratchpad/kafka-src/`)

- apache/kafka trunk `KafkaProducer.java`
  - `AppendCallbacks.onCompletion`: `if (metadata == null) { metadata = new RecordMetadata(topicPartition(), -1, -1, RecordBatch.NO_TIMESTAMP, -1, -1); }` 뒤에 사용자 콜백 호출(약 1801-1807행).
  - `doSend` 의 `catch (ApiException e)`: `RecordMetadata nullMetadata = new RecordMetadata(tp, -1, -1, RecordBatch.NO_TIMESTAMP, -1, -1); callback.onCompletion(nullMetadata, e);` (약 1257-1260행).
  - `ProducerInterceptors.onSendError` 도 같은 방식으로 `-1` 메타데이터를 만든다.
- kafka-clients 2.6.0 `InterceptorCallback.onCompletion`(1359-1363행): `metadata = metadata != null ? metadata : new RecordMetadata(tp, -1, -1, RecordBatch.NO_TIMESTAMP, -1L, -1, -1);`
- kafka-clients 2.6.0 `doSend` 의 `catch (ApiException e)`(964-967행)는 `callback.onCompletion(null, e)` 로 `null` 을 넘긴다. 즉 파티션 배정 전 실패는 2.6.0 에서는 이 버그에 걸리지 않고, 최신 클라이언트(trunk)에서는 걸린다. 이 차이는 소스로만 확인했고, 중간 버전 어디서 바뀌었는지는 확인 안 함.
- `RecordMetadata` Javadoc(trunk): `offset()` — "the offset of the record, or -1 if `hasOffset()` returns false", `hasOffset()` — "Indicates whether the record metadata includes the offset", `UNKNOWN_PARTITION` — "Partition value for record without partition assigned"(값 -1). `hasOffset()` 은 2.6.0 에도 있으나 이 모듈이 컴파일하는 0.11.0.0 에 있는지는 확인 안 함.

정리하면 offset 은 모든 실패에서 -1, partition 은 파티션이 정해지기 전에 실패할 때만 -1(`UNKNOWN_PARTITION`)이고, 정해진 뒤 실패하면 실제 값이다.

## 시맨틱 컨벤션 근거

- `messaging.kafka.offset`: "The offset of a record in the corresponding Kafka partition." 타입 int, 요구 수준 Recommended "If span describes operation on a single message". -1 같은 sentinel 은 정의되어 있지 않고 실제 레코드 offset 이 아닌 값은 의미가 없다. https://github.com/open-telemetry/semantic-conventions/blob/main/model/messaging/registry.yaml (id `messaging.kafka.offset`), https://github.com/open-telemetry/semantic-conventions/blob/main/docs/messaging/kafka.md
- `messaging.destination.partition.id`: "The identifier of the partition messages are sent to or received from, unique within the `messaging.destination.name`." Recommended "When applicable." 파티션이 정해지지 않았다면 해당 사항이 없다. 같은 registry 파일, 같은 kafka.md.
- Kafka 문서에 `message.key` 가 null 이면 "MUST NOT be set" 이라는 문구는 있으나(kafka.md) offset/partition 에 대한 같은 문구는 없었다. 즉 컨벤션이 -1 생략을 명시한 것은 아니고, "값이 없으면 기록하지 않는다"는 일반 관례와 위 정의에서 추론한 것이다. 이 해석은 PR 에서 근거로 과장하지 않는다.
- 기록 시점의 main 기준으로 읽었고 이 저장소가 채택한 시맨틱 컨벤션 버전과 일치하는지는 확인 안 함(`.github/agents/knowledge/semconv-conformance.md` 는 버전 확인 절차를 요구).

## 수정 방향과 기각한 대안

- 채택: `partition() >= 0`, `offset() >= 0` 일 때만 기록. kafka-clients 0.11 에 컴파일되는 모듈이라 가장 이식성이 높다.
- 기각: `recordMetadata.hasOffset()`. 2.6.0 에는 있으나 0.11 에 있는지 확인하지 못했고 파티션에는 대응 메서드가 없다.
- 기각: `exception != null` 이면 둘 다 생략. 파티션이 실제 값으로 있는 경우의 정보를 버린다.
