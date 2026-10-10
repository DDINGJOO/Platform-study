# 메트릭 수집 실습-1: 태그 하나가 시계열을 몇 개로 늘리는지 세어 본다

글: `posts/CS/Observability/metrics-pipeline/06_실습-1 - 태그 하나가 시계열을 몇 개로 늘리는지 세어 본다.html`

스프링 부트 앱의 카운터·타이머에 `user_id` 태그를 붙였다 떼면서 Prometheus head 시계열 수
(`prometheus_tsdb_head_series`), 스크레이프 크기, Prometheus 메모리를 잰다.

## 구성

| 경로 | 내용 |
|---|---|
| `app/` | 스프링 부트 4.1.1 + actuator + micrometer-registry-prometheus. `GET /checkout?user=uN`. `LAB_USER_TAG`(none·counter·timer·histogram)로 user_id 를 붙일 자리를 고른다 |
| `k6/users.js` | 사용자 `USERS` 명(기본 1000)이 한 번씩 주문한다 |
| `prometheus.yml` | 5초마다 앱을 긁는다. `extra_scrape_metrics: true`(스크레이프 본문 크기) |
| `prometheus-limited.yml` | 앱 타깃에 `sample_limit: 2000` |
| `grafana/` | 데이터소스와 대시보드 "카디널리티 실습"(시계열 수·메모리·스크레이프 크기) |
| `measure.py` | Prometheus 와 앱에서 숫자를 한 줄로 찍는다 |
| `run-phases.sh` | none → counter → timer → histogram → none 순서로 바꿔 가며 measure.py 를 찍는다 |
| `wait-app.sh` | 앱이 /actuator/health 에 답할 때까지 기다린다 |

호스트 포트: Grafana 21000, Prometheus 21090, 앱 21080 (`GRAFANA_PORT`, `PROM_PORT`, `APP_PORT` 로 바꾼다).

## 돌리기

Docker 와 Python 3 만 있으면 된다.

```bash
cd labs/observability/metrics-01-cardinality
docker compose up -d --build
./run-phases.sh                       # 2~4절. 5분쯤

# 5절: 블록 길이를 5분으로 줄여 head GC 를 본다
docker compose down -v
PROM_BLOCK=5m LAB_USER_TAG=histogram docker compose up -d
./wait-app.sh && docker compose --profile load run --rm -e USERS=1000 load
LAB_USER_TAG=none docker compose up -d app
python3 measure.py                    # 30초마다 다시. 7~8분 뒤 head_series 가 떨어진다
docker compose logs prometheus | grep -E "write block|Head GC"

# 6절: sample_limit
docker compose down -v
PROM_CONFIG=prometheus-limited.yml LAB_USER_TAG=counter docker compose up -d
./wait-app.sh
docker compose --profile load run --rm -e USERS=1000 load    # 1,106개. 통과
docker compose --profile load run --rm -e USERS=2500 load    # 2,705개. up=0

docker compose down -v
```

## 버전

| 부품 | 버전 |
|---|---|
| Spring Boot | 4.1.1 (Micrometer 1.17.1, Java 21) |
| Prometheus | 3.15.0 |
| Grafana | 13.2.3 |
| k6 | 2.3.0 |

## 돌려서 확인한 것 (2026-10-10, 사용자 1,000명)

| LAB_USER_TAG | 앱이 내보낸 시계열 | 스크레이프 본문 | Prometheus head |
|---|---|---|---|
| none | 108 | 13.6 KB | 830 |
| counter | 1,106 | 62.6 KB | 1,853 |
| timer | 4,100 | 236.3 KB | 4,944 |
| histogram | 73,100 | 5,356.7 KB | 74,275 |
| none (다시) | 108 | 13.6 KB | 74,275 |

## 함정 (돌리다 만난 것)

- Micrometer 문서는 타이머 히스토그램 기본 범위를 1ms~1분, 버킷 73개로 적지만, 1.17.1 소스의
  `AbstractTimerBuilder` 기본 최댓값은 30초다. 실제로 나온 버킷은 68개 + `+Inf` = 69개.
- `--enable-feature=extra-scrape-metrics` 는 Prometheus 3.15 에서 "phased out" 경고가 뜬다.
  설정 파일의 `extra_scrape_metrics: true` 로 켠다.
- 태그를 떼고 앱을 다시 띄워도 head 시계열은 줄지 않는다. 블록 컴팩션 뒤 Head GC 때 지워진다
  (기본 블록 2시간이면 1~3시간 뒤). `--storage.tsdb.min-block-duration` 은 시험용 옵션이다.
- `sample_limit` 을 넘으면 스크레이프 전체를 버리고 `up` 이 0 이 된다. 한도 전에 읽은 시계열 일부는
  stale 표시 없이 남아서 lookback(5분) 동안 마지막 값으로 보였다.
- 다른 컨테이너가 많이 떠서 CPU 가 바쁘면 앱 기동이 3분까지 걸렸다. 고정 sleep 대신 `wait-app.sh` 로 기다린다.
