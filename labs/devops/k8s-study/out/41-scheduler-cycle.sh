#!/usr/bin/env bash
# 실습 저장소의 shared/components/18-scheduler-cycle.sh 를 옮긴 것. 실습 저장소 루트에서 실행한다.
# kube-scheduler 가 실제로 하는 일: 어떤 파드를 집어 가나, 스케줄링 사이클과 바인딩 사이클, 대기열 (Mac 에서 실행)
# 실험 전용 네임스페이스 sc-demo 에서만 파드를 만들고 지운다.
# 3절에서 k8s-worker3 에 임시 라벨 lab/sched-demo=yes 를 붙였다가 마지막에 뗀다.
cd "$(dirname "$0")/../.."   # 실습 저장소 루트 (./lab 이 있는 곳)
K="./lab kubectl"; ts(){ date '+%T'; }
NS=sc-demo; IMG=registry.k8s.io/pause:3.10.2
T=$(mktemp -d)
now(){ python3 -c 'import time;print("%.2f"%time.time())'; }

# 스케줄러 /metrics (마스터 127.0.0.1:10259, admin.conf 클라이언트 인증서로 인증)
smetrics(){ ./lab ssh master -- sudo bash -s <<'R'
d=$(mktemp -d); grep client-certificate-data /etc/kubernetes/admin.conf | awk '{print $2}' | base64 -d > $d/c; grep client-key-data /etc/kubernetes/admin.conf | awk '{print $2}' | base64 -d > $d/k
curl -sk --cert $d/c --key $d/k https://127.0.0.1:10259/metrics; rm -rf $d
R
}
# API 서버가 받은 POST pods/binding 요청 수 (성공·실패 합)
bindings(){ $K get --raw /metrics | awk '/^apiserver_request_total\{/ && /subresource="binding"/ && /verb="POST"/ {s+=$2} END{print s+0}'; }
# 두 메트릭 스냅숏의 차이 (이름 패턴으로 거름)
mdiff(){ python3 - "$1" "$2" "$3" <<'P'
import sys,re
def load(f):
    d={}
    for l in open(f):
        if l.startswith('#') or not l.strip(): continue
        k,v=l.rsplit(' ',1); d[k]=float(v)
    return d
a,b=load(sys.argv[1]),load(sys.argv[2]); pat=re.compile(sys.argv[3])
for k in b:
    if pat.search(k) and b[k]-a.get(k,0)!=0: print("  +%-4g %s" % (b[k]-a.get(k,0), k))
P
}

echo "# kube-scheduler 가 하는 일: 집어 가는 파드, 스케줄링 사이클과 바인딩 사이클, 대기열 ($(date '+%F %T %Z'))"

echo; echo "## 0. 스케줄러는 어디서 무슨 권한으로 도나"
$K -n kube-system get pod -l component=kube-scheduler -o wide
echo "$(ts) master\$ grep -- '- --' /etc/kubernetes/manifests/kube-scheduler.yaml"
./lab ssh master -- sudo grep -E '^\s+- --' /etc/kubernetes/manifests/kube-scheduler.yaml
echo "$(ts) 리더 선출 Lease: $($K -n kube-system get lease kube-scheduler -o jsonpath='holder={.spec.holderIdentity} leaseDurationSeconds={.spec.leaseDurationSeconds} renewTime={.spec.renewTime}')"
echo "$(ts) kubectl get clusterrole system:kube-scheduler (파드 관련 규칙만)"
$K get clusterrole system:kube-scheduler -o json | python3 -c '
import json,sys
for r in json.load(sys.stdin)["rules"]:
    res=[x for x in r.get("resources",[]) if x.startswith("pod") or x in ("bindings","nodes")]
    if res: print("  %-40s %s" % (",".join(res), ",".join(r["verbs"])))'

$K create ns $NS >/dev/null
smetrics > $T/m0; B0=$(bindings)
echo; echo "## 1. 스케줄러가 집어 가는 파드와 안 집어 가는 파드 (바인딩 요청 수 시작값 $B0)"
cat <<Y | $K -n $NS apply -f - >/dev/null
apiVersion: v1
kind: Pod
metadata: {name: sc-normal}
spec: {containers: [{name: c, image: $IMG}]}
---
apiVersion: v1
kind: Pod
metadata: {name: sc-other-scheduler}
spec: {schedulerName: my-scheduler, containers: [{name: c, image: $IMG}]}
---
apiVersion: v1
kind: Pod
metadata: {name: sc-nodename}
spec: {nodeName: k8s-worker1, containers: [{name: c, image: $IMG}]}
Y
echo "$(ts) 파드 3개 생성: sc-normal(아무 설정 없음) / sc-other-scheduler(schedulerName: my-scheduler) / sc-nodename(spec.nodeName: k8s-worker1 을 직접 적음)"
sleep 10
$K -n $NS get pod -o wide
for p in sc-normal sc-other-scheduler sc-nodename; do
  echo "$(ts) $p 이벤트(보고한 컴포넌트, 이유):"
  $K -n $NS get events --field-selector involvedObject.name=$p -o json | python3 -c '
import json,sys
it=json.load(sys.stdin)["items"]
if not it: print("    (이벤트 없음)")
for e in sorted(it,key=lambda e:e.get("firstTimestamp") or e.get("eventTime") or ""):
    src=e.get("reportingComponent") or e.get("source",{}).get("component","")
    print("    %-18s %-10s %s" % (src, e["reason"], e["message"][:110]))'
done
B1=$(bindings)
echo "$(ts) API 서버가 받은 POST pods/binding: $B0 → $B1 (+$((B1-B0)))"
echo "$(ts) sc-normal 의 시각: 생성 $($K -n $NS get pod sc-normal -o jsonpath='{.metadata.creationTimestamp}') / PodScheduled=True $($K -n $NS get pod sc-normal -o jsonpath='{.status.conditions[?(@.type=="PodScheduled")].lastTransitionTime}')"
echo "$(ts) sc-normal 을 쓴 주체(managedFields: manager / operation / subresource):"
$K -n $NS get pod sc-normal --show-managed-fields -o json | python3 -c '
import json,sys
for m in json.load(sys.stdin)["metadata"]["managedFields"]:
    f=json.dumps(m.get("fieldsV1",{}))
    keys=[k for k in ("f:nodeName","f:conditions","f:containers","f:containerStatuses","f:podIP") if k in f]
    print("    %-24s %-7s %-8s 건드린 필드에 %s" % (m["manager"], m["operation"], m.get("subresource","-"), ",".join(keys)))'

echo; echo "## 2. sc-normal 한 개를 스케줄하는 동안 돈 확장 지점 (스케줄러 메트릭 차이, 1절 전후)"
smetrics > $T/m1
mdiff $T/m0 $T/m1 '^scheduler_framework_extension_point_duration_seconds_count'
mdiff $T/m0 $T/m1 '^scheduler_(schedule_attempts_total|queue_incoming_pods_total)'

echo; echo "## 3. 지금은 못 들어가는 파드: 대기열에서 기다리다 노드가 바뀌면 다시 시도하나"
cat <<Y | $K -n $NS apply -f - >/dev/null
apiVersion: v1
kind: Pod
metadata: {name: sc-wait}
spec: {nodeSelector: {lab/sched-demo: "yes"}, containers: [{name: c, image: $IMG}]}
Y
echo "$(ts) sc-wait 생성 (nodeSelector lab/sched-demo=yes, 이 라벨을 가진 노드 없음)"
sleep 5
$K -n $NS get pod sc-wait -o wide --no-headers
$K -n $NS get events --field-selector involvedObject.name=sc-wait,reason=FailedScheduling -o jsonpath='{range .items[*]}    {.reason}: {.message}{"\n"}{end}'
smetrics > $T/m2
echo "$(ts) 스케줄러 대기열:"; grep '^scheduler_pending_pods' $T/m2 | sed 's/^/    /'
sleep 20
echo "$(ts) 20초 더 기다린 뒤에도: $($K -n $NS get pod sc-wait --no-headers -o wide | awk '{print $3, "NODE="$7}'), FailedScheduling 이벤트 count=$($K -n $NS get events --field-selector involvedObject.name=sc-wait,reason=FailedScheduling -o jsonpath='{.items[0].count}')"
L0=$(now); $K label node k8s-worker3 lab/sched-demo=yes >/dev/null
echo "$(ts) kubectl label node k8s-worker3 lab/sched-demo=yes"
while [ -z "$($K -n $NS get pod sc-wait -o jsonpath='{.spec.nodeName}')" ]; do sleep 0.2; done
L1=$(now)
echo "$(ts) sc-wait → $($K -n $NS get pod sc-wait -o jsonpath='{.spec.nodeName}'), 라벨을 붙이고 nodeName 이 보이기까지 $(python3 -c "print('%.1f' % ($L1-$L0))")초 (조회 간격 0.2초 + kubectl 왕복 포함)"
echo "    PodScheduled=True $($K -n $NS get pod sc-wait -o jsonpath='{.status.conditions[?(@.type=="PodScheduled")].lastTransitionTime}')"
smetrics > $T/m3
echo "$(ts) 라벨 전후 대기열 이동(scheduler_queue_incoming_pods_total 차이):"
mdiff $T/m2 $T/m3 '^scheduler_queue_incoming_pods_total'
mdiff $T/m2 $T/m3 '^scheduler_schedule_attempts_total'

echo; echo "## 4. 대기열에 아예 안 넣는 파드: schedulingGates (PreEnqueue)"
cat <<Y | $K -n $NS apply -f - >/dev/null
apiVersion: v1
kind: Pod
metadata: {name: sc-gated}
spec: {schedulingGates: [{name: lab/wait-for-me}], containers: [{name: c, image: $IMG}]}
Y
sleep 4
echo "$(ts) $($K -n $NS get pod sc-gated --no-headers | awk '{print $1, $3}')"
echo "    FailedScheduling 이벤트 수: $($K -n $NS get events --field-selector involvedObject.name=sc-gated,reason=FailedScheduling --no-headers 2>/dev/null | wc -l | tr -d ' ')"
smetrics > $T/m4; echo "    $(grep 'scheduler_pending_pods{queue="gated"}' $T/m4)"
$K -n $NS patch pod sc-gated --type=json -p '[{"op":"remove","path":"/spec/schedulingGates"}]' >/dev/null
echo "$(ts) schedulingGates 를 지움"
sleep 3
echo "$(ts) $($K -n $NS get pod sc-gated --no-headers -o wide | awk '{print $1, $3, "NODE="$7}')"

echo; echo "## 5. 정리"
$K label node k8s-worker3 lab/sched-demo- >/dev/null
$K delete ns $NS --wait=true >/dev/null
echo "$(ts) 네임스페이스 $NS 삭제, worker3 라벨 제거: lab/sched-demo 라벨 가진 노드 $($K get node -l lab/sched-demo --no-headers 2>/dev/null | wc -l | tr -d ' ')개"
rm -rf $T
