#!/usr/bin/env bash
# 파드 하나를 만들고, 컨테이너를 재시작시키고, 지울 때 객체 필드와 노드 상태가 언제 바뀌고 누가 바꾸나 (Mac 에서 실행)
# 실습 저장소 루트에서 실행한다. 네임스페이스 blog-76 만 만들고 지운다. Deployment(replicas 1) + Service 하나.
K="./lab kubectl"; NS=blog-76
now(){ perl -MTime::HiRes=time -e 'printf "%.2f", time'; }
snap(){
  { $K get pod -n $NS -l app=life -o json; echo '@@@'; $K get endpointslice -n $NS -l kubernetes.io/service-name=life-svc -o json; } 2>/dev/null | python3 -c '
import json,sys
raw=sys.stdin.read().split("@@@")
pods=json.loads(raw[0])["items"]; eps=json.loads(raw[1])["items"]
out=[]
for p in sorted(pods,key=lambda x:x["metadata"]["creationTimestamp"]):
    m=p["metadata"]; s=p.get("status",{}); sp=p["spec"]
    ready=next((c["status"] for c in s.get("conditions",[]) if c["type"]=="Ready"),"-")
    rc=sum(cs.get("restartCount",0) for cs in s.get("containerStatuses",[]))
    out.append("%s uid=%s node=%s ip=%s phase=%s ready=%s restarts=%d%s"%(m["name"][-5:],m["uid"][:8],(sp.get("nodeName") or "-").replace("k8s-",""),s.get("podIP","-"),s.get("phase","-"),ready,rc," 삭제중" if m.get("deletionTimestamp") else ""))
e=[]
for sl in eps:
    for ep in sl.get("endpoints") or []:
        c=ep.get("conditions",{})
        f=lambda k: str(c.get(k)).lower()
        e.append("%s(r=%s,s=%s,t=%s)"%(ep["addresses"][0],f("ready"),f("serving"),f("terminating")))
print(" | ".join(out) or "(파드 없음)", "|| EndpointSlice:", " ".join(e) or "(없음)")
'
}
# $1 최대 초, $2 멈출 조건 함수
follow(){ local last="" cur t; while :; do cur=$(snap); t=$(perl -e "printf '%5.1f', $(now) - $T0"); [ "$cur" != "$last" ] && { echo "  +${t}s $cur"; last=$cur; }; $2 "$cur" && break; perl -e "exit($(now) - $T0 > $1 ? 0 : 1)" && { echo "  (시간 초과)"; break; }; sleep 0.2; done; }
node_state(){ # $1 노드, $2 파드 IP
  echo "    $1 의 라우팅 표에서 $2: $(limactl shell k8s-$1 -- sh -c "ip route show | grep -w '$2'" | sed 's/ *$//')"
  echo "    master 의 iptables 에서 $2 를 담은 줄 수: $(limactl shell k8s-master -- sudo sh -c "iptables-save 2>/dev/null | grep -c '$2'")"
}
echo "# 76 파드 하나의 생애 ($(date '+%F %T %Z'))"
$K create ns $NS >/dev/null

echo; echo "## 1. 만들기: Deployment life(replicas 1) + Service life-svc 를 apply 한 시각을 0 으로"
T0=$(now)
cat <<'Y' | $K apply -n $NS -f - | sed 's/^/  /'
apiVersion: apps/v1
kind: Deployment
metadata: {name: life}
spec:
  replicas: 1
  selector: {matchLabels: {app: life}}
  template:
    metadata: {labels: {app: life}}
    spec:
      containers:
      - {name: nginx, image: nginx:1.27-alpine, ports: [{containerPort: 80}]}
---
apiVersion: v1
kind: Service
metadata: {name: life-svc}
spec:
  selector: {app: life}
  ports: [{port: 80, targetPort: 80}]
Y
ready1(){ echo "$1" | grep -q 'ready=True' && echo "$1" | grep -q '(r=true'; }
follow 60 ready1
POD=$($K get pod -n $NS -l app=life -o jsonpath='{.items[0].metadata.name}')
NODE=$($K get pod $POD -n $NS -o jsonpath='{.spec.nodeName}' | sed 's/k8s-//'); PIP=$($K get pod $POD -n $NS -o jsonpath='{.status.podIP}'); UID8=$($K get pod $POD -n $NS -o jsonpath='{.metadata.uid}' | cut -c1-8)
echo "  누가 썼나: 파드 이벤트"
$K get events -n $NS --field-selector involvedObject.name=$POD --sort-by=.lastTimestamp -o custom-columns='SOURCE:.source.component,REASON:.reason' --no-headers | sed 's/^/    /'
echo "  누가 썼나: 파드 managedFields (작성자 / 하위 리소스)"
$K get pod $POD -n $NS -o jsonpath='{range .metadata.managedFields[*]}{.manager}{" / "}{.subresource}{"\n"}{end}' | sed 's/^/    /'
echo "  EndpointSlice 관리자 라벨: $($K get endpointslice -n $NS -l kubernetes.io/service-name=life-svc -o jsonpath='{.items[0].metadata.labels.endpointslice\.kubernetes\.io/managed-by}')"
echo "  노드 상태:"; node_state $NODE $PIP
echo "    master 의 iptables 에서 이 파드로 DNAT 하는 줄: $(limactl shell k8s-master -- sudo sh -c "iptables-save 2>/dev/null | grep -- '--to-destination $PIP'" | cut -c1-150)"

OTHER=$(for n in worker1 worker2 worker3; do [ $n != $NODE ] && { echo $n; break; }; done)
echo; echo "## 2. 파드를 다른 노드로 옮길 수 있나: spec.nodeName 을 $NODE 에서 $OTHER 로 바꾸는 patch"
$K patch pod $POD -n $NS --type=merge -p "{\"spec\":{\"nodeName\":\"k8s-$OTHER\"}}" 2>&1 | grep -E 'Forbidden|NodeName|patched' | cut -c1-200 | sed 's/^/  /'
echo "  patch 뒤 nodeName: $($K get pod $POD -n $NS -o jsonpath='{.spec.nodeName}')"

echo; echo "## 3. 다시 띄우기: 컨테이너 PID 1(nginx)에 SIGTERM (kubectl exec -- kill 1) 한 시각을 0 으로"
T0=$(now); $K exec $POD -n $NS -- kill 1
restarted(){ echo "$1" | grep -q 'ready=True restarts=1' && echo "$1" | grep -q '(r=true'; }
follow 60 restarted
echo "  lastState: $($K get pod $POD -n $NS -o jsonpath='{.status.containerStatuses[0].lastState.terminated.reason} exitCode={.status.containerStatuses[0].lastState.terminated.exitCode}')"

echo; echo "## 4. 지우기: kubectl delete pod $POD 한 시각을 0 으로 (ReplicaSet 이 새 파드를 만든다)"
T0=$(now); $K delete pod $POD -n $NS --wait=false | sed 's/^/  /'
replaced(){ ! echo "$1" | grep -q "uid=$UID8" && echo "$1" | grep -q 'ready=True' && [ "$(echo "$1" | grep -o '(r=' | wc -l | tr -d ' ')" = 1 ] && echo "$1" | grep -q '(r=true'; }
follow 90 replaced
NEW=$($K get pod -n $NS -l app=life -o jsonpath='{.items[0].metadata.name}')
echo "  새 파드 $NEW: node=$($K get pod $NEW -n $NS -o jsonpath='{.spec.nodeName}') ip=$($K get pod $NEW -n $NS -o jsonpath='{.status.podIP}') uid=$($K get pod $NEW -n $NS -o jsonpath='{.metadata.uid}' | cut -c1-8)"
echo "  옛 파드 IP 의 노드 상태:"; node_state $NODE $PIP

$K delete ns $NS --wait=false >/dev/null
echo; echo "(네임스페이스 $NS 삭제 요청)"
