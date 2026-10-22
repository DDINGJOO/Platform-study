# PR 초안 (푸시·PR 생성은 하지 않음)

AGENTS.md 규칙: Summary/Details/Testing 헤딩 없음, 하드랩 없음.

## 제목

Don't record unknown Kafka producer partition and offset

## 본문

When a Kafka producer send fails, kafka-clients still passes the callback a `RecordMetadata`, filled with `-1` for the offset and for the partition if none had been assigned yet (`RecordMetadata.UNKNOWN_PARTITION`). `KafkaProducerAttributesExtractor` only checked for `null`, so failed `send` spans ended up with `messaging.kafka.offset=-1` and sometimes `messaging.destination.partition.id=-1`. Those values are "unknown" markers, not a record offset or a partition, so they are now skipped. A partition that is known (the send failed after it was assigned) is still recorded.

The client-side behavior differs by version: kafka-clients 2.6.0 passes `null` for failures before partition assignment, while recent clients pass the `-1` metadata, so the tests build the callback arguments directly instead of relying on a broker.
