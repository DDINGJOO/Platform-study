# ts-01-delayed-symptom

트러블슈팅 실습-1 「쿼리 하나를 바꾸고 증상이 나타나기까지 몇 분 걸리는지 잰다」의 코드.

주문 조회 API(Spring Boot) 하나가 Postgres 의 `orders` 테이블을 읽는다. 다른 컨테이너가 주문을 계속 넣어
테이블이 자란다. 실행 중에 조회 쿼리를 인덱스를 못 타는 형태로 바꾸는 배포(원인)와, 증상 직전에 배너 문구만
바꾸는 배포(미끼)를 넣고, 각 사건과 증상 사이의 간격을 잰다.

## 구성

| 서비스 | 하는 일 |
|---|---|
| `db` | Postgres. `cpus: 1.0`, 병렬 쿼리 끔(`max_parallel_workers_per_gather=0`). 시작할 때 `SEED_ROWS` 행을 넣는다 |
| `writer` | 1초마다 `WRITE_ROWS` 행을 넣는다 |
| `app` | `GET /orders/recent?customer=C00042`. `QUERY_VARIANT=exact` 는 인덱스를 타고, `ci` 는 `lower(customer_ref)` 라 순차 스캔 |
| `postgres-exporter` | `pg_stat_user_tables_*` (순차 스캔으로 읽은 행 수, 행 수) |
| `prometheus`, `grafana` | 5초 수집. 대시보드 「주문 조회 API」, `deploy` 태그 annotation 을 겹쳐 보여 준다 |
| `load` (k6) | 초당 `RATE` 건 조회, 요청 타임아웃 3초. 요청 단위 기록을 `out/<RUN>-k6.csv.gz` 로 |

호스트 포트: 앱 34080, Prometheus 34090, Grafana 34030.

## 돌리기

```bash
cd labs/observability/ts-01-delayed-symptom
docker compose up -d --build
RUN=run1 T_DECOY=auto caffeinate -i scripts/run.sh          # 시간표대로 배포·되돌리기를 하고 끝나면 k6 를 멈춘다
python3 scripts/analyze.py out/run1            # 간격 정리. 스택이 떠 있을 때 돌린다
docker compose down -v
```

시간표는 환경변수로 바꾼다: `T_CHANGE`(쿼리 변경, 기본 180초), `T_DECOY`(배너 변경, 기본 900초),
`AFTER_TIMEOUT`(5xx 감지 뒤 "직전 변경"을 되돌리기까지, 120초), `OBSERVE`(되돌린 뒤 지켜보는 시간, 300초).
`T_DECOY=auto` 면 prediction.txt 의 "p99 300ms 초과" 예측 시각보다 `DECOY_LEAD`(300초) 앞에 미끼를 둔다
(쿼리 변경 뒤 240초보다 이르게는 두지 않는다). 글의 두 실행은 이 설정으로 돌렸고, 미끼는 둘 다 421초에 나갔다.
데이터 양은 `SEED_ROWS`, `WRITE_ROWS`, `RATE`.

## 결과 파일 (`out/<RUN>/`)

- `summary.txt` 사건 시각과 간격, annotation 을 최근 것부터 짚어 원인 배포에 닿기까지의 단계 수(증상 패널 출발 / 원인 쪽 패널 출발)
- `timeline.csv` 5초 간격: 행 수, 순차 스캔 행/초(천 행 단위), 서버·클라이언트 p99, 5xx, Hikari 대기, DB CPU
- `prediction.txt` 쿼리 변경 3분 뒤에, 그때까지의 지표만으로 계산한 증상 예측
- `explain-*.txt` 두 쿼리의 실행 계획 (시작, 변경 60초 뒤, 끝)

유닉스 시각이 든 원자료(`events.raw`, `cpu.raw`)와 k6 요청 기록은 `.gitignore` 로 뺐다.

`out/run1`, `out/run2` 의 `timeline.csv` 는 analyze.py 가 행/초를 천 단위로 줄이기 전에 만든 것이라, 스택을 내린 뒤 같은 변환
(행/초를 1000 으로 나눠 소수 1자리, 다른 소수는 4자리)을 파일에 직접 적용했다. summary.txt 와 prediction.txt 는 실행 때 그대로다.
두 실행은 각각 `docker compose down -v` 뒤 새로 띄운 스택에서 돌렸다.
