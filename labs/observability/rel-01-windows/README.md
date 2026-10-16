# rel-01-windows

글: `posts/CS/Observability/reliability-design/06_실습-1 - 같은 장애 기록을 네 가지 창으로 판정한다.html`
개념 글: 같은 폴더의 1편(측정 창과 분모)

하루를 24분으로 압축해 사용자·봇·헬스체크 트래픽을 같이 흘리고, 같은 장애를 새벽과 피크에 넣어
시간 기준과 요청 기준 가용성, 분모를 바꿨을 때의 SLI 를 잰다. 합성 1년 기록은 컨테이너 없이 계산한다.

## 구성

| 서비스 | 내용 | 호스트 포트 |
|---|---|---|
| `app` | 파이썬 표준 라이브러리 앱(`app/app.py`). `/api/checkout` 은 평소 0.2% 일시 실패, `/health` 는 늘 200, 나머지 경로는 404 | 32180 |
| `prometheus` | 2초 수집 | 32190 |
| `grafana` | Explore(로그인 없음) | 32130 |
| `day` (profile) | 압축한 하루를 흘리는 부하 생성기(`loadgen/day.py`). 요청마다 CSV 한 줄 | |

압축: 실제 1초 = 압축 1분, 하루 = 1,440초(24분). 트래픽 곡선은 `loadgen/curve.py`(새벽 3~4시 피크의 6%, 오후 2시 피크).
사용자 트래픽은 피크 초당 40건, 봇은 초당 2건 일정, 헬스체크는 3대가 초당 1번씩.
사용자 클라이언트는 5xx 를 받으면 0.2초 뒤 한 번 재시도한다.

## 돌리기

```bash
cd labs/observability/rel-01-windows
docker compose up -d

# 하루 A: 새벽 1시에 60분(실제 60초) 장애
caffeinate -dims docker compose --profile load run --rm day --out /out/day-night.csv --outage-at 1 --outage-min 60
python3 analyze_day.py out/day-night.csv --outage-at 1 --outage-min 60
python3 prom_sli.py --prom http://localhost:32190 --at $(date +%s)      # 하루가 끝난 직후에 친다

# 하루 B: 오후 2시에 10분(실제 10초) 장애
caffeinate -dims docker compose --profile load run --rm day --out /out/day-peak.csv --outage-at 14 --outage-min 10
python3 analyze_day.py out/day-peak.csv --outage-at 14 --outage-min 10
python3 prom_sli.py --prom http://localhost:32190 --at $(date +%s)

docker compose down -v
```

계산만 하는 스크립트(컨테이너 없음, 표준 라이브러리만)

```bash
python3 calc/nines.py              # 9 의 개수별 허용 다운타임
python3 calc/time_vs_request.py    # 곡선으로 계산한 시간 기준 vs 요청 기준
python3 calc/year.py 3             # 합성 1년(시드 3)을 달력 월·28일·30일·365일로 판정
python3 calc/year_many.py 200      # 시드 1~200 요약
```

## 버전

| 부품 | 버전 |
|---|---|
| Prometheus | 3.15.0 |
| Grafana | 13.2.3 |
| Python | 3.13 (python:3.13-alpine) |
