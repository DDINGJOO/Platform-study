#!/usr/bin/env bash
# 라벨 · Service · IP 의 관계: 파드 IP, ClusterIP, externalIPs 로 각각 어디서 닿고, 라벨이 어긋나면 어떻게 되나 (Mac 에서 실행)
# externalIPs 에는 Mac 에서 닿는 worker3 의 lima1 주소(192.168.64.5)를 쓴다
cd "$(dirname "$0")/../.."
K="./lab kubectl"; NS=ch05; EXT=192.168.64.5
M(){ limactl shell k8s-master -- "$@"; }
echo "# 21 라벨 · Service · IP ($(date '+%F %T %Z'))"
cat <<Y | $K apply -n $NS -f - >/dev/null
apiVersion: v1
kind: Pod
metadata: {name: myweb1, labels: {app: myweb1}}
spec:
  containers:
  - {name: nginx-container, image: nginx:1.25.3-alpine, ports: [{containerPort: 80}]}
---
apiVersion: v1
kind: Service
metadata: {name: myweb-svc}
spec:
  selector: {app: myweb1}
  ports: [{port: 8001, targetPort: 80}]
  externalIPs: [$EXT]
Y
$K wait pod/myweb1 -n $NS --for=condition=Ready --timeout=120s >/dev/null
echo; echo "## kubectl get po,svc -o wide"
$K get po,svc -n $NS -o wide | sed 's/^/  /'
PIP=$($K get pod myweb1 -n $NS -o jsonpath='{.status.podIP}'); CIP=$($K get svc myweb-svc -n $NS -o jsonpath='{.spec.clusterIP}')
echo; echo "## Service 와 파드를 잇는 것: 셀렉터 → EndpointSlice"
echo "  selector=$($K get svc myweb-svc -n $NS -o jsonpath='{.spec.selector}')  파드 labels=$($K get pod myweb1 -n $NS -o jsonpath='{.metadata.labels}')"
$K get endpointslice -n $NS -l kubernetes.io/service-name=myweb-svc -o jsonpath='{range .items[*]}  EndpointSlice {.metadata.name}: {range .endpoints[*]}{.addresses[0]}:{..ports[0].port} ready={.conditions.ready} {end}{"\n"}{end}'
$K get endpointslice -n $NS -l kubernetes.io/service-name=myweb-svc -o jsonpath='{range .items[*]}  ports: {.ports}{"\n"}{end}'
c(){ printf '  %-46s → ' "$1"; shift; out=$("$@" 2>&1 | grep -o '<title>[^<]*</title>\|curl: ([0-9]*)[^"]*' | head -1); echo "${out:-응답 없음}"; }
echo; echo "## Service 를 만든 뒤 master 에서 ClusterIP 가 처음 응답하기까지 (0.2초 간격)"
t0=$(perl -MTime::HiRes=time -e 'printf "%.1f", time'); n=0
until M curl -s -m 1 -o /dev/null http://$CIP:8001; do n=$((n+1)); [ $n -gt 50 ] && break; sleep 0.2; done
echo "  실패 $n 번 뒤 응답, 대기 $(perl -e "printf '%.1f', $(perl -MTime::HiRes=time -e 'printf "%.1f", time') - $t0")초 (파드 Ready 확인 뒤부터)"
echo; echo "## 어디서 어디로 닿나 (curl -m 3)"
c "master → 파드 IP $PIP:80"            M curl -sS -m 3 http://$PIP:80
c "master → ClusterIP $CIP:8001"        M curl -sS -m 3 http://$CIP:8001
c "master → ClusterIP $CIP:80 (port 아님)" M curl -sS -m 3 http://$CIP:80
c "Mac → externalIP $EXT:8001"          curl -sS -m 3 http://$EXT:8001
c "Mac → worker1 192.168.64.3:8001 (외부 IP 아님)" curl -sS -m 3 http://192.168.64.3:8001
c "Mac → 파드 IP $PIP:80"               curl -sS -m 3 http://$PIP:80
c "Mac → ClusterIP $CIP:8001"           curl -sS -m 3 http://$CIP:8001
echo; echo "## externalIP 규칙은 worker3 만이 아니라 모든 노드의 kube-proxy 가 만든다 (master 의 규칙)"
echo "  kube-proxy mode: $($K -n kube-system get cm kube-proxy -o jsonpath='{.data.config\.conf}' | grep -E '^mode:' )"
M sudo sh -c "nft list ruleset 2>/dev/null | grep -c '$EXT' ; iptables-save 2>/dev/null | grep -c '$EXT'" | paste -sd' ' - | awk '{print "  master nft 줄 수: "$1", iptables 줄 수: "$2}'
M sudo sh -c "nft list ruleset 2>/dev/null | grep '$EXT' | head -3; iptables-save 2>/dev/null | grep '$EXT' | head -3" | cut -c1-170 | sed 's/^/    /'
echo; echo "## 라벨을 바꾸면 (app=myweb1 → app=other)"
$K label pod myweb1 -n $NS app=other --overwrite >/dev/null; sleep 3
$K get endpointslice -n $NS -l kubernetes.io/service-name=myweb-svc -o jsonpath='{range .items[*]}  EndpointSlice endpoints: {.endpoints}{"\n"}{end}'
c "master → ClusterIP $CIP:8001"        M curl -sS -m 3 http://$CIP:8001
c "master → 파드 IP $PIP:80 (파드는 그대로)" M curl -sS -m 3 http://$PIP:80
$K label pod myweb1 -n $NS app=myweb1 --overwrite >/dev/null; sleep 5
c "라벨 되돌린 뒤 master → ClusterIP"      M curl -sS -m 3 http://$CIP:8001
$K delete svc myweb-svc -n $NS >/dev/null; $K delete pod myweb1 -n $NS --wait=false >/dev/null
