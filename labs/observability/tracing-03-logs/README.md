# 추적과 디버깅 실습-3: 로그의 trace_id에서 트레이스를 바로 연다

실습-1 의 주문·재고·결제 서비스에 로그 몇 줄과 로그 패턴만 더했다. 로그는 stdout → Grafana Alloy(도커 소켓) → Loki,
트레이스는 에이전트 → Collector → Tempo. Grafana 에서 로그 → 트레이스(derived field), 트레이스 → 로그(trace to logs)를 잇는다.

글: `posts/CS/Observability/tracing-debugging/09_실습-3 - 로그의 trace_id에서 트레이스를 바로 연다.html`

## 돌리기

```bash
cd labs/observability/tracing-03-logs
PAYMENT_FAIL_RATE=0.3 docker compose up -d --build
docker compose --profile load run --rm -e DURATION=20s load
python3 log-vs-span.py 900      # 결제 에러 로그 시각과 그 로그를 남긴 스팬 구간 대조
docker compose down -v
```

- Grafana http://localhost:25000 → Explore → Loki: `{service_name="order"} |= "결제 실패"` → 줄 펼치기 → "Tempo에서 트레이스 열기"
- Tempo 트레이스에서 스팬 펼치기 → "Logs for this trace"
- 포트는 `.env` (Loki 25004, Tempo 25001)
- 로그를 OTLP 로도 보내 보려면 `LOGS_EXPORTER=otlp` (stdout 수집과 겹쳐 같은 로그가 두 번 들어간다)

## 이 폴더에서 바꾼 것

| 파일 | 내용 |
|---|---|
| `app/` | 실습-1 앱 복사본. 주문·결제에 로그 몇 줄, `logging.pattern.level` 에 `trace_id=%X{trace_id:-} span_id=%X{span_id:-}` |
| `compose.yaml` | stack/ 을 include 하지 않고 서비스 정의를 옮겨 왔다. Grafana 데이터소스와 Collector 설정이 달라서다(include 로는 덮어쓸 수 없다). tempo/prometheus 설정은 `../stack/` 파일을 그대로 마운트 |
| `grafana/provisioning/` | Loki 데이터소스(derived field), Tempo 의 `tracesToLogsV2` |
| `otel-collector.yaml` | stack/ 설정에 logs 파이프라인(→ Loki `/otlp`) 추가 |
| `alloy.alloy`, `loki.yaml` | 로그 수집과 저장 |

## 버전

| 부품 | 버전 |
|---|---|
| Grafana Loki | 3.7.8 |
| Grafana Alloy | 1.20.1 |
| 나머지 | 실습-1 과 같다 (Spring Boot 4.1.1, OTel agent 2.32.0, Tempo 2.10.8, Grafana 13.2.3) |

## 돌리다 만난 것

- **trace to logs 가 빈 화면.** Grafana 는 스팬 시작·끝을 밀리초로 내림해 Loki 에 묻는다(`spanStartTimeShift`/`spanEndTimeShift` 기본 0).
  스팬 끝을 밀리초로 내린 경계와 실제 끝 사이에 찍힌 로그가 빠진다. 결제 에러 로그 101줄 중 38줄이 그랬다. ±1s 로 넓혀서 해결.
  저장소의 datasources.yaml 에는 고친 뒤의 ±1s 가 들어 있다. 빈 화면을 재현하려면 두 줄을 지우고 `docker compose restart grafana`.
- **Alloy 가 Loki 자기 로그까지 가져왔다.** 이 설정에서 `loki.source.docker` 의 `relabel_rules` 에 넣은 keep 규칙으로는 Loki 로그가 걸러지지 않았다(원인은 확인 못 함).
  `discovery.relabel` 의 `output` 을 `targets` 로 넘기고, compose 프로젝트 라벨 필터도 넣었다(도커 소켓은 다른 실습 컨테이너도 다 보인다).
- Loki 의 로그 시각은 앱이 본문에 쓴 시각보다 중앙값 0.99ms 늦게 나왔다. 본문 시각이 밀리초로 잘려 있어 평균 0.5ms 는 절단 오차라 실제 차이는 더 작다.
- OTLP 로 보낸 로그는 본문에 trace_id 가 없다(structured metadata 로 붙는다). 정규식 derived field 는 그 로그에 링크를 못 만든다.
