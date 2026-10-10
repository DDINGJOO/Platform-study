# 계측 라이브러리 실습-1: 같은 카운터가 Prometheus와 OTLP로 동시에 나간다

글: `posts/CS/Observability/instrumentation/05_실습-1 - 같은 카운터가 Prometheus와 OTLP로 동시에 나간다.html`

스프링 부트 앱 하나에 Micrometer 레지스트리 두 개(Prometheus, OTLP)를 넣는다. 부트가
`CompositeMeterRegistry` 를 만들어 주입하고, 같은 `Counter`/`Timer`/`DistributionSummary` 가

- 경로 A: Prometheus 가 `/actuator/prometheus` 를 긁는다
- 경로 B: 앱이 OTLP/HTTP 로 Collector 에 밀고, Collector 가 Prometheus 의 OTLP 수신 엔드포인트로 넘긴다

두 길로 같은 Prometheus 에 들어간다. 이름·단위·접미사가 어떻게 달라지는지 본다.

## 돌리기

```bash
cd labs/observability/instr-01-composite
docker compose up -d --build
curl -s localhost:22080/registries                       # 주입된 레지스트리 확인
for i in $(seq 1 10); do curl -s -XPOST 'localhost:22080/orders?region=seoul' >/dev/null; done
for i in $(seq 1 5);  do curl -s -XPOST 'localhost:22080/orders?region=busan' >/dev/null; done
curl -s localhost:22080/actuator/prometheus | grep -E '^(orders|checkout|order_payload)'   # 경로 A 원문
sleep 20
docker compose logs otel-collector --no-log-prefix | python3 show-otlp.py orders checkout order.payload   # 경로 B 원문
# Prometheus: http://localhost:22090  쿼리 {__name__=~"orders.*"}
docker compose down -v
```

포트: 앱 22080, Prometheus 22090 (`APP_PORT`, `PROM_PORT` 로 바꾼다).

## 버전

| 부품 | 버전 |
|---|---|
| Spring Boot | 4.1.1 (Micrometer 1.17.1, Prometheus Java client 1.7.0) |
| OTel Collector contrib | 0.162.0 |
| Prometheus | 3.15.0 (`--web.enable-otlp-receiver`) |

## 돌리다 만난 것

- `orders.created` 카운터가 스크레이프에서는 `orders_total` 이 된다. Prometheus 자바 클라이언트 1.7.0 의
  `PrometheusNaming.sanitizeMetricName` 이 예약 접미사(`_total`, `_created`, `_bucket`, `_info`)를 떼어 낸다.
  (`_created` 제거는 1.5.0 에 있었고 1.6.0 에서 빠졌다가 1.7.0 에서 돌아왔다. 클라이언트 버전에 따라 이름이 다를 수 있다.)
  OTLP 경로로 들어온 같은 카운터는 `orders_created_total` 이다.
- OTLP 레지스트리의 기본 시간 단위는 밀리초다(`management.otlp.metrics.export.base-time-unit`).
  같은 Timer 가 `checkout_latency_seconds_*` 와 `checkout_latency_milliseconds_*` 두 벌로 들어온다.
- max 의 시간 창이 다르다. 스크레이프 쪽 `_max` 는 마지막 요청 뒤 약 3분, OTLP 쪽은 30초 안에 0 이 됐다.
  두 레지스트리 모두 `step` 을 expiry 로 쓰고(Prometheus 기본 1분, 이 실습의 OTLP 10s), `TimeWindowMax` 는
  3칸 고리를 expiry 마다 넘겨 값이 step 의 2~3배 동안 남는다.
- OTLP 레지스트리는 `service.instance.id` 를 보내지 않아 OTLP 경로 시계열에는 `instance` 라벨이 없다.
