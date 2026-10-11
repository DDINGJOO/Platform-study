# 트래픽 관리 실습-1: 느린 서버 한 대를 라운드로빈과 P2C가 다르게 피한다

같은 백엔드 네 대(`app-1`~`app-4`) 앞에 Envoy 를 두고 `app-4` 만 느리게 만든다.
Envoy 의 로드 밸런싱 정책만 바꿔 가며(ROUND_ROBIN, LEAST_REQUEST P2C, LEAST_REQUEST FULL_SCAN)
같은 부하(초당 500건, 90초)를 주고 인스턴스별 요청 수와 지연을 비교한다. Envoy 를 세 대로 늘린 경우도 본다.

| 백엔드 | 처리 시간 | 동시 처리 한도 |
|---|---|---|
| app-1~3 | 10~20ms (`LAB_DELAY_MS=10`, `LAB_JITTER_MS=10`) | 8 (`LAB_MAX_CONCURRENT`) |
| app-4 | 60~80ms (`LAB_DELAY_MS=60`, `LAB_JITTER_MS=20`) | 8 |

앱은 `../common-envoy/app` (실습 1~3 공용). 한도를 넘친 요청은 앱 안에서 줄을 선다.

## 돌리기

```bash
cd labs/traffic/tm-01-p2c
python3 ../common-envoy/scripts/make-dashboard.py .   # grafana/lab.json (저장소에 이미 있다)
docker compose up -d --build
RATE=400 ./run.sh p2c single            # 처음 한 번은 앱을 데우는 용도
export RATE=500
./run.sh rr single                       # ROUND_ROBIN
./run.sh p2c single                      # LEAST_REQUEST, choice_count 2
./run.sh fullscan single                 # LEAST_REQUEST, FULL_SCAN
./run.sh p2c multi                       # Envoy 세 대에 요청을 나눠 보낸다
./run.sh fullscan multi
docker compose --profile multi --profile load down -v
```

`run.sh` 는 Envoy 만 새로 띄우고(`--no-deps --force-recreate`, 앱은 그대로) k6 를 돌린 뒤
`out/<정책>-<single|multi>/` 에 `k6.txt`, `access.log`(Envoy 접근 로그, 저장소에는 올리지 않음),
`clusters.txt`(Envoy `/clusters` 의 호스트별 요청 수)를 남기고 인스턴스별 표를 찍는다.
표는 `../common-envoy/scripts/access-summary.py` 가 접근 로그로 계산한다(첫 10초 제외).

- Grafana http://localhost:26000 → 대시보드 「트래픽 실습-1 느린 서버 한 대」
- Prometheus http://localhost:26090, Envoy http://localhost:26080, Envoy admin http://localhost:26901
- 백엔드 직접 호출 http://localhost:26101 ~ 26104 (`POST /chaos?delayMs=..` 로 실행 중에 손잡이를 바꿀 수 있다)

## 버전

| 부품 | 버전 |
|---|---|
| Envoy | 1.39.3 (`envoyproxy/envoy:v1.39.3`, 2026-10-06 배포. 실습 시점 최신 안정판) |
| Spring Boot | 4.1.1 (Java 21, Micrometer 1.17.1) |
| Prometheus | 3.15.0 |
| Grafana | 13.2.3 |
| k6 | 2.3.0 |

Envoy 정책은 예전 `lb_policy` 필드 대신 `load_balancing_policy` 확장으로 적었다.
`selection_method: FULL_SCAN` 은 확장 설정(`LeastRequest`)에만 있다.

## 결과 (2026-10-11, Docker Desktop, Apple M5 Pro)

| 실행 | app-4 몫 | 전체 p90 | 전체 p99 |
|---|---|---|---|
| ROUND_ROBIN | 24.2% | 5.12s | 7.95s (k6 가 753건을 못 보냄) |
| P2C | 11.4% | 63ms | 80ms |
| FULL_SCAN | 8.0% | 22ms | 79ms |
| P2C, Envoy 3대 | 13.8% | 67ms | 80ms |
| FULL_SCAN, Envoy 3대 | 9.1% | 22ms | 80ms |

## 돌리다 만난 함정

- **느린 서버가 밀리면 그 서버의 지표가 먼저 사라진다.** 라운드로빈에서 app-4 의 줄이 2초를 넘자
  Prometheus 수집(`/actuator/prometheus`)도 같은 톰캣 줄에 서서 시간 초과가 났다(`up=0`, 약 55초).
  수집 간격이 2초라 수집 타임아웃도 2초를 넘을 수 없다.
- **앱이 잰 p99 는 2초에서 멈췄다. Envoy 는 8초를 쟀다.** 앱 타이머는 톰캣 작업 스레드(기본 200개)에
  올라탄 뒤부터 잰다. 스레드 200개가 앱 안 세마포어 줄에 서 있으면 나머지는 톰캣 바깥에서 기다리고,
  그 시간은 앱 지표에 없다. 인스턴스별 진실은 Envoy 접근 로그로 봤다.
- **Envoy 의 기본 히스토그램 버킷은 1s, 2.5s, 5s, 10s 처럼 듬성듬성하다.** `upstream_rq_time` 으로 그린 p99 가
  계단 모양으로 나온다. 초 단위 지연을 볼 거면 접근 로그나 버킷 설정(`stats_config.histogram_bucket_settings`)이 필요하다.
- **Envoy 는 접근 로그를 모아 두었다가 내보낸다.** k6 가 끝나자마자 `docker compose logs` 로 모으면 마지막 몇 초가 빠진다.
  글의 표는 이 상태로 셌다(실행마다 마지막 1~5초 누락). 지금 `run.sh` 는 12초 기다렸다가 모은다.
- `docker compose up -d --force-recreate envoy` 만 하면 `depends_on` 때문에 앱까지 건드린다. `--no-deps` 를 붙였다.
- k6 가 라운드로빈에서 753건을 못 보낸 건 VU 상한(2000) 때문이 아니다. 미리 만든 VU 200개가 모자라 새로 만드는 사이에 버렸다(최대 936개).
- `out/rr-single/app4-up.txt`, `out/inflight-at-arrival.txt` 는 실행 당시 Prometheus 에 질의한 결과를 PromQL 과 함께 옮겨 적은 것이다.
- macOS 기본 bash(3.2)는 `set -u` 에서 빈 배열 `"${arr[@]}"` 을 unbound 로 본다. `run.sh` 는 문자열 변수를 쓴다.
