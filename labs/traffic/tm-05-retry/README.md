# 트래픽 관리 실습-5: 세 겹 재시도가 부하를 몇 배로 늘리는지 센다

서비스 셋을 한 줄로 잇고 맨 아래(`svc-c`)가 모든 요청에 503 을 내게 한다. 층마다 Envoy 가 재시도를 2번(시도 3번)
하면 맨 아래가 사용자 요청 하나에 몇 번 불리는지 Envoy 통계로 센다.

```
k6 -> Envoy :10000(edge) -> svc-a -> Envoy :10001(a_out) -> svc-b -> Envoy :10002(b_out) -> svc-c (503)
```

Envoy 는 하나만 띄우고 리스너 셋, 클러스터 셋으로 세 사이드카를 대신했다. 재시도 횟수와 서킷 브레이커는
클러스터마다 따로 세므로 사이드카를 셋으로 나눠도 셈은 같다.

| 모드(`envoy/<모드>.yaml`) | 내용 |
|---|---|
| `retry` | 세 층 모두 `retry_on: 5xx`, `num_retries: 2`. 서킷 브레이커 기본값(`max_retries` 3) |
| `retry-nocb` | 위와 같고 `circuit_breakers.thresholds.max_retries: 10000` |
| `budget` | 위와 같고 `retry_budget: { budget_percent: 20, min_retry_concurrency: 3 }` |
| `edge-only` | 맨 위(edge -> svc-a)만 재시도 2번 |

## 돌리기

```bash
cd labs/traffic/tm-05-retry
docker compose up -d --build
./run.sh retry seq-retry VUS=1 ITERATIONS=200          # 한 번에 하나씩 200건
./run.sh retry open-retry RATE=100 DURATION=60s        # 초당 100건 60초
./run.sh retry-nocb open-retry-nocb RATE=100 DURATION=60s
./run.sh budget open-budget RATE=100 DURATION=60s
./run.sh edge-only open-edge-only RATE=100 DURATION=60s
./run.sh retry long-retry VUS=100 DURATION=60s         # 사용자 100명이 쉬지 않고 (닫힌 부하)

# 재시도 간격(백오프) 재기: svc-c 도착 시각을 로그로
LOG_ARRIVALS=true docker compose up -d --no-deps svc-c
./run.sh retry seq-gap VUS=1 ITERATIONS=200
docker compose logs --since 5m svc-c | python3 backoff.py

docker compose --profile load down -v
```

`run.sh` 는 모드가 바뀌면 Envoy 를 그 설정으로 다시 만들고 `svc-a`, `svc-b` 를 재시작한 뒤 워밍업한다.
측정 직전에 `POST /reset_counters` 로 Envoy 카운터를 0 으로 돌리고, 끝나면 `count.py` 가 층별 요청 수를 찍는다.

- Grafana http://localhost:27130 → 대시보드 「실습-5 재시도 증폭」
- Prometheus http://localhost:27190, Envoy http://localhost:27100, admin http://localhost:27101

## 버전

Envoy 1.39.3, Spring Boot 4.1.1(Java 21), Prometheus 3.15.0, Grafana 13.2.3, k6 2.3.0

## 결과 요약 (2026-10-11, Docker Desktop, Apple M5 Pro)

| 실행 | 사용자 요청 | svc-a | svc-b | svc-c | p50 |
|---|---|---|---|---|---|
| `retry` 순차 200건 | 200 | 3.00 | 9.00 | 27.00 | 728ms |
| `budget` 순차 200건 | 200 | 3.00 | 9.00 | 27.00 | 737ms |
| `retry` 초당 100건 | 6001 | 1.48 | 2.18 | 3.30 | 63ms |
| `budget` 초당 100건 | 6001 | 1.47 | 2.18 | 3.30 | 63ms |
| `retry-nocb` 초당 100건 | 6001 | 3.00 | 9.00 | 27.00 | 682ms |
| `edge-only` 초당 100건 | 6001 | 1.85 | 1.85 | 1.85 | 16ms |
| `retry` 100명 60초 | 271736 | 1.02 | 1.04 | 1.04 | 19ms |
| `budget` 100명 60초 | 210337 | 1.12 | 1.25 | 1.36 | 18ms |
| `retry-nocb` 100명 60초 | 8731 | 3.00 | 9.00 | 27.00 | 683ms |

재시도 간격(svc-c 도착 기준, 처리 시간 약 5ms 포함): 1→2번째 5.6~39.8ms, 2→3번째 6.0~64.6ms.
Envoy 소스(`JitteredExponentialBackOffStrategy`)는 N번째 재시도를 `[0, min(25 x 2^(N-1), 250))`ms 에서 고른다
(25, 50, 100, 200, 그다음부터 250. `doubling_limit_ = max/2 = 125` 를 넘으면 두 배 대신 250 으로 묶는다).
`--since` 창에 직전 워밍업 curl 묶음이 섞여 처음엔 1,808건이 나왔다. 앞 25줄을 빼고 센 1,800건 결과는 `out/backoff-k6only.txt`.
문서의 `[0, (2^N - 1) x 25)` 라면 두 번째는 0~75ms 여야 한다.

## 돌리다 만난 함정

- **Envoy 를 다시 만들면 앱이 옛 Envoy 를 계속 부른다.** 처음엔 앱이 `http://envoy:10001` 로 불렀는데, 모드를 바꾸려
  Envoy 컨테이너를 다시 만들자 JDK HttpClient 가 들고 있던 연결이 읽기 타임아웃(10초)까지 멈추고,
  이름 조회가 실패하는(`UnresolvedAddressException`) 구간도 생겼다. 다른 실습이 Docker 를 같이 쓰며 부하가 높던 때였다.
  그래서 네트워크를 `198.18.27.0/24` 로 고정하고 모든 주소를 IP 로 박았다. 모드를 바꿀 때는 `svc-a`, `svc-b` 도 재시작한다.
- **`docker compose up -d envoy` 가 의존 서비스를 다시 만든다.** `LOG_ARRIVALS=true` 로 띄운 `svc-c` 가 기본값으로 돌아갔다.
  `run.sh` 가 모드를 바꾸며 Envoy 를 다시 만들 때도 그렇다. 백오프 측정은 `retry` 모드로 한 번 돌린 뒤(모드가 바뀌지 않게)
  `svc-c` 만 `--no-deps` 로 다시 띄우고 돌린다.
- **zsh 에서는 `set -- $spec` 이 단어를 나누지 않는다.** 반복문은 `bash -c` 로 돌린다. 나누지 못한 이름이
  compose 볼륨 경로가 되어 `envoy/` 아래에 빈 디렉터리가 생겼다.
- 동시 실행 숫자는 지연에 따라 달라진다. 고정 IP 로 바꾸기 전, 같은 `retry` 모드 초당 20건이 두 번 돌려 7.41배와 2.04배로
  갈렸다(위의 연결 문제와 Docker 부하가 섞여 버린 결과). 지연이 늘면 동시에 진행 중인 재시도가 늘어 상한에 더 걸린다.
  결과 요약의 숫자는 고정 IP(당시에는 사설 대역)로 바꾼 뒤 돌린 것이다. 공개 전에 사설 대역 표기를 피하려고
  `198.18.27.0/24` 로 옮겼고, 옮긴 뒤 `retry` 순차 100건으로 3/9/27배가 그대로인 것을 다시 확인했다.
