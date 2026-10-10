# 계측 라이브러리 실습-4: MeterFilter로 태그 상한을 걸고 넘친 값을 쫓는다

글: `posts/CS/Observability/instrumentation/08_실습-4 - MeterFilter로 태그 상한을 걸고 넘친 값을 쫓는다.html`

`FilterConfig` 가 MeterFilter 빈 네 개를 `@Order` 순서로 건다.

1. `deny(user_id 태그가 있으면)`
2. `renameTag("login", "uid", "user_id")` (거부보다 뒤에 걸었다)
3. `accept(item 이 vip- 로 시작하면)`
4. `maximumAllowableTags("item.views", "item", 50, 거부하며 횟수 세기)` → `meter_filter_denied_total`

그리고 `management.metrics.web.client.max-uri-tags=20` 으로 스프링 부트의 클라이언트 URI 상한을 낮췄다.

| 엔드포인트 | 하는 일 |
|---|---|
| `GET /items/{id}` | `item.views{item=<id>}` 증가 |
| `POST /fanout?n=N&prefix=P` | RestClient 로 자기 `/items/P0..` 를 N 번 호출. URI 를 문자열로 이어 붙인다 |
| `POST /login?uid=U` | `login{uid=U}` 증가 |
| `POST /late-filter` | 기동 뒤에 `denyNameStartsWith("item.views")` 를 건다 |

## 돌리기

```bash
cd labs/observability/instr-04-meterfilter
docker compose up -d --build
curl -s -XPOST 'localhost:22380/fanout?n=80'
curl -s -XPOST 'localhost:22380/fanout?n=5&prefix=vip-'
curl -s localhost:22380/actuator/prometheus | grep -c '^item_views_total{'
curl -s localhost:22380/actuator/prometheus | grep -E '^meter_filter_denied|^login'
curl -s -XPOST 'localhost:22380/login?uid=alice'
curl -s -XPOST localhost:22380/late-filter
docker compose logs app | grep WARN
docker compose down -v
```

## 버전

Spring Boot 4.1.1 (Micrometer 1.17.1), Prometheus 3.15.0

## 돌리다 만난 것

- Micrometer 의 `MeterFilter.maximumAllowableTags` 는 상한에 닿아도 로그를 남기지 않는다. 스프링 부트의
  `MaximumAllowableTagsMeterFilter`(URI 상한)는 경고를 **한 번만** 남긴다.
- 거부된 미터는 캐시되지 않아 증가 호출마다 필터를 다시 탄다. 그래서 거부 횟수 = 잃어버린 증가 횟수다.
- 모든 필터의 `map`(renameTag 등)이 먼저 돌고, 그다음 `accept` 를 순서대로 묻는다. 거부를 이름 바꾸기보다 앞에 걸어도 바뀐 이름으로 거부된다.
- 기동 뒤에 건 거부 필터는 이미 있는 미터를 지우지 못하고, 앞선 필터가 ACCEPT/DENY 를 먼저 내면 묻지도 않는다.
