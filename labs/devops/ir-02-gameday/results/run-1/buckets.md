# run-1: 주입 중 110초 동안의 주문 응답 시간 분포

구간: T+00:06 ~ T+01:56 (완화 전). Prometheus 에서 이 구간 끝 시각에 `increase(...[110s])` 로 셌다(increase 의 외삽 때문에 소수점이 생길 수 있다).

| 응답 시간 | 건수 |
|---|---|
| 0.5초 이하 | 0 |
| 0.5 ~ 0.75초 | 282 |
| 0.75 ~ 1.0초 | 892 |
| 1.0 ~ 1.5초 | 1,020 |
| 1.5초 초과 | 0 |
| 합계 | 2,195 |

- 같은 구간 503(재고 호출 timeout) 건수: 672.7 → 약 673건
- 따라서 1초를 넘긴 1,020건 중 약 347건은 실패하지 않고 성공했다. `urllib` 의 timeout 은 소켓 동작마다 걸리기 때문이다.
- `histogram_quantile(0.99, ...)` 는 1.0~1.5초 버킷 안을 선형 보간해 1.489s 를 냈다. 실제로 1.5초를 넘은 응답은 없다.

쿼리:
```
sum by (le) (increase(http_server_duration_seconds_bucket{service="order"}[110s]))
sum(increase(http_server_requests_total{service="order",code="503"}[110s]))
sum(increase(upstream_requests_total{outcome="timeout"}[110s]))
```
