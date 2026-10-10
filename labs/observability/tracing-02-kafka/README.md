# 추적과 디버깅 실습-2: Kafka를 건너도 트레이스가 이어지는지 본다

주문(order) → Kafka `orders` 토픽 → 결제 컨슈머(payment). 앱에는 계측 코드가 없고 OTel 자바 에이전트만 붙인다.
에이전트가 producer/consumer 스팬을 부모-자식으로 잇는지 span link로 잇는지, 컨슈머가 일을 다른 스레드로 넘기면 어디서 끊기는지 본다.

글: `posts/CS/Observability/tracing-debugging/08_실습-2 - Kafka를 건너도 트레이스가 이어지는지 본다.html`

## 돌리기

```bash
cd labs/observability/tracing-02-kafka
docker compose up -d --build
curl -XPOST localhost:25003/orders -H 'Content-Type: application/json' -d '{"sku":"A-100","qty":1}'
python3 show-trace.py                       # 최근 주문 트레이스(링크 포함)
python3 show-trace.py '{name="orders receive"}'   # TraceQL 로 고른 최근 트레이스
docker compose down -v
```

- Grafana http://localhost:25000 (Explore → Tempo), Tempo API http://localhost:25001. 포트는 `.env`.
- 관측 스택은 `../stack/compose.yaml` 을 include 한다.

## 바꿔 가며 돌리는 값 (compose 환경변수)

| 변수 | 값 | 무엇이 바뀌나 |
|---|---|---|
| `RECEIVE_TELEMETRY` | `true` | payment 에 `OTEL_INSTRUMENTATION_MESSAGING_EXPERIMENTAL_RECEIVE_TELEMETRY_ENABLED`(2.32.0 에서 deprecated, 새 이름은 `otel.instrumentation.common.messaging.experimental.receive-telemetry.enabled`. 옛 이름도 동작했다). 컨슈머가 receive 스팬으로 새 트레이스를 시작하고 link 로 잇는다 |
| `SEMCONV_OPT_IN` | `messaging` | `OTEL_SEMCONV_STABILITY_OPT_IN`. 새 메시징 규약 이름(`send orders`, `messaging.operation.type`). 부모 + link 둘 다 건다 |
| `BATCH` | `true` | 배치 리스너(`@KafkaListener(batch = "true")`). process 스팬 하나에 link 여러 개 |
| `HANDOFF` | `inline`(기본) `executor` `queue` `queue-ctx` | 결제 처리를 넘기는 방식. `queue` 에서 트레이스가 끊긴다 |

```bash
RECEIVE_TELEMETRY=true docker compose up -d payment
HANDOFF=queue docker compose up -d payment && docker compose --profile load run --rm load && ./count.sh 75
# 배치: 메시지를 쌓아 두고 다시 띄운다
BATCH=true docker compose up -d payment; docker compose stop payment
for i in $(seq 1 10); do curl -s -XPOST localhost:25003/orders -H 'Content-Type: application/json' -d '{"sku":"A-100","qty":1}' & done; wait
docker compose start payment
```

`count.sh [초]` 는 최근 N초의 트레이스를 뿌리 스팬 이름별로 센다. `queue` 에서는 `payment / INSERT shop.payments` 가 주문 수만큼 나온다.

## 버전

| 부품 | 버전 | 비고 |
|---|---|---|
| Apache Kafka | 4.3.1 | `apache/kafka` 이미지, KRaft 단일 노드(브로커+컨트롤러). 4.3.2, 4.4.0 은 실습 시점(2026-10) RC |
| Spring Boot | 4.1.1 | `spring-boot-starter-kafka` |
| OTel Java agent | 2.32.0 | 메시징은 기본으로 v1.24.0 규약을 낸다 |
| 나머지 | 실습-1 과 같다 | Collector 0.162.0, Tempo 2.10.8, Grafana 13.2.3, k6 2.3.0 |

## 돌리다 만난 것

- 에이전트 기본값은 process 스팬을 publish 스팬의 **자식**으로 붙이고 링크는 없다. 규약상 단일 메시지면 부모로 삼아도 되지만(MAY), 메시지마다 생성 컨텍스트에 링크를 걸라(SHOULD)는 부분과 어긋난다.
- receive 스팬 길이는 poll 이 기다린 시간이다. 메시지 사이 간격이 2초면 receive 스팬도 2초가 된다.
- `Executors.newFixedThreadPool` 로 넘기면 끊기지 않는다(에이전트가 Executor 를 계측). 끊기는 건 직접 만든 큐에 객체만 넣을 때.
- Tempo 검색 API 는 `limit` 을 넘는 결과를 잘라 돌려주는데, 잘린 쪽이 최근 것일 수 있다(처음 스크립트가 엉뚱한 옛 트레이스를 집었다). `show-trace.py` 는 `limit=5000` 과 최근 10분 범위로 찾는다.
- 브로커가 하나뿐이라 오프셋·트랜잭션·share 코디네이터 내부 토픽의 복제 수를 compose 에서 1로 지정했다.
