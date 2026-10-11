# 집계와 분포 실습-4: 부하 생성기가 숨긴 지연을 다시 찾는다

같은 앱(`/work`, 2~4ms 응답)을 세 번 띄우고, `docker pause` 로 **30초마다 약 2초씩 세 앱을 동시에 얼린다**.
부하 생성기 셋이 각자 앱 하나를 맡아 같은 멈춤을 다르게 잰다.

| 앱 | 부하 | 모델 |
|---|---|---|
| `app-closed` | `k6/closed.js` VU 10개, 각자 100ms 간격 | 닫힌 모델 (응답을 받아야 다음 요청) |
| `app-open` | `k6/open.js` 초당 100건, VU 300개 | 열린 모델 (도착률 고정) |
| `app-starved` | `k6/open.js` 초당 100건, VU 20개 | 열린 모델인데 멈춤 동안 VU 가 바닥난다 |

서버 쪽은 스프링이 자동으로 거는 `http.server.requests` 타이머(버킷 켬)를 Prometheus 로 모은다.
k6 는 결과를 CSV 와 Prometheus 원격 쓰기로 내보낸다.

## 돌리기

```bash
cd labs/observability/agg-04-coordinated-omission
docker compose up -d --build
date +%s > out/start.txt
DURATION=5m docker compose --profile load up load-closed load-open load-starved > out/k6.log 2>&1 &
./scripts/pause-loop.sh                     # 15초 뒤부터 30초마다 2초씩 10번 얼린다. out/pauses.log
date +%s > out/end.txt                      # 부하가 끝난 뒤
python3 scripts/summary.py                  # k6 CSV 와 서버 버킷으로 p50~max 표, 0.1118초 경계를 넘은 서버 요청 수
./hdr/run.sh out/closed.csv 100             # HdrHistogram 2.2.2 로 닫힌 모델 결과 보정 (예상 간격 100ms)
./hdr/run.sh out/open.csv 10                # 열린 모델에 보정을 잘못 걸면 어떻게 되는지
docker compose --profile load down -v
```

- Grafana http://localhost:21000 → 대시보드 「실습-4 조율된 누락」
- Prometheus http://localhost:21090, app-closed http://localhost:21081/actuator/prometheus
- 포트는 `GRAFANA_PORT`, `PROM_PORT`, `APP_PORT` 로 바꾼다. 멈춤 주기는 `PERIOD`, `PAUSE`, `COUNT`, `FIRST`
- `summary.py` 의 서버 숫자는 앱이 기동한 뒤 쌓인 버킷 전체로 계산한다. 앱을 새로 띄우고 한 번만 돌려야 k6 와 같은 구간을 본다
- `out/` 의 CSV(각 40MB 남짓)와 시각 기록은 커밋하지 않는다. 이번 실행의 표는 `out/summary.txt`, `out/hdr.txt`, `out/k6-summary.txt`, `out/server-buckets.txt`,
  멈춘 시각은 부하 시작 기준 초로 옮긴 `out/pauses-relative.txt`

## 버전

Spring Boot 4.1.1 (Micrometer 1.17.1), Prometheus 3.15.0, Grafana 13.2.3, k6 2.3.0, HdrHistogram 2.2.2 (Java 21 단일 파일 실행).
실행 환경 Docker Desktop, Apple M5 Pro.

## 돌리다 만난 함정

- **서버 버킷 원자료를 저장하지 않고 스택을 내렸다.** 글 5절의 버킷 표(0.1118초 초과 1/5/2건)는 실행 직후 질의한 결과를
  `out/server-buckets.txt` 에 옮겨 적은 것이다. 지금의 `summary.py` 는 이 표를 같이 찍으니 실행 결과를 파일로 남겨 두면 된다.

- **k6 원격 쓰기의 `k6_http_req_duration_p99` 는 창 단위가 아니라 테스트 시작부터 누적한 값이다.** k6 소스
  (`internal/output/prometheusrw/remotewrite`)가 시계열마다 `TrendSink` 하나를 만들어 끝까지 계속 더한다.
  그래서 대시보드 1번 패널은 서버 쪽도 "기동부터 쌓인 버킷 전체"로 맞춰 그렸다.
- **k6 기본 요약에는 p99 가 없다.** 기본 trend 통계는 avg, min, med, max, p(90), p(95) 다. 열린 모델의 p95 가 670ms 로
  보여서야 이상하다는 걸 알 수 있었다. p99 는 `summary.py` 로 CSV 에서 계산했다.
- **`docker pause` 는 명령을 친 뒤 0.1초쯤 지나야 실제로 얼고, 녹이는 데도 0.1초쯤 걸린다.** `pauses.log` 에 네 시각을
  다 남겼다. pause 가 끝난 시각부터 unpause 가 끝난 시각까지는 2.13~2.16초였다.
- **HdrHistogram 보정은 예상 간격을 아는 경우에만 맞다.** 열린 모델 결과에 10ms 로 보정을 걸면 3만 건이 26만 건이 되고
  중앙값이 554ms 가 된다. 열린 모델은 이미 멈춤 동안의 요청을 다 쟀으니 보정할 누락이 없다.
