# rel-02-small-samples

글: `posts/CS/Observability/reliability-design/07_실습-2 - 표본 수와 분포 모양이 경고를 몇 번 틀리게 하는지 센다.html`
개념 글: 같은 폴더의 2편(적은 표본), 3편(평균+3σ)

같은 에러율에서 초당 요청 수만 바꿔 burn rate 경고가 몇 번 켜지고 꺼지는지 세고,
같은 지연 데이터에 평균+3σ 문턱을 걸어 몇 %가 넘는지 센다.

## 구성

| 서비스 | 내용 | 호스트 포트 |
|---|---|---|
| `app` | 파이썬 표준 라이브러리 앱(`app/app.py`). 서비스 여러 개를 한 프로세스가 흉내 낸다 | 32080 |
| `prometheus` | 2초 수집·2초 평가. burn rate 기록 규칙과 경고 규칙(`prometheus/rules.yml`) | 32090 |
| `grafana` | Explore 로 그래프를 본다(로그인 없음) | 32030 |
| `load` (profile) | 열린 루프 부하 생성기(`loadgen/loadgen.py`). 요청마다 CSV 한 줄 | |

앱 서비스 (compose.yaml 의 `APP_CONFIG`)

| 서비스 | 에러율 | 초당 요청 | 뜻 |
|---|---|---|---|
| `e1`, `e10`, `e100` | 1% | 1, 10, 100 | SLO 99.9% 기준 burn rate 10. 6배 단은 켜져 있어야 맞고, 14.4배 단은 꺼져 있어야 맞다 |
| `h1`, `h10`, `h100` | 0.1% | 1, 10, 100 | burn rate 1. 둘 다 꺼져 있어야 맞다 |
| `lat-ln` | 0 | 50 | 지연 로그정규(중앙값 40ms, σ_log 0.6) |
| `lat-bi` | 0 | 50 | 지연 두 봉우리(95% 중앙값 20ms + 5% 중앙값 400ms) |

## 시간 압축

경고 창을 SRE 워크북 권고의 30분의 1로 줄였다(1h→2m, 5m→10s, 6h→12m, 30m→1m).
창 안 요청 수도 30분의 1이 되므로, 초당 1건 서비스는 **실제 창 기준 시간당 120건 서비스**와 표본 크기가 같다.
초당 10건은 시간당 1,200건, 초당 100건은 시간당 12,000건에 해당한다.
60분 실행 중 앞 12분(가장 긴 창이 찰 때까지)을 빼고 48분을 센다 = 실제 창 기준 24시간.

## 돌리기

```bash
cd labs/observability/rel-02-small-samples
docker compose up -d
caffeinate -dims docker compose --profile load run --rm load  # 60분. -i 만으로는 잠든 적이 있다. 끝나면 out/run.csv
python3 analyze.py out/run.csv --prom http://localhost:32090 | tee out/analyze.txt
docker compose down -v
```

계산만 하는 스크립트(컨테이너 없음, 표준 라이브러리만)

```bash
python3 calc/binom.py        # 이항 신뢰구간, 에러 예산 건수
python3 calc/burn_sim.py 50 0.001                 # 30일, 건강한 서비스의 오탐 횟수
python3 calc/burn_sim.py 50 0.01 30 120,1200,12000   # 이 실습 조건의 예측
python3 calc/sigma.py        # 평균+3σ, n 과 n-1, 시간 기준과 요청 기준, 몬테카를로
```

## 버전

| 부품 | 버전 |
|---|---|
| Prometheus | 3.15.0 |
| Grafana | 13.2.3 |
| Python | 3.13 (python:3.13-alpine) |

## 함정 (돌리다 만난 것)

- 에러 카운터를 0으로 미리 만들어 두지 않으면, 첫 에러가 나는 순간 시계열이 생겨서 `rate()` 가 그 첫 건을 세지 못한다. 앱이 시작할 때 서비스마다 `code="500"` 시계열을 0으로 만든다(`zero_init`).
