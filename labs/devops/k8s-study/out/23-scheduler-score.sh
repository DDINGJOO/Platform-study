#!/usr/bin/env bash
# 스케줄러의 스코어 단계: 필터를 통과한 노드가 여럿일 때 어디로 보내나 (Mac 에서 실행)
# 실험 전용 네임스페이스 w23 안에서만 파드를 만들고 지운다. 노드 라벨·taint 는 건드리지 않고 기존 라벨(kubernetes.io/hostname)만 쓴다.
cd "$(dirname "$0")/../.."   # 실습 저장소 루트 (./lab 이 있는 곳)
K="./lab kubectl"; ts(){ date '+%T'; }
NS=w23; IMG=registry.k8s.io/pause:3.10.2
T=$(mktemp -d)
echo "# E23 스케줄러 스코어: 통과한 노드 중 어디로 가나 ($(date '+%F %T %Z'), Mac 에서 ./lab kubectl 로, 네임스페이스 w23)"

echo; echo "## 0. 지금 돌고 있는 스케줄러의 프로필 (kube-scheduler /configz, 마스터 127.0.0.1:10259)"
./lab ssh master -- sudo bash -s <<'R' > $T/configz.json
d=$(mktemp -d); grep client-certificate-data /etc/kubernetes/admin.conf | awk '{print $2}' | base64 -d > $d/c; grep client-key-data /etc/kubernetes/admin.conf | awk '{print $2}' | base64 -d > $d/k
curl -sk --cert $d/c --key $d/k https://127.0.0.1:10259/configz; rm -rf $d
R
python3 - $T/configz.json <<'P'
import json,sys
c=json.load(open(sys.argv[1]))['componentconfig']; p=c['profiles'][0]
print("profile:", p['schedulerName'], "| podInitialBackoffSeconds:", c['podInitialBackoffSeconds'], "| podMaxBackoffSeconds:", c['podMaxBackoffSeconds'])
print("multiPoint 로 켜진 플러그인(이름:점수 가중치, 0 = 점수를 매기지 않거나 가중치 없음):")
print("  " + " ".join(f"{x['name']}:{x.get('weight',0)}" for x in p['plugins']['multiPoint']['enabled']))
for pc in p['pluginConfig']:
    if pc['name']=='NodeResourcesFit': print("NodeResourcesFit scoringStrategy:", json.dumps(pc['args']['scoringStrategy']))
    if pc['name']=='NodeResourcesBalancedAllocation': print("NodeResourcesBalancedAllocation resources:", json.dumps(pc['args']['resources']))
P

# 노드별로 requests 합계(필터와 BalancedAllocation 이 쓰는 값)와
# requests 를 안 적은 컨테이너를 CPU 100m·메모리 200Mi 로 친 합계(LeastAllocated 점수가 쓰는 값)를 구하고,
# v1.37.2 소스의 공식대로 점수를 계산해 본다 (score 플러그인 중 이 실험에서 노드마다 값이 달라지는 셋만)
cat > $T/predict.py <<'P'
import json,sys
pods=json.load(open(sys.argv[1]))['items']; nodes=json.load(open(sys.argv[2]))['items']
cpu=int(sys.argv[3]); mem=int(sys.argv[4])*1024**2; pref=sys.argv[5]; req=sys.argv[6]
def qc(v):
    if v is None: return None
    v=str(v); return int(v[:-1]) if v.endswith('m') else int(float(v)*1000)
U={'Ki':1024,'Mi':1024**2,'Gi':1024**3,'K':1000,'M':1000**2,'G':1000**3}
def qm(v):
    if v is None: return None
    v=str(v)
    for s,m in U.items():
        if v.endswith(s): return int(float(v[:-len(s)])*m)
    return int(float(v))
def bal(rc,rm,ac,am):
    f1=min(rc/ac,1); f2=min(rm/am,1); return int((1-abs(f1-f2)/2)*100)
rows=[]
for n in nodes:
    name=n['metadata']['name']
    if any(t['effect']=='NoSchedule' for t in n['spec'].get('taints',[])): continue
    ac=qc(n['status']['allocatable']['cpu']); am=qm(n['status']['allocatable']['memory'])
    rc=rm=zc=zm=0
    for p in pods:
        if p['spec'].get('nodeName')!=name or p['status'].get('phase') in ('Succeeded','Failed'): continue
        for c in p['spec']['containers']:
            r=c.get('resources',{}).get('requests',{}); c1=qc(r.get('cpu')); m1=qm(r.get('memory'))
            rc+=c1 or 0; rm+=m1 or 0; zc+=c1 if c1 else 100; zm+=m1 if m1 else 200*1024**2
    npods=sum(1 for p in pods if p['spec'].get('nodeName')==name and p['status'].get('phase') not in ('Succeeded','Failed'))
    ok = rc+cpu<=ac and rm+mem<=am and npods+1<=int(n['status']['allocatable']['pods']) and (req=='-' or name==req)
    # least_allocated.go 의 leastRequestedScore: 요청 합이 할당 가능량보다 크면 그 자원은 0점, 아니면 (할당 가능량-요청 합)*100/할당 가능량 (정수 나눗셈)
    def least(r,cap): return 0 if cap==0 or r>cap else ((cap-r)*100)//cap
    fit=(least(zc+cpu,ac)*1 + least(zm+mem,am)*1)//2
    b=50+(50+bal(rc+cpu,rm+mem,ac,am)-bal(rc,rm,ac,am))//2
    aff=(100 if name==pref else 0)*2 if pref!='-' else 0
    rows.append((name,rc,zc,rm//1024**2,zm//1024**2,ok,fit,b,aff))
print("    노드          requests(cpu/mem)  점수용(cpu/mem)    필터  Fit  Balanced  NodeAffinity×2  합")
best=max([r[6]+r[7]+r[8] for r in rows if r[5]] or [None])
for r in rows:
    tot=r[6]+r[7]+r[8]
    print(f"    {r[0]:<13} {r[1]:>4}m/{r[3]:>4}Mi       {r[2]:>4}m/{r[4]:>4}Mi       {'통과' if r[5] else '탈락'}  {r[6]:>3}  {r[7]:>8}  {r[8]:>14}  {tot if r[5] else '-':>3}{'  ← 최고점' if r[5] and tot==best else ''}")
P
predict(){ $K get pods -A -o json > $T/pods.json; $K get nodes -o json > $T/nodes.json; python3 $T/predict.py $T/pods.json $T/nodes.json "$@"; }
waitnode(){ for i in $(seq 1 20); do n=$($K -n $NS get pod $1 -o jsonpath='{.spec.nodeName}' 2>/dev/null); [ -n "$n" ] && { echo "$n"; return; }; sleep 1; done; echo "<none>"; }
mkpod(){ # 이름 cpu(m) mem(Mi) 선호노드|- 필수노드|-
  local aff=""
  [ "$4" != "-" ] && aff="  affinity:
    nodeAffinity:
      preferredDuringSchedulingIgnoredDuringExecution:
      - weight: 100
        preference:
          matchExpressions: [{key: kubernetes.io/hostname, operator: In, values: [$4]}]"
  [ "$5" != "-" ] && aff="  affinity:
    nodeAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        nodeSelectorTerms:
        - matchExpressions: [{key: kubernetes.io/hostname, operator: In, values: [$5]}]"
  cat <<Y | $K apply -f - >/dev/null
apiVersion: v1
kind: Pod
metadata: {name: $1, namespace: $NS, labels: {exp: w23}}
spec:
$aff
  terminationGracePeriodSeconds: 0
  containers:
  - name: pause
    image: $IMG
    resources: {requests: {cpu: ${2}m, memory: ${3}Mi}}
Y
}

$K create namespace $NS >/dev/null

echo; echo "## 1. 선호(preferred): worker3 를 weight 100 으로 선호하는 파드(CPU 500m) 4개를 하나씩"
echo "# | affinity.nodeAffinity.preferredDuringSchedulingIgnoredDuringExecution: [{weight: 100, preference: kubernetes.io/hostname In [k8s-worker3]}]"
for i in 1 2 3 4; do
  echo "$(ts) pref-$i 만들기 직전 계산:"; predict 500 32 k8s-worker3 -
  mkpod pref-$i 500 32 k8s-worker3 -; echo "$(ts) pref-$i → $(waitnode pref-$i)"
done
$K -n $NS get pods -o wide --no-headers | awk '{print "  "$1, $3, $7}'
$K -n $NS delete pod -l exp=w23 --wait=true >/dev/null; echo "$(ts) pref 파드 삭제"

echo; echo "## 2. 필수(required): 같은 조건을 requiredDuringSchedulingIgnoredDuringExecution 으로 바꾼 파드 4개"
for i in 1 2 3 4; do mkpod req-$i 500 32 - k8s-worker3; echo "$(ts) req-$i → $(waitnode req-$i)"; done
sleep 3
$K -n $NS get pods -o wide --no-headers | awk '{print "  "$1, $3, $7}'
echo "$(ts) req-4 이벤트:"; $K -n $NS get events --field-selector involvedObject.name=req-4 -o 'custom-columns=REASON:.reason,MESSAGE:.message' --no-headers | tail -1
$K -n $NS delete pod -l exp=w23 --wait=true >/dev/null; echo "$(ts) req 파드 삭제"

echo; echo "## 3. 조건 없음: CPU 300m·메모리 64Mi 를 요청하는 파드 6개를 하나씩 (LeastAllocated + BalancedAllocation)"
for i in 1 2 3 4 5 6; do
  echo "$(ts) spread-$i 만들기 직전 계산:"; predict 300 64 - -
  mkpod spread-$i 300 64 - -; echo "$(ts) spread-$i → $(waitnode spread-$i)"
done
$K -n $NS get pods -o wide --no-headers | awk '{print "  "$1, $3, $7}'

echo; echo "## 4. 정리"
$K delete namespace $NS --wait=true >/dev/null && echo "$(ts) 네임스페이스 $NS 삭제"
rm -rf $T
