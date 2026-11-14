#!/usr/bin/env bash
# 21편: 워커 한 대가 빠져도 남은 노드에 requests 가 들어가나, requests 와 실제 사용량은 얼마나 다른가
# w21 네임스페이스 안에서만 파드를 만들고 끝나면 네임스페이스째 지운다. 노드는 건드리지 않는다. (Mac 에서 실행)
cd "$(dirname "$0")/../.."   # 실습 저장소 루트 (./lab 이 있는 곳)
K="./lab kubectl"; ts(){ date '+%T'; }
NS=w21; T=$(mktemp -d)
trap '$K delete ns $NS --ignore-not-found --wait=false >/dev/null 2>&1; rm -rf $T' EXIT
echo "# 21편 N+1 확인과 requests·실사용 비교 ($(date '+%F %T %Z'))"

echo; echo "## 1. 워커별 할당 가능 CPU·메모리와 requests 합 (실험 전, kubectl describe node 의 Allocated resources)"
for n in k8s-worker1 k8s-worker2 k8s-worker3; do
  a=$($K get node $n -o jsonpath='{.status.allocatable.cpu} {.status.allocatable.memory}')
  r=$($K describe node $n | awk '/Allocated resources/{f=1} f&&/^  cpu/{c=$2} f&&/^  memory/{m=$2} END{print c, m}')
  echo "$n $a $r"
done | tee $T/alloc.txt | awk '{printf "  %s allocatable cpu=%s memory=%s | requests cpu=%s memory=%s\n",$1,$2,$3,$4,$5}'

echo; echo "## 2. requests 합과 실제 사용량 (kubelet /stats/summary, metrics-server 없이 API 서버 프록시로 조회)"
$K get pods -A -o json > $T/pods.json
for n in k8s-worker1 k8s-worker2 k8s-worker3; do $K get --raw /api/v1/nodes/$n/proxy/stats/summary > $T/$n.json; done
python3 - "$T" <<'PY'
import json,sys,os
T=sys.argv[1]
pods=json.load(open(f"{T}/pods.json"))["items"]
noreq={(p["metadata"]["namespace"],p["metadata"]["name"]) for p in pods
       if all(not c.get("resources",{}).get("requests") for c in p["spec"]["containers"])}
alloc={l.split()[0]:l.split() for l in open(f"{T}/alloc.txt")}
for n in ["k8s-worker1","k8s-worker2","k8s-worker3"]:
    s=json.load(open(f"{T}/{n}.json"))
    nd=s["node"]; mi=lambda b: round(b/2**20)
    allp=sum(p.get("memory",{}).get("workingSetBytes",0) for p in s["pods"])
    nrp=sum(p.get("memory",{}).get("workingSetBytes",0) for p in s["pods"] if (p["podRef"]["namespace"],p["podRef"]["name"]) in noreq)
    nnr=sum(1 for p in s["pods"] if (p["podRef"]["namespace"],p["podRef"]["name"]) in noreq)
    print(f"  {n}: 노드 실사용 cpu {round(nd['cpu']['usageNanoCores']/1e6)}m, memory workingSet {mi(nd['memory']['workingSetBytes'])}Mi"
          f" | 파드 {len(s['pods'])}개의 memory workingSet 합 {mi(allp)}Mi (그중 requests 없는 파드 {nnr}개가 {mi(nrp)}Mi)"
          f" | memory requests 합 {alloc[n][4]}")
PY

echo; echo "## 3. 계산: 파드 하나가 cpu 800m 을 요청하면 노드마다 몇 개 들어가나"
python3 - "$T" <<'PY'
import sys
T=sys.argv[1]
def m(v): return int(v[:-1]) if v.endswith("m") else int(float(v)*1000)
tot={}
for l in open(f"{T}/alloc.txt"):
    n,a,_,r,_=l.split(); free=m(a)-m(r); tot[n]=free//800
    print(f"  {n}: 할당 가능 {m(a)}m - requests {m(r)}m = 남은 {free}m → 800m 파드 {free//800}개")
print(f"  세 대 모두: {sum(tot.values())}개 | worker3 이 빠지면: {tot['k8s-worker1']+tot['k8s-worker2']}개")
PY

dep(){ # $1 이름, $2 replicas, $3 nodeAffinity 로 뺄 노드(없으면 빈 값)
  aff=""; [ -n "$3" ] && aff="      affinity: {nodeAffinity: {requiredDuringSchedulingIgnoredDuringExecution: {nodeSelectorTerms: [{matchExpressions: [{key: kubernetes.io/hostname, operator: NotIn, values: [$3]}]}]}}}"
  cat <<Y | $K apply -f - >/dev/null
apiVersion: apps/v1
kind: Deployment
metadata: {name: $1, namespace: $NS}
spec:
  replicas: $2
  selector: {matchLabels: {app: $1}}
  template:
    metadata: {labels: {app: $1}}
    spec:
$aff
      terminationGracePeriodSeconds: 1
      containers:
      - name: pause
        image: registry.k8s.io/pause:3.10.2
        resources: {requests: {cpu: 800m, memory: 16Mi}}
Y
}
$K create ns $NS >/dev/null

echo; echo "## 4. 워커 세 대를 모두 쓸 수 있을 때: cpu 800m 파드 5개"
echo "$(ts) mac\$ kubectl -n $NS apply (Deployment all3, replicas 5, requests cpu 800m)"; dep all3 5 ""
sleep 20
echo "$(ts) mac\$ kubectl -n $NS get pods -o wide"
$K -n $NS get pods -o custom-columns=NAME:.metadata.name,STATUS:.status.phase,NODE:.spec.nodeName
echo "  노드별 개수:"; $K -n $NS get pods -o jsonpath='{range .items[*]}{.spec.nodeName}{"\n"}{end}' | sort | uniq -c | sed 's/^/  /'
$K -n $NS delete deploy all3 --wait=true >/dev/null; $K -n $NS wait --for=delete pod -l app=all3 --timeout=60s >/dev/null 2>&1
echo "$(ts) all3 삭제"

echo; echo "## 5. worker3 이 빠졌다고 치고(nodeAffinity NotIn k8s-worker3 으로 후보에서 뺀다): 같은 5개"
echo "$(ts) mac\$ kubectl -n $NS apply (Deployment no-w3, replicas 5, requests cpu 800m, worker3 제외)"; dep no-w3 5 k8s-worker3
sleep 20
echo "$(ts) mac\$ kubectl -n $NS get pods -o wide"
$K -n $NS get pods -o custom-columns=NAME:.metadata.name,STATUS:.status.phase,NODE:.spec.nodeName
P=$($K -n $NS get pods --field-selector status.phase=Pending -o jsonpath='{.items[0].metadata.name}')
echo "$(ts) Pending 파드 $P 의 이벤트:"
$K -n $NS get events --field-selector involvedObject.name=$P -o custom-columns=SOURCE:.source.component,REASON:.reason,MESSAGE:.message --no-headers | head -3 | sed 's/^/  /'

$K delete ns $NS --wait=true >/dev/null && echo "$(ts) 네임스페이스 $NS 삭제"
trap - EXIT; rm -rf $T
