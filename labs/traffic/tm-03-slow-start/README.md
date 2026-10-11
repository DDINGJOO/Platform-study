# 트래픽 관리 실습-3: 갓 뜬 인스턴스에 slow start를 걸면 무엇이 달라지나

같은 백엔드 네 대 앞에 Envoy 를 두고, app-1~3 이 초당 150건을 받는 도중 app-4 를 새로 띄운다.
요청마다 CPU 일(`LAB_CPU_ROUNDS=100`, 데워진 뒤 3~4ms)을 하고 컨테이너 CPU 를 0.5개로 묶어서
JIT 가 데워지기 전과 후의 차이가 드러나게 했다. Envoy 정책 네 가지를 같은 조건으로 비교한다.

| 설정 파일 | 내용 |
|---|---|
| `envoy/rr.yaml` | ROUND_ROBIN |
| `envoy/rr-ss.yaml` | ROUND_ROBIN + `slow_start_config` (창 60s, aggression 1.0, 바닥 10%) |
| `envoy/lr.yaml` | LEAST_REQUEST (P2C) |
| `envoy/lr-ss.yaml` | LEAST_REQUEST + 같은 slow start |

네 설정 모두 액티브 헬스 체크(`/actuator/health`, 1초 간격, 타임아웃 1초, 실패 2번이면 제외, 성공 1번이면 복귀)를 건다.
새 호스트는 첫 헬스 체크를 통과해야 요청을 받고, slow start 창도 그때부터 센다.
앱은 `../common-envoy/app` (실습 1~3 공용).

## 돌리기

```bash
cd labs/traffic/tm-03-slow-start
docker compose up -d --build
./run.sh rr && mv out/rr out/warmup-rr     # 첫 실행은 app-1~3 을 데우는 용도
./run.sh rr
./run.sh rr-ss
./run.sh lr
./run.sh lr-ss
docker compose --profile load down -v
```

`run.sh <설정>` 은 app-4 를 내리고 Envoy 를 새 설정으로 띄운 뒤 k6 로 초당 150건을 150초 보낸다.
부하 시작 30초(`JOIN_AT`) 뒤에 `docker compose up -d app-4` 로 새 인스턴스를 띄운다.
끝나면 `join-report.py` 가 Envoy 접근 로그로 "app-4 기동 후 120초" 요약과 5초 구간별 표를 찍는다.
결과는 `out/<설정>/`(`k6.txt`, `access.log`(저장소에는 올리지 않음), `stats.txt`, `join`, `app4-start.txt`), 네 실행의 출력은 `out/all-runs.txt`.

- Grafana http://localhost:26000 → 대시보드 「트래픽 실습-3 새 인스턴스와 slow start」
  (인스턴스별 요청 수·p99, JIT 컴파일 시간 `jvm_compilation_time_ms_total`, CPU)
- Prometheus http://localhost:26090, Envoy http://localhost:26080, Envoy admin http://localhost:26901

## 버전

Envoy 1.39.3, Spring Boot 4.1.1(Java 21, Temurin 21 JRE), Prometheus 3.15.0, Grafana 13.2.3, k6 2.3.0

## 결과 (2026-10-11, Docker Desktop, Apple M5 Pro, app-4 기동 후 120초 = 18000건)

| 실행 | app-4 몫 | 200ms 넘은 요청 | 1초 넘은 요청 | 최대 | 200 이 아닌 응답 |
|---|---|---|---|---|---|
| ROUND_ROBIN | 22.3% | 292 | 171 | 10.0s | 5 (504 2, 연결 끊김 3) |
| ROUND_ROBIN + slow start | 17.7% | 12 | 1 | 1.07s | 0 |
| LEAST_REQUEST | 23.7% | 1 | 0 | 282ms | 0 |
| LEAST_REQUEST + slow start | 17.6% | 10 | 0 | 751ms | 0 |

## 돌리다 만난 함정

- **트래픽이 없는 클러스터는 헬스 체크를 60초마다만 한다.** `no_traffic_interval` 기본값이 60초라서,
  Envoy 를 막 띄우고 요청이 없으면 호스트가 한참 `failed_active_hc` 로 남는다(그동안은 panic 모드로 전부에 보낸다).
  실습에서는 1초로 줄였다.
- **새로 뜬 인스턴스가 밀리면 헬스 체크도 시간 초과가 나서 빠진다.** ROUND_ROBIN 에서 app-4 는 기동 약 8초 뒤 healthy,
  12초 뒤 unhealthy, 20초 뒤 다시 healthy 였다(`envoy_cluster_membership_healthy`). 헬스 체크 타임아웃이 짧으면 생긴다.
- **새 호스트는 첫 헬스 체크 통과 전에는 요청을 받지 않는다.** DNS 로 호스트가 추가된 직후에는 `failed_active_hc` 상태라
  스프링 기동 전 연결 실패가 없었다.
- **slow start 실행에서 app-4 첫 요청이 3초 늦은 건 slow start 때문이 아니다.** 같은 이미지인데 스프링 기동이
  4.1~4.3초(slow start 없는 실행)와 6.1~6.5초(slow start 실행)로 달랐다. 첫 요청은 어느 실행이든 스프링 기동 뒤 0.4~0.8초.
- **Envoy 를 새로 띄우면 기존 호스트도 slow start 창에 들어간다.** 첫 헬스 체크 통과가 "unhealthy → healthy" 전환이라
  그 시각이 기록되고(`health_checker_base_impl.cc`), slow start 가중치는 창 안의 모든 호스트에 걸린다. `run.sh` 가 실행마다 Envoy 를
  다시 띄워서 app-4 합류 직후 13초쯤은 app-1~3 의 가중치도 0.8 안팎이었다. 그래서 첫 5초 몫이 계산 3.2% 가 아니라 4.0% 로 나왔다.
  기존 호스트 영향을 빼려면 Envoy 를 띄우고 60초 넘게 기다린 뒤 app-4 를 띄운다(`JOIN_AT` 을 늘린다).
- `out/rr/membership-healthy.txt` 는 실행 당시 Prometheus 에 질의한 결과를 옮겨 적은 것이다(스택을 내리면 사라져서).
- macOS 의 zsh 에서 `set -- $var` 는 단어로 나뉘지 않는다. 캡처 반복문은 bash 로 돌렸다.
