# ds-02-canary: 카나리를 통계로 판정해 자동으로 되돌린다

배포 안전성 시리즈 실습-2 의 코드. kind 클러스터에 Argo Rollouts 와 Prometheus 를 올리고,
나쁜 버전을 카나리로 내보내 자동으로 멈추는 것과, 같은 카나리를 "같이 띄운 대조군"과
"운영본 전체"에 동시에 판정시켰을 때 결과가 갈리는 것을 본다.

## 구성

| 디렉터리 | 내용 |
|---|---|
| `app/` | 표준 라이브러리만 쓴 파이썬 HTTP 서버. `VERSION`, `EXTRA_MS`, `ERROR_RATE`, 예열(`WARMUP_MS`, `WARMUP_TAU_S`)을 환경변수로 받는다 |
| `judge/` | Kayenta `NetflixACAJudge` 의 맨-휘트니 분류와 점수를 파이썬으로 옮긴 판정 서버. Argo Rollouts web 공급자가 부른다 |
| `judge/test_port.py` | Kayenta 저장소의 테스트 스위트 기대값과 이식본을 대조한다 (22건) |
| `judge/sim_sensitivity.py` | 표본 수, 평균 증가율별로 High 가 나오는 비율 모의 실험 (3편의 표) |
| `k8s/` | 기반(Prometheus, judge, Service), AnalysisTemplate 셋, Rollout 두 가지, 부하, 저트래픽 Experiment |
| `scripts/` | `up.sh`, `down.sh`, `deploy.sh`(버전 바꾸기), `load.sh`(부하 바꾸기), `watch.sh`(상태 기록), `lowtraffic.sh` |
| `results/` | 이번 실행의 원자료 |

## 버전

| 구성 요소 | 버전 | 메모 |
|---|---|---|
| kind | 0.33.0 | 노드 이미지 `kindest/node:v1.37.0` (0.33.0 의 기본값) |
| Argo Rollouts | 1.10.0 | 2026-08 최신 안정판. 컨트롤러와 `kubectl-argo-rollouts` 플러그인 |
| Prometheus | 3.15.0 | 스크레이프 2초 |
| k6 | 2.3.0 | 클러스터 안에서 Job 으로 |
| Python | 3.13 (alpine) | 앱과 판정 서버 |
| 판정기 원본 | spinnaker/kayenta master `5310ab7` | `MannWhitneyClassifier.scala`, `MannWhitney.scala`, `BrentSolver.java`, `WeightedSumScorer.scala` |

## 돌리는 법

포트는 25000-25999 만 쓴다(API 서버 25443, Prometheus 25090, judge 25080).

```bash
./scripts/up.sh
K="kubectl --context kind-ds-02"

# 시나리오 1: 에러율 임계값 분석
$K apply -f k8s/rollout-threshold.yaml
$K apply -f k8s/load.yaml                 # 초당 50건
./scripts/deploy.sh v2-bad 0 0.10         # 10% 실패하는 버전
./scripts/watch.sh results/s1-threshold-watch.log 480

# 시나리오 2: Experiment 로 대조군과 카나리를 같이 띄우고 두 비교 대상에 판정
$K apply -f k8s/rollout-experiment.yaml   # 진행 중인 롤아웃이 있으면 먼저 정리된다
# 운영본 파드가 모두 10분 넘게 떠 있을 때까지 기다린다 (demo_uptime_seconds)
./scripts/deploy.sh v2 0 0                # 동작은 같은 버전
./scripts/deploy.sh v3-slow 5 0           # 요청마다 5ms 더 느린 버전 (v2 가 운영본이 되고 10분 뒤)
$K -n ds02 logs deploy/judge              # 판정마다 한 줄

# 시나리오 3: 부하를 바꿔 가며 같은 판정
$K apply -f k8s/experiment-lowtraffic.yaml
$K -n ds02 port-forward svc/judge 25080:80 &
./scripts/lowtraffic.sh                   # 예열 10분 + 초당 50, 10, 2건 각 10분 (results/raw/ 에 쌓인다)
python3 scripts/summarize.py              # raw 를 요약 표로

# 그래프
$K -n ds02 port-forward svc/prometheus 25090:9090 &

./scripts/down.sh
```

판정 서버를 직접 부를 수도 있다. `end` 를 주면 지난 구간을 다시 판정한다.

```
GET /judge?control=<해시>&experiment=<해시>&window=600&step=10[&end=<유닉스초>]
```

## 돌리다 만난 함정

- **CRD 가 커서 `kubectl apply` 가 거절된다.** Argo Rollouts `install.yaml` 의 CRD 두 개가
  `metadata.annotations: Too long: may not be more than 262144 bytes`. `--server-side` 로 넣는다.
- **`kind load docker-image` 가 `content digest ... not found` 로 실패한다.** 여러 플랫폼이 든
  이미지(argo-rollouts, prometheus, k6)에서 났다. `docker save --platform linux/<arch>` 로 저장해
  `kind load image-archive` 로 넣는다. `up.sh` 가 그렇게 한다.
- **호스트가 바쁘면 컨트롤 플레인이 넘어진다.** 같은 Docker Desktop(메모리 8GB) 위에 다른 kind
  클러스터 셋이 같이 돌던 첫 시도에서, 리스 갱신이 5초를 넘겨 controller-manager 와 scheduler 가
  CrashLoopBackOff 에 빠졌고, kubelet 하트비트가 늦어 노드가 NotReady 로 찍히자 judge 의
  엔드포인트가 빠져 판정 요청이 `connection refused` 가 됐다. `kind.yaml` 에서 리더 선출을 끄고
  (`leader-elect=false`) 노드 판정 유예를 5분(`node-monitor-grace-period`)으로 늘렸다. Argo Rollouts
  컨트롤러도 `--leader-elect=false`. 글의 결과는 전부 이 설정의 클러스터에서 나왔다.
- **연결을 재사용하는 부하는 카나리에 안 간다.** k6 가 연결을 재사용하면 먼저 맺은 연결이 기존
  파드에 붙어 있어 나중에 뜬 파드가 트래픽을 거의 못 받는다. `noConnectionReuse: true`.
- **카나리가 막 떴을 때 첫 측정은 Error 다.** 그 해시의 시계열이 아직 없어 Prometheus 결과가 비고
  `successCondition` 을 평가하지 못한다. 실패로 세지 않고 10초 뒤 다시 잰다(소스의
  `DefaultErrorRetryInterval`). 연속 Error 4번(`DefaultConsecutiveErrorLimit`)이면 분석이 Error 로 끝나니,
  web 공급자에는 `consecutiveErrorLimit` 을 넉넉히 줬다.
- **500 이 없으면 에러율이 Nodata 가 된다.** 분자 시계열이 없어서다. 판정 서버 쿼리는
  `or sum(rate(전체)) * 0` 으로 0 을 채운다.
- **`rate` 창을 판정 간격과 같게(10초) 두면 스크레이프 누락이 그대로 점 누락이 된다.** 호스트가
  바쁜 동안 2초 스크레이프가 240번 중 172번만 성공했고, 판정 점이 49개 대신 39개였다.

## results/

| 파일 | 내용 |
|---|---|
| `port-vs-kayenta-tests.txt` | 이식본 대조 결과 22건 |
| `sim-sensitivity.txt` | 3편의 모의 실험 표 |
| `s1-threshold-watch.log`, `s1-events.txt` | 시나리오 1 상태 기록(배포부터 경과 초)과 이벤트 |
| `s2a-good-watch.log`, `s2b-bad-watch.log` | 시나리오 2 상태 기록 |
| `s2-judgments.txt` | 시나리오 2 판정 16건 요약 (`scripts/summarize.py`) |
| `counts.txt` | 판정 로그에 남지 않는 숫자(요청·에러 건수, 스크레이프 수, 0인 점 비율)와 그 쿼리 |
| `s3-lowtraffic.txt` | 시나리오 3 판정 9건 요약 (고친 판정 서버로 다시 판정한 값) |
| `raw/`, `aborted/` | 유닉스 시각, 긴 소수, 사설 IP 가 든 원자료와 중단된 첫 시도. 커밋하지 않는다(`.gitignore`) |

시나리오 3 은 처음에 판정 서버가 step 과 상관없이 10초 `rate` 창을 써서 step 30/60초 판정이 점 사이 요청을
버렸다. `judge.py` 를 고친 뒤 이미지를 다시 넣고 `scripts/rejudge-s3.sh` 로 같은 구간(같은 `end`)을 다시
판정했다. 표는 그 결과다.
