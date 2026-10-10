# 집계와 분포 실습-3: 히스토그램 점을 눌러 트레이스로 넘어간다

스프링 부트 앱 하나가 Micrometer 로 지연 히스토그램을 내보내고, Micrometer Tracing(OTel 브리지)으로 같은 요청의
트레이스를 Tempo 에 보낸다. Prometheus 는 OpenMetrics 형식으로 긁으면서 버킷마다 붙은 exemplar(trace_id)를 저장하고,
Grafana 는 그 점을 눌러 Tempo 트레이스를 연다. 자바 에이전트는 쓰지 않는다.

`/work` 는 요청의 89%를 20~60ms(`kind=fast`), 10%를 300~500ms(`slow`), 1%를 1~2초(`very_slow`)로 잔다.
`kind` 는 자식 스팬 `lab.work` 의 속성으로 남는다.

## 단계 네 개

| 단계 | 설정 | 끊으면 |
|---|---|---|
| 앱이 exemplar 를 단다 | Micrometer Tracing 이 있으면 스프링 부트가 자동 연결. 샘플링된 스팬만 | `management.tracing.sampling.probability` 기본 0.1 |
| OpenMetrics 로 긁는다 | Prometheus 3 기본 협상 순서가 OpenMetrics 우선 | 텍스트 0.0.4 로만 긁으면 exemplar 0개 |
| Prometheus 가 저장한다 | `--enable-feature=exemplar-storage` (원형 버퍼, 기본 100,000개) | 플래그가 없으면 exemplar 0개, 오류 없음 |
| Grafana 가 링크를 건다 | 데이터 소스 `exemplarTraceIdDestinations` + 패널 쿼리 `exemplar: true` | 점은 쿼리 스위치, 링크는 데이터 소스 설정이 정한다(링크 쪽은 실험하지 않음) |

## 돌리기

```bash
cd labs/observability/agg-03-exemplar
docker compose up -d --build
docker compose --profile load run --rm load          # 초당 20건, 3분
# Grafana http://localhost:23300 → 대시보드 「실습-3 exemplar」 → 점에 마우스 → Query with Tempo

# 점 클릭을 자동으로 찍기 (Playwright 필요)
python scripts/exemplar-click.py "http://localhost:23300/d/agg03/x?orgId=1&from=now-5m&to=now&kiosk&viewPanel=panel-1" tip.png trace.png

# 단계 하나씩 빼 보기: 플래그 없는 Prometheus, 텍스트 형식만 긁는 Prometheus 를 옆에 붙인다
docker compose -f compose.yaml -f experiments/compose.yaml up -d prom-noflag prom-text
docker compose --profile load run --rm -e DURATION=1m load
# exemplar 수 비교 (23390 본 Prometheus, 23391 플래그 없음, 23392 텍스트 형식)
for p in 23390 23391 23392; do curl -s -G localhost:$p/api/v1/query_exemplars \
  --data-urlencode 'query=http_server_requests_seconds_bucket{uri="/work"}' \
  --data-urlencode start=$(($(date +%s)-90)) --data-urlencode end=$(date +%s); echo; done

# 샘플링 10%로 다시 띄우기
TRACING_PROBABILITY=0.1 docker compose up -d app

docker compose -f compose.yaml -f experiments/compose.yaml --profile load down -v
```

포트: Grafana 23300, Prometheus 23390, Tempo 23320, 앱 23381 (`GRAFANA_PORT` 등으로 바꾼다)

## 버전

Spring Boot 4.1.1 (Micrometer 1.17.1, Prometheus 클라이언트 1.7.0, `spring-boot-starter-opentelemetry`),
Prometheus 3.15.0, Tempo 2.10.8, Grafana 13.2.3, k6 2.3.0

## 돌리다 만난 함정

- `spring-boot-starter-opentelemetry` 에는 OTLP 지표 레지스트리가 딸려 온다. 지표를 Prometheus 로만 볼 거면
  `management.otlp.metrics.export.enabled: false`.
- OTLP 트레이스 내보내기는 `management.opentelemetry.tracing.export.otlp.endpoint` 를 줘야 켜진다(스프링 부트 4 이름).
- exemplar 는 버킷마다 하나뿐이고, 한 번 단 exemplar 는 최소 7초 동안 바뀌지 않는다. 그 위에 시계열마다
  후보를 90ms 에 하나만 받는 문이 있고(모든 칸이 차 있으면 가장 오래된 견본이 7초를 넘길 때까지 닫힘),
  70초가 넘은 견본은 내보낼 때 빠진다(Prometheus 자바 클라이언트 `ExemplarSampler`, `ExemplarSamplerConfig`).
  3분 동안 3,601건을 보낸 실행에서 버킷 줄 exemplar 는 228개 저장됐다.
- 샘플링 100%면 Prometheus 가 5초마다 긁는 `/actuator/prometheus` 요청도 트레이스로 남는다.
- 같은 Docker Desktop VM 에서 다른 컨테이너가 CPU 를 많이 쓰는 동안 돌리면 `kind=fast` 요청이 수백 ms~수 초
  걸린다. 이 실습의 첫 실행이 그랬고, 글에서는 그 트레이스를 exemplar 로 찾아간 과정을 그대로 썼다.
