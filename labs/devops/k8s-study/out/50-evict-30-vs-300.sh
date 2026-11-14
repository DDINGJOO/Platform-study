#!/usr/bin/env bash
# 실습 저장소의 shared/why/01-node-heartbeat-and-eviction-timeouts/02-evict-30-vs-300.sh 를 옮긴 것. 실습 저장소 루트에서 실행한다.
# worker3 kubelet 을 멈추고: Lease 마지막 갱신 → NotReady·taint → tolerationSeconds 30 파드와 기본(300) 파드가 언제 쫓겨나나 (Mac 에서 실행)
# 네임스페이스 w8-evict 만 쓰고 지운다. 끝나면(중간에 끊겨도 trap) worker3 kubelet 을 다시 켠다.
cd "$(dirname "$0")/../../.."   # 실습 저장소 루트
K="./lab kubectl"; ts(){ date '+%T'; }; NS=w8-evict; N=k8s-worker3
trap './lab ssh worker3 -- sudo systemctl start kubelet' EXIT
echo "# kubelet 정지 → 축출: toleration 30초 vs 기본 300초 ($(date '+%F %T %Z'), 대상 $N)"
$K create ns $NS >/dev/null
for d in tol30 default; do
cat <<Y | $K -n $NS apply -f - >/dev/null
apiVersion: apps/v1
kind: Deployment
metadata: {name: $d}
spec:
  replicas: 1
  selector: {matchLabels: {app: $d}}
  template:
    metadata: {labels: {app: $d}}
    spec:
      terminationGracePeriodSeconds: 0
      affinity: {nodeAffinity: {preferredDuringSchedulingIgnoredDuringExecution: [{weight: 100, preference: {matchExpressions: [{key: kubernetes.io/hostname, operator: In, values: [$N]}]}}]}}
$( [ $d = tol30 ] && echo '      tolerations: [{key: node.kubernetes.io/unreachable, operator: Exists, effect: NoExecute, tolerationSeconds: 30}, {key: node.kubernetes.io/not-ready, operator: Exists, effect: NoExecute, tolerationSeconds: 30}]' )
      containers: [{name: c, image: registry.k8s.io/pause:3.10.2}]
Y
done
$K -n $NS rollout status deploy/tol30 deploy/default --timeout=90s >/dev/null 2>&1; $K -n $NS wait --for=condition=Ready pod --all --timeout=90s >/dev/null
echo; echo "## 0. 파드와 toleration (어드미션이 채운 값 포함)"
$K -n $NS get pod -o json | python3 -c '
import json,sys
for p in json.load(sys.stdin)["items"]:
    t=[("%s=%ss" % (x["key"].split("/")[-1], x.get("tolerationSeconds"))) for x in p["spec"].get("tolerations",[]) if x.get("effect")=="NoExecute"]
    print("  %-28s node=%-12s NoExecute toleration: %s" % (p["metadata"]["name"], p["spec"]["nodeName"], ", ".join(t)))'
echo; echo "## 1. 정지 전 Lease 갱신 간격 (1초마다 renewTime 확인, 25초)"
prev=""; for i in $(seq 1 25); do r=$($K -n kube-node-lease get lease $N -o jsonpath='{.spec.renewTime}'); [ "$r" != "$prev" ] && echo "  $(ts) renewTime $r"; prev=$r; sleep 1; done
T0=$(python3 -c 'import time;print(time.time())'); ./lab ssh worker3 -- sudo systemctl stop kubelet
echo; echo "## 2. $(ts) worker3\$ systemctl stop kubelet  (이 시각 = +0s, 아래 시각은 모두 이 기준)"
python3 $(dirname "$0")/watch_nodes.py $T0 480 $NS $N evict:default-
echo; echo "## 3. 이벤트 (축출 관련)"
$K -n $NS get events -o json | python3 -c '
import json,sys
for e in sorted(json.load(sys.stdin)["items"],key=lambda e:e.get("lastTimestamp") or e.get("eventTime") or ""):
    if e["reason"] in ("TaintManagerEviction","SuccessfulCreate","Scheduled","Killing"): print("  %s %-22s %-20s %s" % ((e.get("lastTimestamp") or e.get("eventTime") or "")[11:19], e.get("reportingComponent") or e["source"].get("component",""), e["reason"], e["message"][:90]))'
echo; echo "## 4. $(ts) worker3 kubelet 다시 시작"
./lab ssh worker3 -- sudo systemctl start kubelet; trap - EXIT
until [ "$($K get node $N -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}')" = True ]; do sleep 2; done
echo "  $(ts) $N Ready"; sleep 5; $K -n $NS get pod -o wide --no-headers | awk '{print "  "$1, $3, $7}'
echo; echo "## 5. 정리"; $K delete ns $NS --wait=true >/dev/null; echo "  $(ts) 네임스페이스 $NS 삭제"
