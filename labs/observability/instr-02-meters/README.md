# 계측 라이브러리 실습-2: 한 요청에 Timer, DistributionSummary, LongTaskTimer를 걸어 본다

글: `posts/CS/Observability/instrumentation/06_실습-2 - 한 요청에 Timer, DistributionSummary, LongTaskTimer를 걸어 본다.html`

`POST /reports?ms=N` 하나에 미터 네 개를 건다.

| 미터 | 이름 | 설정 |
|---|---|---|
| Timer | `report.duration` | `publishPercentileHistogram()` 버킷 내보내기 |
| Timer | `report.duration.pct` | `publishPercentiles(0.5, 0.99)` 앱이 백분위 계산 |
| DistributionSummary | `report.size` | baseUnit `rows` |
| LongTaskTimer | `report.active` | |

`POST /reports/leaky` 는 LongTaskTimer 를 시작만 하고 멈추지 않는다.

## 돌리기

```bash
cd labs/observability/instr-02-meters
docker compose up -d --build
curl -s -XPOST 'localhost:22180/reports?ms=20000' &        # 20초짜리 보고서
sleep 5; curl -s localhost:22180/actuator/prometheus | grep -E '^report_(active|duration_seconds_(count|sum|max))'
curl -s -XPOST localhost:22180/reports/leaky               # stop() 을 빼먹은 작업
docker compose --profile load run --rm load                # k6 60초, 2% 는 1~2초짜리
# Prometheus: http://localhost:22190
#   histogram_quantile(0.99, rate(report_duration_seconds_bucket[1m]))
docker compose down -v
```

## 버전

Spring Boot 4.1.1 (Micrometer 1.17.1), Prometheus 3.15.0, k6 2.3.0

## 돌리다 만난 것

- 타이머 기본 버킷 범위는 1ms~30s 로 버킷 68개 + `+Inf` 다(`AbstractTimerBuilder`).
  Micrometer 문서의 "1ms~1분, 73개" 와 다르다.
- 클라이언트 백분위는 시간 창으로 계산돼 부하가 끝나고 52초 뒤 0 이 됐다. Prometheus 레지스트리는 expiry 를 step(기본 1분)으로
  두고 3칸으로 나눠 20초마다 넘기므로, 마지막 기록이 40~60초 뒤 빠진다.
- LongTaskTimer 는 기본 상태에서 summary 로 나오고 `_count` 가 진행 중인 개수다. `publishPercentileHistogram` 을 켜면 gauge histogram 으로 나간다(소스 확인, 실행 안 함).
  버킷은 누적이라 나중에 `increase(...[10m])` 로 다시 계산할 수 있다.
- 스프링이 `http.server.requests.active` 라는 LongTaskTimer 를 이미 걸어 둔다. 진행 중에는 `uri="UNKNOWN"` 이다.
- `http.server.requests` 는 기본으로 버킷을 내보내지 않는다. `management.metrics.distribution.percentiles-histogram.http.server.requests=true` 를 켜야 한다.
