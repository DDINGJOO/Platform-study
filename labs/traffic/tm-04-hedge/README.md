# 트래픽 관리 실습-4: Envoy 헤지 요청으로 꼬리 지연을 깎는다

같은 이미지로 띄운 백엔드 세 대 앞에 Envoy 하나를 둔다. 백엔드는 요청마다 `BASE_MS + [0, JITTER_MS)` 만큼 자고,
`SLOW_RATIO` 비율의 요청은 `SLOW_MS` 를 더 잔다(기본: 5~10ms, 2%가 300ms 더). Envoy 는 경로 앞부분마다
다른 클러스터 이름으로 같은 백엔드를 묶어서, 정책별 통계를 따로 센다.

| 경로 | 정책 |
|---|---|
| `/plain` | 재시도·헤지 없음 |
| `/hedge` | `per_try_timeout: 25ms` + `hedge_on_per_try_timeout: true`, `num_retries: 1` |
| `/retry` | `/hedge` 와 같은 재시도 정책, 헤지 없음(시도 타임아웃이면 원본을 끊고 다시 보냄) |
| `/hedge-nocb` | `/hedge` 와 같되 클러스터 `circuit_breakers.max_retries` 를 10000 으로 |
| `/hedge-getonly` | `/hedge` + `retriable_request_headers: [:method == GET]` (ROADMAP 숙제) |
| `/retry-getonly` | `/retry` + 같은 `retriable_request_headers` (대조군) |

## 돌리기

```bash
cd labs/traffic/tm-04-hedge
docker compose up -d --build
./run-main.sh                                   # /plain, /hedge, /retry 를 초당 200건 x 2분씩 (워밍업 30초 포함 약 8분)
curl -s localhost:27001/stats | grep -E 'cluster\.backend_(plain|hedge|retry)\.upstream_rq_(total|retry)'

# 과부하: 백엔드마다 톰캣 스레드 4개로 줄이고 초당 600건
TOMCAT_THREADS=4 docker compose up -d backend-1 backend-2 backend-3
docker compose restart envoy
for p in plain hedge hedge-nocb; do docker compose --profile load run --rm -e TARGET=/$p -e RATE=600 -e DURATION=60s -e NAME=t4-$p-600 load; done
curl -s localhost:27001/stats | grep -E 'cluster\.backend_hedge(_nocb)?\.upstream_rq_(total|retry|retry_overflow):'   # Envoy 를 재시작하기 전에 찍는다

# 사본이 원본보다 얼마나 늦게 출발하나 (백엔드 도착 시각 로그)
LOG_ARRIVALS=true docker compose up -d backend-1 backend-2 backend-3
docker compose --profile load run --rm -e TARGET=/hedge -e RATE=100 -e DURATION=60s -e NAME=hedge-gap load
docker compose logs --since 2m backend-1 backend-2 backend-3 | python3 gap.py

# 숙제: retriable_request_headers 가 헤지를 막나 (백엔드를 모두 느리게)
SLOW_RATIO=1 SLOW_MS=100 LOG_ARRIVALS=true docker compose up -d backend-1 backend-2 backend-3
docker compose restart envoy
python3 homework.py 20
# 같은 실험에서 원본이 실패하면: 백엔드를 모두 100ms 뒤 503 으로
FAIL_RATE=1 SLOW_RATIO=1 SLOW_MS=100 LOG_ARRIVALS=true docker compose up -d backend-1 backend-2 backend-3
docker compose restart envoy
python3 homework.py 20

docker compose --profile load down -v
```

- Grafana http://localhost:27030 → 대시보드 「실습-4 헤지 요청」
- Prometheus http://localhost:27090, Envoy 리스너 http://localhost:27000, Envoy admin http://localhost:27001
- 포트는 `GRAFANA_PORT`, `PROM_PORT`, `ENVOY_PORT`, `ENVOY_ADMIN_PORT` 로 바꾼다
- k6 결과 요약은 `out/<이름>.json` 에 남는다(커밋하지 않는다)

## 버전

| 부품 | 버전 | 비고 |
|---|---|---|
| Envoy | 1.39.3 (`envoyproxy/envoy:v1.39.3`) | 2026-10-06 릴리스, 실습 시점 최신 안정판 |
| Spring Boot | 4.1.1 | Java 21, 4.2 는 아직 마일스톤 |
| Prometheus | 3.15.0 | |
| Grafana | 13.2.3 | |
| k6 | 2.3.0 | |

## 결과 요약 (2026-10-11, Docker Desktop, Apple M5 Pro)

| 실행 | 요청 | p50 | p99 | p99.9 | max | 백엔드 추가 요청 |
|---|---|---|---|---|---|---|
| `/plain` 200rps 2분 | 24000 | 8.3 | 308.2 | 310.3 | 313.1 | 0 |
| `/hedge` 200rps 2분 | 24000 | 8.3 | 47.1 | 58.6 | 310.2 | 453 (1.89%) |
| `/retry` 200rps 2분 | 24001 | 8.4 | 47.6 | 58.4 | 75.3 | 490, 504 응답 10건 |
| `/plain` 600rps, 스레드 4 | 35957 | 9.1 | 309.2 | 409.6 | 634.0 | 0 |
| `/hedge` 600rps, 스레드 4 (다시 잰 실행) | 35930 | 10.1 | 328.2 | 496.2 | 633.4 | 3967 (overflow 7665) |
| `/hedge-nocb` 600rps, 스레드 4 | 26222 (9778건 못 보냄) | 876.0 | 1565.1 | 1688.4 | 1737.2 | 25085 |

과부하 `/hedge` 줄은 처음 실행에서 Envoy 카운터를 남기지 못해 같은 조건으로 다시 잰 값이다(`out/t4-hedge-600-rerun.txt`).
워밍업 30초 뒤 `curl -X POST localhost:27001/reset_counters` 로 카운터를 0 으로 돌리고 60초 돌린 직후 `/stats` 를 찍었다.
Grafana 그림(overload-*.png)은 처음 실행의 화면이다.

`FAIL_RATE=1 SLOW_RATIO=1 SLOW_MS=100` 으로 `homework.py` 를 돌리면(`out/homework-fail.txt`) 헤지된 GET 은 원본 503 을 버리고
사본 503 을 기다려 중앙값 156ms, POST 는 원본 503 을 116ms 에 바로 돌려준다(재시도 조건이 0 이라 버릴 오류가 없다).

숙제 결과: `retriable_request_headers` 는 헤지를 막지 않는다. GET 만 허용한 라우트에서 POST 도 사본이 나갔다
(`upstream_rq_retry` 20/20). 본문이 있는 POST 의 사본은 `Content-Length: 7` 헤더만 가고 본문이 없었다.
일반 재시도(`/retry-getonly`)는 POST 에서 막혔다. 이유는 Envoy 소스 `source/common/router/retry_state_impl.cc`:
요청 헤더가 안 맞으면 `retry_on_ = 0` 으로만 바꾸는데, 헤지 경로 `shouldHedgeRetryPerTryTimeout()` 는
`retry_on_` 을 보지 않고 `RetryWithBackoff` 로 `shouldRetry()` 를 부른다. 본문 버퍼링은 `retry_state_->enabled()`
(= `retry_on_ != 0`)이거나 internal redirect 가 켜져 있을 때만 하므로 사본에 실을 본문이 없다.

## 돌리다 만난 함정

- **`retry_on` 이 비어 있으면 헤지도 없다.** 재시도 상태 객체는 `retry_on` 이 있을 때만 만들어진다
  (`RetryStateImpl::create`). 헤지를 켜려면 재시도 조건을 하나는 적어야 하고, 그 조건으로 일반 재시도도 같이 켜진다.
- **헤지는 `upstream_rq_per_try_timeout` 을 올리지 않는다.** 헤지 경로(`onSoftPerTryTimeout`)는 이 카운터를 건너뛴다.
  헤지가 몇 번 나갔는지는 `upstream_rq_retry` 로 센다.
- **진 쪽 요청을 끊으면 HTTP/1.1 연결이 통째로 닫힌다.** `upstream_cx_destroy_local_with_active_rq` 가 사본 수와 같이 올랐다.
  끊긴 요청도 백엔드에서는 끝까지 돌아 200 으로 기록됐다(백엔드 합계 78945 = Envoy 업스트림 요청 합계).
- **클러스터 기본 `max_retries` 는 3이다.** 동시에 진행 중인 재시도(헤지 사본 포함)가 3개를 넘으면 `upstream_rq_retry_overflow`
  로 빠진다. 초당 200건에서는 안 걸렸고, 과부하 실행에서는 헤지를 7665번 막았다(다시 잰 실행). 이걸 풀자(`/hedge-nocb`) 지연이 폭주했다.
- **사본 셋 중 하나는 원본과 같은 백엔드로 갔다**(130건 중 47건). 기본 설정은 이전 호스트를 피하지 않는다.
- k6 의 `PATH` 환경변수는 컨테이너의 실행 경로와 겹친다. 경로는 `TARGET` 으로 넘긴다.
- curl `-d` 는 `application/x-www-form-urlencoded` 로 보내서 스프링이 본문을 `hello=` 로 다시 만든다. 본문 길이를 볼 때는 `text/plain` 으로.
- Envoy 기본 히스토그램 버킷(0.5, 1, 5, 10, 25, 50, 100, 250ms...)은 25~50ms 가 한 칸이다. `stats_config.histogram_bucket_settings`
  로 촘촘하게 바꿨다. 그래도 Grafana 의 p99 는 버킷 보간값이라 k6 숫자와 다르다(평시 p99 가 280ms 안팎으로 보임, k6 는 308ms).
- Envoy 1.39 에서 가상 호스트 필드 이름은 `include_request_attempt_count` 다(`include_attempt_count_in_request` 는 없음).
