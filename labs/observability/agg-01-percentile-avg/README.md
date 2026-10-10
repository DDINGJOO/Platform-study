# 집계와 분포 실습-1: 인스턴스 세 대의 p99를 평균 내면 틀린다

같은 이미지를 세 번 띄우고(`app-a`, `app-b`, `app-c`) `app-c` 만 요청의 10%를 300~500ms로 늦춘다.
k6 로 부하를 준 뒤 세 가지 "전체 p99"를 비교한다.

| 값 | 어디서 |
|---|---|
| 인스턴스별 p99의 평균 | `avg(lab_work_seconds{quantile="0.99"})` (앱이 직접 계산한 클라이언트 백분위) |
| 버킷 합산 p99 | `histogram_quantile(0.99, sum by (le) (rate(http_server_requests_seconds_bucket{uri="/work"}[1m])))` |
| 실제 p99 | k6 가 잰 모든 요청의 p99 (`out/raw.csv` 로 다시 계산 가능) |

## 돌리기

```bash
cd labs/observability/agg-01-percentile-avg
docker compose up -d --build
docker compose --profile load run --rm load                 # 세 대가 같은 양(초당 60건, 3분)
docker compose restart app-a app-b app-c                    # 클라이언트 백분위 창을 비운다
docker compose --profile load run --rm -e C_EVERY=20 load   # app-c 가 5%만 받는다
docker compose --profile load down -v
```

- Grafana http://localhost:23000 → 대시보드 「실습-1 p99 평균 vs 버킷 합산」
- Prometheus http://localhost:23090, app-a http://localhost:23081/actuator/prometheus
- 포트는 `GRAFANA_PORT`, `PROM_PORT`, `APP_PORT` 로 바꾼다

## 버전

Spring Boot 4.1.1 (Micrometer 1.17.1, Prometheus 클라이언트 1.7.0), Prometheus 3.15.0, Grafana 13.2.3, k6 2.3.0

## 돌리다 만난 함정

- **버킷을 켜면 클라이언트 백분위가 사라진다.** `percentiles` 와 `percentiles-histogram` 을 같은 타이머에 켜면
  `/actuator/prometheus` 에 `quantile` 줄이 없다. Micrometer 1.13 부터 쓰는 새 Prometheus 레지스트리
  (`io.micrometer.prometheusmetrics.PrometheusMeterRegistry`)는 버킷이 있으면 histogram 으로, 없을 때만
  summary(quantile 포함)로 내보낸다. 그래서 클라이언트 백분위는 `lab.work` 라는 타이머를 따로 만들어 켰다.
- **`percentiles-histogram.http.server.requests` 는 `http.server.requests.active` 에도 걸린다.** 스프링 부트는
  미터 이름을 점 단위로 잘라 가며 앞부분이 맞는 설정을 찾는다. LongTaskTimer 에 버킷 29줄이 따라 나왔다.
- 타이머 기본 버킷 범위는 1ms~30s(Micrometer `AbstractTimerBuilder`), `/work` 하나에 버킷 68개 + `+Inf`.
- 클라이언트 백분위는 HdrHistogram(유효숫자 1자리) 근사값이고 최근 2분(버퍼 3칸)짜리 창이다.
  실제 61.5ms인 p99를 59.8ms로 보고했다.
