# SLO와 경고 실습-1: SLO 하나로 burn rate 경고를 만들고 실제로 울린다

Sloth 로 SLO 정의(`sloth/slo.yaml`)에서 다중 창·다중 burn rate 기록 규칙과 경고 규칙을 만들고,
Prometheus + Alertmanager 에 넣은 뒤 앱에 에러를 주입해 경고가 울리고 웹훅으로 도착하는 시각을 잰다.

## 30일을 하루로 줄였다 (중요)

30일 SLO 를 그대로 쓰면 가장 긴 창이 3일이라 실습에서 기다릴 수 없다.
Sloth 의 `AlertWindows` 사용자 정의 창(`sloth/windows/lab-1d.yaml`)으로 **SLO 기간과 모든 창을 1/30** 로 줄였다.
`errorBudgetPercent` 는 그대로라서 burn rate 계수(14.4, 6, 3, 1)는 30일 기본값과 같다.

| 단 | 30일 기본(Sloth google-30d) | 실습(1/30) | burn rate |
|---|---|---|---|
| page 빠른 | 1h / 5m | 2m / 10s | 14.4 |
| page 느린 | 6h / 30m | 12m / 1m | 6 |
| ticket 빠른 | 1d / 2h | 48m / 4m | 3 |
| ticket 느린 | 3d / 6h | 2h24m / 12m | 1 |

줄이지 **못한** 것: 스크레이프 간격(2초), 규칙 평가 간격(5초), Alertmanager 의 `group_wait` 30초,
`group_interval` 5분. 이 고정 지연은 실습에서 상대적으로 30배 크게 보인다. 짧은 창에 들어가는 요청 수도
30분의 1(10초 창에 약 400건)이라 에러 비율이 운영보다 훨씬 출렁인다.

## 돌리기

```bash
cd labs/observability/slo-01-burn-rate
# 규칙 다시 만들기(결과는 prometheus/slo-rules.yaml 에 이미 들어 있다)
docker run --rm -v $PWD/sloth:/sloth ghcr.io/slok/sloth:v0.16.0 generate \
  -i /sloth/slo.yaml --slo-period-windows-path=/sloth/windows --default-slo-period=1d \
  > prometheus/slo-rules.yaml

docker compose up -d --build
docker compose --profile load up -d load                     # 초당 40건, 180분(RATE·DURATION 환경변수로 변경)
python3 scripts/watch-alerts.py                              # 경고 상태가 바뀔 때마다 시각과 burn rate 출력
docker compose logs -f webhook                               # Alertmanager 가 보낸 알림이 도착한 시각

# 에러 주입(앱 재시작 없이 바뀐다)
curl -X POST 'localhost:24080/chaos?errorRate=0.01'   # 1%: burn rate 10
curl -X POST 'localhost:24080/chaos?errorRate=0.1'    # 10%: burn rate 100
curl -X POST 'localhost:24080/chaos?errorRate=0'      # 복구

docker compose --profile load down -v
```

- Grafana http://localhost:24030 → 대시보드 SLO / SLO burn rate
- Prometheus http://localhost:24090/alerts, Alertmanager http://localhost:24093
- 주입 전에 정상 트래픽을 최소 48분(티켓 빠른 창 길이) 흘려 두었다. 긴 창이 덜 찬 상태에서 주입하면 경고가 일찍 울린다(글 참고)

## 버전

| 부품 | 버전 |
|---|---|
| Sloth | v0.16.0 (`ghcr.io/slok/sloth`) |
| Prometheus | 3.15.0 |
| Alertmanager | 0.34.1 |
| Grafana | 13.2.3 |
| k6 | 2.3.0 |
| Spring Boot | 4.1.1 (Micrometer 1.17.1, Java 21) |

## 함정 (돌리다 만난 것)

- **에러가 한 번도 안 나면 SLI 가 0 이 아니라 "없음"이다.** Micrometer 는 5xx 응답이 처음 나올 때
  `status="500"` 시계열을 만든다. 그 전에는 `sum(rate(...{status=~"5.."}[..]))` 결과가 비어서
  Sloth 기록 규칙 전체가 비고, 오차 예산 잔량도 "No data" 가 된다. `error_query` 끝에 `or vector(0)` 을 붙였다.
- Sloth 가 만든 경고에는 `for` 가 없다. pending 단계 없이 첫 평가에서 바로 firing 이 되고,
  짧은 창이 문턱 아래로 한 번 내려가면 바로 풀렸다가 다시 울린다(실습에서 9초짜리 끊김이 한 번 있었다).
- k6 실행 시간을 compose 환경변수로 넘기지 않으면 스크립트 기본값으로 끝난다. 처음 실행에서 이것 때문에 10% 주입을 멈춘 뒤 경고 해제를 기다리던 중(07:52:51) 부하가 끊겼다(지금 compose 는 고쳤다).
- 주입 전에 Docker Desktop 이 다른 작업으로 바쁠 때 스크레이프가 2초 타임아웃을 넘겨 `up=0` 이 여러 번 났다. 주입 구간에는 없었다.
- `sloth generate -o -` 는 `open : no such file or directory` 로 실패했다. `-o` 를 빼면 표준 출력으로 나온다.
- Prometheus 규칙 평가 기본 간격은 1분이다. 10초 창을 쓰려면 `evaluation_interval` 을 줄여야 한다.
