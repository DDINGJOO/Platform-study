# ir-03-chaos-mesh: 정상 상태 가설을 세우고 Chaos Mesh로 깨 본다

장애 대응 시리즈 실습-3 의 코드. kind 클러스터에 Chaos Mesh 와 프로메테우스를 올리고,
`loadgen -> front(3) -> stock(3)` 서비스에 파드 죽이기, 네트워크 지연·손실, CPU 부하를 차례로 건다.
사용자 자리(loadgen)에서 잰 성공률과 지연으로 정상 상태 가설을 판정하고, 가설이 깨지면 실험을 스스로 멈춘다.

## 구성

| 경로 | 내용 |
|---|---|
| `app/app.py` | 표준 라이브러리만 쓴 파이썬 서버. `ROLE` 로 stock, front, loadgen 을 고른다. `STARTUP_S` 초 동안 포트를 늦게 연다 |
| `k8s/00-base.yaml` | 네임스페이스 `ir03`, 프로메테우스(스크레이프 2초), stock·front 각 3개, loadgen(초당 40건). 처음 상태는 readinessProbe 없음, 재시도 없음 |
| `k8s/10-readiness.yaml` | 고친 것 1: readinessProbe (`scripts/fix.sh readiness`) |
| `k8s/20-pdb-stock.yaml` | stock 의 PodDisruptionBudget(minAvailable 2). pod-kill 이 이를 지키는지 보는 실험에만 쓴다 |
| `chaos/` | 실험 정의. 01 반복 pod-kill, 02·03 지연 one/all, 04 한 번 pod-kill(one, fixed 2, fixed-percent 67, all), 05 손실, 06 CPU 부하, 07 PDB 를 둔 상태에서 전부 죽이기 |
| `scripts/up.sh`, `down.sh` | 클러스터 만들기와 지우기 |
| `scripts/fix.sh` | `readiness`, `retry-only`(재시도 1번, 타임아웃 1초), `retry`(재시도 1번, 타임아웃 300ms), `naive` |
| `scripts/experiment.py` | 기준 구간 확인, 카오스 적용, 5초마다 가설 판정, 연속 2번 깨지면 중단, 회복 기록 |
| `scripts/ir03-rerun.sh` | 두 번째 클러스터에서 e1, e2-kill-all-pdb, e4, e5 를 차례로 돌린다. 덮개가 닫힌 채 배터리로 돌면 풀릴 때까지 기다리고, 판정 사이 공백(8초 초과)이나 컨트롤 플레인 재시작이 있으면 그 실행을 버리고 다시 돈다 |
| `scripts/probe.py` | loadgen 파드 안에서 stock Service 를 50ms 마다 불러 요청마다 받은 파드나 실패 종류를 찍는다 |
| `results/` | 이번 실행의 결과 |

## 버전

| 구성 요소 | 버전 | 메모 |
|---|---|---|
| kind | 0.33.0 | 노드 이미지 `kindest/node:v1.37.0`, containerd 2.3.4, kube-proxy iptables 모드 |
| Chaos Mesh | 2.8.4 | 2026-08 최신 안정판. 공식 차트를 `helm template` 으로 그려 넣는다(helm 은 `alpine/helm:3.22.0` 컨테이너로) |
| Prometheus | 3.15.0 | |
| Python | 3.13 (alpine) | 앱 |
| 실행 환경 | Docker Desktop(메모리 8GB, 다른 실습과 같이 씀), Apple Silicon, 커널 6.12.76-linuxkit | |

Chaos Mesh 차트 값: `chaosDaemon.runtime=containerd`, `socketPath=/run/containerd/containerd.sock`(kind 노드의 런타임),
컨트롤러 1개·리더 선출 끔, 대시보드 끔, `controllerManager.enableFilterNamespace=true`
(주석 `chaos-mesh.org/inject=enabled` 가 붙은 네임스페이스에만 주입. `up.sh` 가 `ir03` 에만 붙인다).
DNSChaos 용 `chaos-dns-server` 는 차트 기본값대로 같이 떴다.

## 돌리는 법

포트는 29000-29999 만 쓴다(API 서버 29443, 프로메테우스 29090).

```bash
./scripts/up.sh
kubectl --context kind-ir-03 -n ir03 port-forward svc/prometheus 29090:9090 &

# 처음 상태(재시도 없음, readinessProbe 없음)에서 30초마다 stock 파드 하나 죽이기
python3 scripts/experiment.py e1-pod-kill-naive chaos/01-pod-kill-stock-one.yaml --baseline 30 --observe 120 --recover 30 --no-abort

./scripts/fix.sh readiness
python3 scripts/experiment.py e1-pod-kill-readiness chaos/01-pod-kill-stock-one.yaml --baseline 30 --observe 120 --recover 30 --no-abort

# 폭발 반경: 한 번 죽이기를 모드만 바꿔서. 중단 조건을 켠다(--no-abort 없음)
for n in one fixed2 pct67 all; do
  python3 scripts/experiment.py e2-kill-$n chaos/04-pod-kill-stock-$n.yaml --baseline 30 --observe 60 --recover 30
done

# 네트워크
python3 scripts/experiment.py e3-delay-one chaos/02-delay-stock-one.yaml --baseline 30 --observe 60 --recover 30 --no-abort
python3 scripts/experiment.py e3-delay-all chaos/03-delay-stock-all.yaml --baseline 30 --observe 60 --recover 30 --no-abort
python3 scripts/experiment.py e4-loss-one chaos/05-loss-stock-one.yaml --baseline 30 --observe 60 --recover 30 --no-abort
./scripts/fix.sh retry-only
python3 scripts/experiment.py e4-loss-one-retry-only chaos/05-loss-stock-one.yaml --baseline 30 --observe 60 --recover 30 --no-abort
./scripts/fix.sh retry
python3 scripts/experiment.py e4-loss-one-retry300ms chaos/05-loss-stock-one.yaml --baseline 30 --observe 60 --recover 30 --no-abort

# PDB 를 둔 채 전부 죽이기 (readinessProbe 있는 상태에서)
kubectl --context kind-ir-03 -n ir03 apply -f k8s/20-pdb-stock.yaml
python3 scripts/experiment.py e2-kill-all-pdb chaos/07-pod-kill-stock-all-pdb.yaml --baseline 30 --observe 60 --recover 30
kubectl --context kind-ir-03 -n ir03 delete -f k8s/20-pdb-stock.yaml

# CPU 부하, 고친 상태로 다시 파드 죽이기
python3 scripts/experiment.py e5-stress-front-one chaos/06-stress-front-one.yaml --baseline 30 --observe 60 --recover 30 --no-abort
python3 scripts/experiment.py e1-pod-kill-fixed chaos/01-pod-kill-stock-one.yaml --baseline 30 --observe 120 --recover 30 --no-abort

# 엔드포인트가 없는 Service 를 부르면
kubectl --context kind-ir-03 -n ir03 scale deploy stock --replicas=0
kubectl --context kind-ir-03 -n ir03 exec -i deploy/loadgen -- python - 2 < scripts/probe.py

./scripts/down.sh

# 두 번째 클러스터의 e1, e2-kill-all-pdb, e4, e5 를 한 번에(덮개·전원 조건과 판정 공백 검사 포함)
./scripts/ir03-rerun.sh
```

`experiment.py` 는 기준 구간의 마지막 세 번 판정 중 하나라도 가설이 깨지면 장애를 넣지 않고 코드 2 로 끝난다.
실제로 두 번 그랬다. `e3-delay-all-baseline-refused.tsv` 는 기준 구간 마지막 판정에 실패 한 건(503)이 생겼고,
`e4-loss-one-retry300ms-baseline-refused.tsv` 는 실패 없이 p99 가 1.3초로 튀었다. 뒤의 것은 `fix.sh retry` 로 front 를
다시 띄운 직후라 롤아웃의 영향일 수 있고, 원인은 확인하지 못했다. 두 실행 모두 앞 판정들은 가설을 지켰다.

## 돌리다 만난 함정

- **차트 기본 런타임은 docker 다.** kind 노드는 containerd 라서 `chaosDaemon.runtime`, `socketPath` 를 바꿔야 한다.
- **`fixed-percent: 67` 은 파드 셋 중 셋을 고른다.** `pkg/selector/generic/mode.go` 가 `math.Ceil(개수 × 비율 / 100)` 으로 센다.
  3 × 0.67 = 2.01 이 올림되어 3. 둘만 죽이려면 `mode: fixed`, `value: "2"`.
- **pod-kill 은 PodDisruptionBudget 을 거치지 않는다.** `controllers/chaosimpl/podchaos/podkill/impl.go` 가 파드를 Delete 한다(축출 API 아님). `k8s/20-pdb-stock.yaml`(minAvailable 2, ALLOWED DISRUPTIONS 1)을 둔 채 `mode: all` 을 걸어 확인했다(`e2-kill-all-pdb`): 세 파드가 같은 초에 지워졌다.
- **Service 에 엔드포인트가 없으면 거절이 아니라 타임아웃이 난다.** kube-proxy(iptables)는 `REJECT --reject-with icmp-port-unreachable`
  규칙을 넣지만, 커널이 ICMP 오류를 목적지마다 속도 제한한다(`inet_peer_xrlim_allow`, 몰아서 6개, 그 뒤 `icmp_ratelimit` 1000ms 마다 1개).
  처음 몇 건만 바로 거절되고 나머지는 SYN 이 응답 없이 버려져 클라이언트 타임아웃까지 기다린다. 노드의 `/proc/net/snmp` 의
  `OutRateLimitHost` 가 그 수를 센다. `experiment.py` 요약의 "속도 제한으로 못 보냄" 이 그 값이다.
- **readinessProbe 를 `periodSeconds: 1`, `failureThreshold: 1` 로 촘촘히 잡으면 호스트가 잠깐 멈출 때 멀쩡한 파드도 빠진다.**
  이벤트에 `Readiness probe failed: ... context deadline exceeded` 가 실험과 무관한 시각에 찍혔다.
- **노트북이 잠들면 실행이 망가진다.** 덮개가 닫힌 채 배터리로 돌면 `caffeinate` 를 걸어도 시스템이 잠들었다. 첫 클러스터에서 판정 사이가 270초, 13초, 그리고 기준 구간에서 5분 넘게 빈 실행이 나왔다. 그래서 e1, e4, e5 를 `scripts/ir03-rerun.sh` 로 새 클러스터에서 다시 돌렸고, 첫 클러스터의 그 결과는 `results/aborted/run1/` 로 옮겼다(커밋 안 함). 다시 돌린 여덟 실행(e1 셋, e2-kill-all-pdb, e4 셋, e5)은 판정 공백 0, kube-system·chaos-mesh 파드 재시작 0(`results/raw/final-restarts.txt`).

## results/

| 파일 | 내용 |
|---|---|
| `summary.txt` | 실험마다 한 단락: 카오스 구간 전체의 요청 수, 성공률, p50·p99(버킷 누적값 차이로 계산), 실패 종류, 판정 횟수, 노드 ICMP 카운터 차이. 새 클러스터 실행에는 front 의 stock 호출 실패 종류(시도 단위)도 있다. 클러스터별로 구획을 나눴다 |
| `<실험>.tsv` | 5초마다 한 줄. `t_s` 는 카오스를 건 순간부터 경과 초(음수는 기준 구간). 15초 창의 성공률·p50·p99 와 직전 5초의 요청·실패 수 |
| `*-baseline-refused.tsv` | 기준 구간에서 가설이 깨져 시작하지 않은 실행 둘(둘 다 첫 클러스터) |
| `probe-pct67.txt` | `fixed-percent 67` 을 건 동안 50ms 마다 stock 을 부른 결과(경과 초, 받은 파드 또는 실패 종류, ms) |
| `probe-no-endpoints.txt` | stock 0개일 때 2초 동안 부른 결과와 노드 ICMP 카운터 전후 |
| `e5-stress-front-perpod.txt` | CPU 부하 실험 구간의 front 파드별 p50·p99 |
| `raw/`, `aborted/` | 카오스 객체 상태, 이벤트(유닉스 시각, 사설 IP 포함), 중단된 실행. 커밋하지 않는다 |

실험과 그때의 클러스터, 앱 상태:

| 실험 | 클러스터 | readinessProbe | front 의 stock 호출 |
|---|---|---|---|
| e2-kill-one, e2-kill-fixed2, e2-kill-pct67, e2-kill-all, e3-* | 첫 번째 | 있음 | 타임아웃 1초, 재시도 없음 |
| e1-pod-kill-naive | 두 번째 | 없음 | 타임아웃 1초, 재시도 없음 |
| e1-pod-kill-readiness, e2-kill-all-pdb(PDB 있음), e4-loss-one | 두 번째 | 있음 | 타임아웃 1초, 재시도 없음 |
| e4-loss-one-retry-only | 두 번째 | 있음 | 타임아웃 1초, 재시도 1번 |
| e4-loss-one-retry300ms, e5-stress-front-one, e1-pod-kill-fixed | 두 번째 | 있음 | 타임아웃 300ms, 재시도 1번 |
