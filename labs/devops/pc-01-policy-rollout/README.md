# 플랫폼 실습-1: 재시도 정책 하나를 바꾸면 라이브러리는 다섯 번 다시 뜨고 사이드카는 설정만 바뀐다

블로그 「플랫폼 엔지니어링」 시리즈 실습-1(`posts/CS/DevOps/platform-culture/07_실습-1 ...`)의 코드다. 3편(공통 기능은 실어 보내는 경로가 업그레이드 값을 정한다)의 세 축을 잰다.

- 축 1: 정책 **값** 하나를 바꿀 때 무엇을 다시 띄우나
- 축 2: **구현**(여기서는 사이드카 Envoy 버전)을 올릴 때 무엇을 다시 띄우나
- 축 3: 바꾸는 동안 옛 정책과 새 정책이 함께 응답하는 창(섞인 창)은 얼마나 긴가. 부하기 기록에서 "v2 로 응답한 첫 요청"부터 "v1 으로 응답한 마지막 요청"까지(요청을 보낸 시각 기준)

서비스 다섯 개(`svc1`~`svc5`)가 하위 서비스 `backend` 의 `/data` 를 부른다. `backend` 는 모든 요청에 5ms 뒤 응답하고, 그중 10% 가 503 이다.
바꾸는 정책은 하나다.

| 정책 | 내용 | 스타터(Resilience4j) | Envoy |
|---|---|---|---|
| v1 | 재시도 없음, 요청 하나에 2초 | `maxAttempts=1`, 읽기 타임아웃 2000ms | `retry_policy` 없음, `timeout: 2s` |
| v2 | 최대 3번 시도, 시도당 0.5초 | `maxAttempts=3`, 읽기 타임아웃 500ms, 대기 25ms | `num_retries: 2`, `per_try_timeout: 0.5s`, `retry_on: 5xx,reset,connect-failure` |

## 방식 넷

| 이름 | 정책이 있는 곳 | 바꾸는 방법 (`scripts/run.sh`) |
|---|---|---|
| `lib` | 플랫폼 스타터 jar 안 (`starter/`, 빌드할 때 `platform-defaults.properties` 에 구움) | 스타터 1.1.0 을 `repo/` 에 내고, 서비스마다 이미지 재빌드(스타터 1.1.0) → `docker compose up -d --no-deps` 로 한 대씩 재기동 |
| `dyn` | 같은 스타터, 서비스마다 마운트한 정책 파일(`state/dyn/svcN.properties`). 스타터가 1초마다 읽는다 | 파일 다섯 개를 새 내용으로 바꿔치운다(임시 파일 + mv) |
| `sidecar` | 서비스 옆 Envoy 의 RDS 파일(`state/envoy/svcN/rds.yaml`, `path_config_source`) | Envoy 컨테이너 안에서 새 파일로 rename (`docker exec ... mv`) |
| `upgrade` | (정책은 v2 그대로) | 사이드카 Envoy 를 v1.39.2 에서 v1.39.3 으로, 한 대씩 다시 만든다 |

사이드카는 서비스 컨테이너의 네트워크 이름공간에 들어간다(`network_mode: service:sc-svcN`). 앱은 `127.0.0.1:15001` 로 부르고, 재시도 없는 클라이언트(읽기 타임아웃 10초)를 쓴다.
응답 헤더 `X-Policy`(정책 이름), `X-Attempts`(시도 수), `X-Starter`(스타터 버전)로 어느 정책이 적용됐는지 부하기가 요청마다 기록한다.
사이드카 쪽 `X-Policy` 는 Envoy 가 라우트의 `response_headers_to_add` 로 붙이고, `X-Attempts` 는 `x-envoy-attempt-count`(`include_attempt_count_in_response`)를 옮긴 것이다.

## 돌리기

```bash
cd labs/devops/pc-01-policy-rollout
./scripts/setup.sh                 # 스타터 1.0.0(v1) 을 내고 서비스 이미지 다섯 개(pc01/svcN:1.0.0)
./scripts/run_all.sh               # lib, sidecar, dyn, upgrade 를 번갈아 세 번씩 (약 15분)
python3 scripts/analyze.py lib-1 sidecar-1 dyn-1 upgrade-1 ...   # 실행별 요약
./scripts/latency.sh               # 사이드카 한 홉의 지연과 메모리 (약 7분)
./scripts/extra-badfile.sh         # 덧붙인 확인: 실행 중 읽는 정책 파일이 깨지면
./scripts/extra-poll.sh            # 덧붙인 확인: 호스트에서 바꾼 RDS 파일을 Envoy 가 알아채나
docker compose --profile lib --profile dyn --profile sidecar down -v
```

`run.sh` 하나는: 처음 상태로 되돌림 → 스택 기동 → 부하 20초 → 바꾸기 → 부하 20초. 부하는 `scripts/loadgen.py` 가 호스트에서 서비스마다 초당 20건(열린 부하, 요청마다 새 연결, 타임아웃 5초)을 보낸다.
포트: 서비스 37001~37005(lib, dyn) / 37011~37015(sidecar), Envoy admin 37021~37025, backend 37080. 네트워크 198.18.37.0/24 고정 IP.

## 버전과 환경

Spring Boot 4.1.1(Java 21, `eclipse-temurin:21-jre`), Resilience4j 2.4.0(`resilience4j-retry`, 재시도 대기 25ms 고정. Envoy 기본 백오프는 첫 재시도 [0, 25ms) 균등이라 간격은 다르다), Gradle 9.8.1(`gradle:9.8.1-jdk21`),
Envoy v1.39.2 / v1.39.3, `python:3.13-alpine`(backend), k6 2.3.0. Docker 29.5.3, Compose v5.1.4, Docker Desktop VM 15 CPU · 7.7GiB, Apple M5 Pro. 2026-10-16 실행.

## 결과 (`results/summary.txt` 에서. 시각은 바꾸기 시작을 0 으로 한 초, 세 번)

| 방식 | 바꾸기 시작~끝 | 섞인 창 | 다시 시작한 컨테이너 | 바꾸는 중 연결 실패·503 |
|---|---|---|---|---|
| `lib` | 30.1 / 37.4 / 34.9s | 20.1 / 25.6 / 23.5s | 서비스 5 | 162 / 178 / 176건 (서비스당 31~40건, 한 번에 1.5~1.95초) |
| `sidecar` | 0.8 / 0.9 / 0.8s | 0.45 / 0.50 / 0.40s | 0 | 0 |
| `dyn` | 1.1 / 0.4 / 1.2s | 0.90 / 0 / 0.95s | 0 | 0 |
| `upgrade` | 2.4 / 2.1 / 1.9s | (정책 그대로) | Envoy 5 (앱 0) | 503 20 / 19 / 18건 (사이드카당 3~5건, 한 번에 0.1~0.2초) |

- `lib` 의 시간 구성: 스타터 빌드·발행 2.5~3.4초, 서비스 이미지 빌드 하나 3.4~5.2초, `compose up`(옛 컨테이너를 멈추고 새로 만든 뒤 돌아옴) 0.8~1.2초, 그 뒤 v2 응답까지 1.0~1.4초.
  서비스 코드가 클래스 세 개이고 Gradle 의존성 캐시가 데워진 상태라 빌드가 짧다. CI·승인·팀 일정은 없다. **하한으로 읽는다.**
- 서비스는 한 대씩이라 재기동하는 동안 그 서비스로 가는 요청이 연결 실패로 끝났다. 여러 대로 굴리는 롤링 배포면 실패는 줄겠지만 재빌드·재기동 횟수는 그대로다.
- `sidecar` 의 0.4~0.5초 창은 `docker exec` 를 다섯 번 차례로 부른 시간이다. 사이드카 하나 안에서 v1 마지막 응답과 v2 첫 응답 사이는 0.05초 안팎.
- `dyn` 의 창은 1초 폴링 주기를 따른다(svc5 만 1초 늦게 읽은 회차가 둘).
- 정책 효과: 바꾸기 전(v1) 502 가 9~10%, 바꾼 뒤(v2) 0~0.3%(이론값 0.1% = 0.1³).

### 사이드카 한 홉 (`scripts/latency.sh`, 하위 실패 0, 정책 v1, 같은 네트워크 안의 k6 초당 200건 60초, 두 바퀴)

```
direct-1  p50=6.12ms p90=7.10ms p99=7.87ms     direct-2  p50=6.26ms p90=7.41ms p99=9.34ms
lib-1     p50=6.83ms p90=7.93ms p99=9.49ms     lib-2     p50=7.08ms p90=8.08ms p99=9.97ms  (12,000건 중 1건 실패, max 1004ms)
sidecar-1 p50=7.33ms p90=8.68ms p99=10.16ms    sidecar-2 p50=7.35ms p90=8.38ms p99=10.32ms
```

같은 바퀴끼리 빼면 sidecar − lib 는 p50 0.27~0.50ms, p99 0.35~0.67ms.

메모리(`docker stats`, 그 직후): Envoy 사이드카 17.2~23.5MiB씩, 앱 163~242MiB씩(`-Xmx160m`).

### 덧붙인 확인

- `out/extra-badfile.txt`: 정책 파일에 `maxAttempts=three`, `maxAttempts=0` 을 넣으면 스타터가 읽기를 거부하고 v1 을 유지했다(WARN 로그).
  `maxAttempts=50, timeoutMs=1` 은 형식이 맞아 1초 안에 적용됐고, 이어진 요청 세 개가 모두 50번씩 시도했다.
- `out/extra-poll.txt`: 호스트에서 RDS 파일을 rename 하면 Envoy(기본 감시)는 30초가 지나도 v1 이었다. 컨테이너 안에서 rename 하자 1초 안에 v2.
  `PathConfigSource.poll_interval` 은 v1.39.4 문서에 없고 v1.40.0(2026-10-13) 문서부터 있다. v1.39.3 은 `no such field: 'poll_interval'` 로 기동 실패(`out/extra-poll.txt` 의 오류 원문은 `cut` 으로 잘렸다).

## 돌리다 만난 함정

1. **호스트에서 바꾼 파일을 Envoy 가 못 봤다.** Envoy 는 `path_config_source` 파일을 "옮겨짐(move)" 이벤트로 감시한다(문서: "Envoy will watch the file path for moves").
   Docker Desktop(macOS) 바인드 마운트에서 호스트 쪽 `mv` 는 컨테이너 안에 그 이벤트로 오지 않았다. 그래서 `run.sh` 는 새 파일을 호스트에 두고 rename 만 `docker exec` 로 컨테이너 안에서 한다.
   바인드 마운트라 바뀐 파일은 호스트에 남고, `upgrade` 에서 Envoy 를 다시 만들어도 v2 로 뜬다.
2. **파일에서 읽는 RDS 도 node id 가 있어야 뜬다.** 처음 판은 `node 'id' and 'cluster' are required` 로 기동 실패. 부트스트랩에 `node:` 를 넣었다.
3. **backend 가 Nagle 을 켠 채로 응답하자 지연이 약 40ms 붙었다.** (k6 도 연결을 재사용하는데 k6 → backend 직접 호출이 왜 6ms 였는지는 확인하지 못했다.) 파이썬 `BaseHTTPRequestHandler` 는 헤더와 본문을 따로 쓴다. 연결을 재사용하는 요청(JDK HttpClient, Envoy)에서 p50 이 48ms 로 몰렸고,
   k6 가 바로 부른 backend 는 6ms 였다. `disable_nagle_algorithm = True` 로 고치고 실행을 전부 다시 했다(아래 버린 실행 2).
4. **사이드카를 내리면 처리 중이던 응답이 끊긴다.** 버린 두 바퀴의 `upgrade` 에서 매번 1~4건이 앱의 500 으로 끝났다. 앱 로그는
   `RestClientException: Error while extracting response ... java.io.EOFException: EOF reached while reading`. Envoy 가 응답을 다 보내기 전에 컨테이너가 멈췄다. 최종 바퀴에서는 0건.
5. 앱 이미지는 서비스마다 캐시 사슬이 갈리게 `SVC` 를 `RUN` 에 쓴다. 같은 소스라 그대로 두면 둘째 서비스부터 Docker 층 캐시를 타서 빌드가 0초가 된다. 회차마다 `BUILD_ID` 도 바꾼다.

## 버린 실행

- 시험 4번(`try-*`): 스크립트 확인용.
- 1차 12번: `rollout_start` 표시를 `docker inspect` 앞에 찍어 그 시간이 바꾸는 시간에 섞였고, `dyn-3` 은 그 `docker inspect` 가 5.8초 걸리는 동안 요청이 타임아웃으로 쏟아졌다(호스트 쪽 멈춤). 숫자 흐름은 최종과 같았다(바꾸기 시작~끝 `lib` 35.2~36.1초, `sidecar` 0.9초).
- 2차 12번 + 지연 비교: 함정 3. 바꾸는 시간·재기동 수는 최종과 같은 흐름이었지만(`lib` 39.4~42.0초, `sidecar` 0.8~0.9초) 지연 비교가 틀렸다.

`out/*.csv`(요청마다 한 줄, 유닉스 시각)와 `out/*.marks` 는 커밋하지 않는다. 다시 돌리면 생긴다.
