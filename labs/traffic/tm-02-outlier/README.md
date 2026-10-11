# 트래픽 관리 실습-2: 빨리 실패하는 서버가 트래픽을 빨아들이고 outlier detection이 빼낸다

같은 백엔드 다섯 대(`app-1`~`app-5`, 40~60ms) 앞에 Envoy 를 두고, `app-5` 를 "요청이 오면 바로 503" 상태로 바꾼다
(`POST /chaos?fail=true`). 정책별로 app-5 가 받는 몫을 재고, outlier detection 으로 빠지고 돌아오는 것을 본다.

| 설정 파일 | 내용 |
|---|---|
| `envoy/rr.yaml` | ROUND_ROBIN |
| `envoy/p2c.yaml` | LEAST_REQUEST, choice_count 2 |
| `envoy/fullscan.yaml` | LEAST_REQUEST, FULL_SCAN |
| `envoy/p2c-od-default.yaml` | P2C + `outlier_detection: {}` (기본값 그대로) |
| `envoy/p2c-od-20.yaml` | P2C + outlier detection, `max_ejection_percent: 20`, 제외·복귀 사건 로그(`event_log_path`). 사건 로그 설정은 240초 실행(`out/p2c-od-20-heal`) 뒤에 넣어서 그 실행에는 사건 줄이 없다 |
| `envoy/p2c-od-20-nomerge.yaml` | 위와 같고 `common_lb_config.update_merge_window: 0s` |

앱은 `../common-envoy/app` (실습 1~3 공용).

## 돌리기

```bash
cd labs/traffic/tm-02-outlier
docker compose up -d --build
export RATE=200
./run.sh rr
./run.sh p2c
./run.sh fullscan
./run.sh p2c-od-default
DURATION=240s ./run.sh p2c-od-20 170 && mv out/p2c-od-20 out/p2c-od-20-heal   # 170초에 app-5 를 고친다
DURATION=120s ./run.sh p2c-od-20         # 고치지 않고 2분
DURATION=120s ./run.sh p2c-od-20-nomerge
RATE=600 DURATION=60s ./run.sh p2c       # 부하를 올리면 블랙홀 몫이 어떻게 되나
RATE=600 DURATION=60s ./run.sh fullscan
docker compose --profile load down -v
```

`run.sh <설정> [고칠 시점]` 은 Envoy 만 새로 띄우고 app-5 를 고장 낸 뒤 k6 를 돌린다. 끝나면 app-5 를 다시 고친다.
결과는 `out/<설정>/` 에 `k6.txt`, `access.log`(Envoy 접근 로그 + 제외·복귀 사건 JSON, 저장소에는 올리지 않음),
`stats.txt`(outlier detection 통계)로 남는다. 같은 설정을 다시 돌리면 덮어쓴다.
글에 쓴 200건/초 결과 중 rr·p2c·fullscan·p2c-od-default 의 표와 통계는 `out/all-runs.txt` 에 있다
(p2c·fullscan 디렉터리는 600건/초 실행이 덮어써서 `out/p2c-600`, `out/fullscan-600` 으로 옮겼다).

- Grafana http://localhost:26000 → 대시보드 「트래픽 실습-2 빨리 실패하는 서버」
- Prometheus http://localhost:26090, Envoy http://localhost:26080, Envoy admin http://localhost:26901
- 백엔드 직접 호출 http://localhost:26101 ~ 26105

## 버전

Envoy 1.39.3, Spring Boot 4.1.1(Java 21), Prometheus 3.15.0, Grafana 13.2.3, k6 2.3.0

## 결과 (2026-10-11, Docker Desktop, Apple M5 Pro)

| 실행 | app-5 몫 | k6 실패율 |
|---|---|---|
| ROUND_ROBIN, 200건/초 | 20.0% | 19.99% |
| P2C, 200건/초 | 34.7% | 34.65% |
| FULL_SCAN, 200건/초 | 67.4% | 67.33% |
| P2C, 600건/초 | 35.9% | 35.89% |
| FULL_SCAN, 600건/초 | 87.0% | 86.97% |
| P2C + outlier 기본값, 200건/초 | 34.7% (한 번도 안 빠짐, `ejections_overflow` 2514) | 34.63% |
| P2C + outlier 20%, 120초 | 503 143건 | 0.59% |
| P2C + outlier 20% + merge window 0, 120초 | 503 16건 | 0.06% |

## 돌리다 만난 함정

- **기본값 outlier detection 은 다섯 대짜리 클러스터에서 아무것도 빼지 않는다.** `max_ejection_percent` 기본 10%,
  (제외 중 + 1) / 5 = 20% 라서 매번 `ejections_overflow` 만 오른다. `ejections_detected_*` 는 오르니 "감지는 됐다"로 착각하기 쉽다.
- **복귀 직후의 재제외는 약 1초 늦게 반영된다.** 제외·복귀는 헬스 상태 변경이라 `common_lb_config.update_merge_window`
  (기본 1초) 안에서 합쳐진다. 복귀(첫 변경)는 바로 반영되고, 수십 ms 뒤의 재제외는 창이 끝날 때 반영된다.
  그 1초 동안 P2C 가 app-5 에 60~70건을 더 보냈다. 창을 0 으로 끄면 다섯 건 남짓에서 멈췄다.
- **`ejections_active` 게이지로는 복귀가 안 보인다.** 다시 빠지기까지 1초 남짓이라 2초 간격 수집에 안 잡혔다.
  복귀와 재제외는 사건 로그(`cluster_manager.outlier_detection.event_log_path`)나 접근 로그로 확인한다.
- **503 은 gateway failure 로도 감지된다.** `ejections_detected_consecutive_gateway_failure` 가 같이 오르지만
  `enforcing_consecutive_gateway_failure` 기본값이 0 이라 사건 로그에 `"enforced": false` 로 남고 실제로는 안 뺀다.
- 복귀 판정은 `interval`(10초)마다만 해서 제외 시간이 설정보다 0~10초 길어질 수 있다. 접근 로그로 잰 34.7s/68.9s/99.0s 에는
  재제외 반영 지연(merge window 1초)도 섞여 있다. 사건 로그로 잰 120초 실행의 제외 시간은 33.7s, 60.0s 였다.
- merge window 1초/0초 비교는 각각 한 번씩, 다른 시각·호스트 부하에서 돌렸다.
- 바쁜 호스트에서는 결과가 흔들린다. 다른 부하가 몰린 시간(부하 평균 20 이상)에 돌린 실행은
  k6 가 요청을 수천 건 못 보내서 버렸다(`out/p2c-od-20-nomerge-contended`).
- `run.sh` 는 k6 가 끝나고 12초 기다렸다가 접근 로그를 모은다. Envoy 가 로그를 모아 두었다가 내보내기 때문이다.
