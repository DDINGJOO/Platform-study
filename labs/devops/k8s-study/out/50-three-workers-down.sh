#!/usr/bin/env bash
# 실습 저장소의 shared/why/01-node-heartbeat-and-eviction-timeouts/03-three-workers-down.sh 를 옮긴 것. 실습 저장소 루트에서 실행한다.
# 워커 3대 kubelet 을 동시에 멈추면(노드 4대 중 3대 NotReady = 75%) 축출이 멈추나 (Mac 에서 실행)
# 네임스페이스 w8-zone 만 쓰고 지운다. 끝나면(중간에 끊겨도 trap) 세 워커 kubelet 을 다시 켠다.
cd "$(dirname "$0")/../../.."   # 실습 저장소 루트
K="./lab kubectl"; ts(){ date '+%T'; }; NS=w8-zone; W="worker1 worker2 worker3"
startall(){ for w in $W; do ./lab ssh $w -- sudo systemctl start kubelet & done; wait; }
trap startall EXIT
kcm(){ ./lab ssh master -- sudo bash -s <<'R' | grep -E '^node_collector_(zone_health|zone_size|unhealthy_nodes_in_zone|evictions_total)'
d=$(mktemp -d); grep client-certificate-data /etc/kubernetes/admin.conf | awk '{print $2}' | base64 -d > $d/c; grep client-key-data /etc/kubernetes/admin.conf | awk '{print $2}' | base64 -d > $d/k
curl -sk --cert $d/c --key $d/k https://127.0.0.1:10257/metrics; rm -rf $d
R
}
echo "# 워커 3대 동시 정지: 축출이 멈추나 ($(date '+%F %T %Z'))"
$K create ns $NS >/dev/null
for w in 1 2 3; do
cat <<Y | $K -n $NS apply -f - >/dev/null
apiVersion: v1
kind: Pod
metadata: {name: on-worker$w}
spec: {nodeName: k8s-worker$w, terminationGracePeriodSeconds: 0, containers: [{name: c, image: registry.k8s.io/pause:3.10.2}]}
Y
done
$K -n $NS wait --for=condition=Ready pod --all --timeout=60s >/dev/null
echo; echo "## 0. KCM 노드 상태 메트릭 (정지 전)"; kcm | sed 's/^/  /'
T0=$(python3 -c 'import time;print(time.time())')
for w in $W; do ./lab ssh $w -- sudo systemctl stop kubelet & done; wait
echo; echo "## 1. $(ts) worker1·2·3 kubelet 동시 정지 (+0s)"
python3 $(dirname "$0")/watch_nodes.py $T0 420 $NS k8s-worker1,k8s-worker2,k8s-worker3 none
echo; echo "## 2. $(ts) KCM 노드 상태 메트릭 (정지 뒤 7분)"; kcm | sed 's/^/  /'
echo "  KCM 로그 (disruption·eviction 관련):"
$K -n kube-system logs kube-controller-manager-k8s-master --since=10m 2>/dev/null | grep -i -E 'disruption|zone|Evict|taint' | cut -c1-200 | tail -15 | sed 's/^/    /'
echo "  w8-zone 파드:"; $K -n $NS get pod -o wide --no-headers | awk '{print "    "$1, $3, $7}'
echo "  삭제 표시가 붙은 파드(클러스터 전체): $($K get pod -A -o json | python3 -c 'import json,sys;print(sum(1 for p in json.load(sys.stdin)["items"] if p["metadata"].get("deletionTimestamp")))')개"
echo; echo "## 3. $(ts) 세 워커 kubelet 다시 시작"; startall; trap - EXIT
for n in k8s-worker1 k8s-worker2 k8s-worker3; do until [ "$($K get node $n -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}')" = True ]; do sleep 2; done; done
echo "  $(ts) 세 워커 Ready"; sleep 5; kcm | sed 's/^/  /'
echo; echo "## 4. 정리"; $K delete ns $NS --wait=true >/dev/null; echo "  $(ts) 네임스페이스 $NS 삭제"
echo "  Running 아닌 파드: $($K get pod -A --no-headers | grep -v -E 'Running|Completed' | wc -l | tr -d ' ')개"
