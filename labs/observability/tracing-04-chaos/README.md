# 추적과 디버깅 실습-4: 지연을 주입하고 트레이스로 원인을 찾는다

order → inventory → **Toxiproxy** → Postgres, order → payment.
재고 DB 경로에 지연을 넣어 트레이스에서 원인 스팬을 찾고, W3C baggage 의 `chaos` 깃발이 실린 요청만 결제에서 실패시킨다.

글: `posts/CS/Observability/tracing-debugging/10_실습-4 - 지연을 주입하고 트레이스로 원인을 찾는다.html`

## 돌리기

```bash
cd labs/observability/tracing-04-chaos
docker compose up -d --build

# 1) 지연: 재고 DB 경로에 300ms
curl -XPOST localhost:25005/proxies/inventory-db/toxics \
  -d '{"name":"db-latency","type":"latency","stream":"downstream","attributes":{"latency":300,"jitter":0}}'
docker compose --profile load run --rm -e DURATION=30s load
python3 breakdown.py 50          # 최근 50초 주문 트레이스의 스팬별 중앙값·p90
curl -XDELETE localhost:25005/proxies/inventory-db/toxics/db-latency

# 2) baggage 깃발로 결제 실패 주입
curl -XPOST localhost:25003/orders -H 'Content-Type: application/json' \
     -H 'baggage: chaos=payment-fail' -d '{"sku":"C-300","qty":1}'          # 502
python3 show-trace.py '{span.chaos.flag = "payment-fail"}'

# 3) 입구에서 깃발 검문
BAGGAGE_GUARD=true CHAOS_TOKEN=lab-token docker compose up -d order
curl ... -H 'baggage: chaos=payment-fail'                                    # 200 (깃발 버림)
curl ... -H 'X-Chaos-Token: lab-token' -H 'baggage: chaos=payment-fail'     # 502

docker compose --profile load down -v
```

포트(`.env`): Grafana 25000, Tempo 25001, 주문 25003, Toxiproxy API 25005.

## 이 폴더에서 바꾼 것 (실습-1 앱 대비)

| 파일 | 내용 |
|---|---|
| `app/build.gradle` | `org.postgresql:postgresql`, `io.opentelemetry:opentelemetry-api` 추가 |
| `app/.../application-inventory.yml` | 재고만 Postgres(`toxiproxy:15432`) |
| `app/.../data.sql` | Postgres 문법(`on conflict do nothing`) |
| `app/.../ChaosFilter.java` | payment. `Baggage.current()` 의 `chaos` 값이 `payment-fail` 이면 503, `payment-slow` 면 2초 지연. 스팬에 `chaos.flag`, `chaos.injected` |
| `app/.../BaggageGuard.java` | order. `SHOP_BAGGAGE_GUARD=true` 면 토큰(`X-Chaos-Token`) 없는 `chaos` 키를 뺀 baggage 로 바꿔 끼운다. 스팬에 `chaos.rejected` |
| `toxiproxy.json` | `inventory-db` 프록시 (15432 → postgres:5432) |

## 버전

| 부품 | 버전 |
|---|---|
| Toxiproxy | 2.12.0 (`ghcr.io/shopify/toxiproxy`) |
| PostgreSQL | 18.6-alpine |
| pgjdbc / HikariCP | 42.7.13 / 7.0.2 (Spring Boot 4.1.1 이 정한 버전) |
| opentelemetry-api | 1.62.0 (앱), 에이전트 2.32.0 안의 SDK 는 1.66.0 |

## 돌리다 만난 것

- 한가할 때(요청 간격 > 500ms)는 300ms 지연이 600ms 로 보인다. HikariCP 가 500ms 넘게 쉰 커넥션을 `isValid()` 로 확인하고,
  pgjdbc 는 빈 쿼리를 보낸다. 에이전트는 이걸 `db.statement` 가 빈 JDBC 스팬(이름 `shop`)으로 남긴다.
- TraceQL `quantile_over_time` 은 버킷 근사라 스팬 실측(약 0.30s)보다 크게(0.38s) 나왔다. 어디가 느린지 고를 때만 쓴다.
- 에이전트는 들어온 baggage 를 그대로 하위로 넘긴다(이메일 같은 값, 7KB 값도). 100개를 보내면 64개만 넘어간다(SDK 의 W3C 한도).
  9,000바이트 헤더는 톰캣이 400 으로 거절했다(요청 헤더 8KB 제한).
- Docker Desktop 을 여러 실습이 같이 쓰는 동안 JVM 기동이 수 분씩 걸린 적이 있다. 글의 숫자는 부하가 가라앉은 뒤 지연 없음/300ms 를 연달아 돌린 실행이다.
