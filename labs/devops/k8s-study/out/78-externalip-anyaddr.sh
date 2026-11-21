#!/usr/bin/env bash
# externalIPs 에 아무 주소나 적으면 클러스터 안에서 그 주소로 가는 요청이 어떻게 되나, ClusterIP·externalIP 는 누가 기록하나, NodePort 는 어느 노드 IP 에서 열리나 (Mac 에서 실행)
# 실습 저장소 루트에서 실행한다. 네임스페이스 blog-78 만 만들고 지운다. 203.0.113.10 은 문서용으로 예약된 대역(TEST-NET-3)의 주소라 실제로 쓰는 곳이 없다.
K="./lab kubectl"; NS=blog-78; FAKE=203.0.113.10
M(){ limactl shell k8s-master -- "$@"; }
c(){ printf '  %-44s → ' "$1"; shift; out=$("$@" 2>&1 | grep -o '<title>[^<]*</title>\|curl: ([0-9]*)[^"]*' | head -1); echo "${out:-응답 없음}"; }
echo "# 78 externalIPs 와 IP 종류 ($(date '+%F %T %Z'))"
$K create ns $NS >/dev/null
cat <<'Y' | $K apply -n $NS -f - >/dev/null
apiVersion: v1
kind: Pod
metadata: {name: web, labels: {app: web}}
spec:
  containers:
  - {name: nginx, image: nginx:1.27-alpine, ports: [{containerPort: 80}]}
---
apiVersion: v1
kind: Pod
metadata: {name: client}
spec:
  containers:
  - {name: curl, image: curlimages/curl:8.11.1, command: [sleep, "3600"]}
Y
$K wait pod/web pod/client -n $NS --for=condition=Ready --timeout=120s >/dev/null
PIP=$($K get pod web -n $NS -o jsonpath='{.status.podIP}')
echo "  web 파드 IP $PIP (노드 $($K get pod web -n $NS -o jsonpath='{.spec.nodeName}')), client 파드 노드 $($K get pod client -n $NS -o jsonpath='{.spec.nodeName}')"

echo; echo "## 1. Service 를 만들기 전, $FAKE:8001 로 요청"
c "client 파드 → $FAKE:8001"   $K exec client -n $NS -- curl -sS -m 3 http://$FAKE:8001
c "master 노드 → $FAKE:8001"   M curl -sS -m 3 http://$FAKE:8001

echo; echo "## 2. externalIPs: [$FAKE] 인 Service 를 만든다 (kubectl apply 출력 그대로)"
cat <<Y | $K apply -n $NS -f - 2>&1 | sed 's/^/  /'
apiVersion: v1
kind: Service
metadata: {name: ext-demo}
spec:
  selector: {app: web}
  ports: [{port: 8001, targetPort: 80}]
  externalIPs: [$FAKE]
Y
sleep 3
c "client 파드 → $FAKE:8001"   $K exec client -n $NS -- curl -sS -m 3 http://$FAKE:8001
c "client 파드 → $FAKE:80 (port 아님)" $K exec client -n $NS -- curl -sS -m 3 http://$FAKE:80
c "master 노드 → $FAKE:8001"   M curl -sS -m 3 http://$FAKE:8001
c "worker1 노드 → $FAKE:8001"  limactl shell k8s-worker1 -- curl -sS -m 3 http://$FAKE:8001
printf '  노드마다 %s 를 잡는 iptables 줄 수:' $FAKE
for n in k8s-master k8s-worker1 k8s-worker2 k8s-worker3; do printf ' %s=%s' ${n#k8s-} "$(limactl shell $n -- sudo sh -c "iptables-save 2>/dev/null | grep -c '$FAKE'")"; done; echo
printf '  노드마다 %s 가 붙은 인터페이스 수:' $FAKE
for n in k8s-master k8s-worker1 k8s-worker2 k8s-worker3; do printf ' %s=%s' ${n#k8s-} "$(limactl shell $n -- sh -c "ip -br addr | grep -c '$FAKE'")"; done; echo
M sudo sh -c "iptables-save 2>/dev/null | grep '$FAKE'" | cut -c1-170 | sed 's/^/    /'

echo; echo "## 3. 누가 이 주소들을 기록하나: ClusterIP 는 IPAddress 객체, externalIP 는 Service 의 문자열"
CIP=$($K get svc ext-demo -n $NS -o jsonpath='{.spec.clusterIP}')
echo "  ext-demo clusterIP=$CIP externalIPs=$($K get svc ext-demo -n $NS -o jsonpath='{.spec.externalIPs}')"
$K get ipaddress $CIP -o custom-columns='IPADDRESS:.metadata.name,PARENT:.spec.parentRef.resource,NAMESPACE:.spec.parentRef.namespace,NAME:.spec.parentRef.name,MANAGED-BY:.metadata.labels.ipaddress\.kubernetes\.io/managed-by' | sed 's/^/  /'
echo "  kubectl get ipaddress $FAKE → $($K get ipaddress $FAKE 2>&1)"
echo "  ServiceCIDR kubernetes: $($K get servicecidr kubernetes -o jsonpath='{.spec.cidrs}')"
echo "  Calico IPPool: $($K get ippools.crd.projectcalico.org default-ipv4-ippool -o jsonpath='{.spec.cidr} ipipMode={.spec.ipipMode} blockSize={.spec.blockSize}')"
echo "  API 서버 플래그:"; M sudo grep -E 'service-cluster-ip-range|admission-plugins' /etc/kubernetes/manifests/kube-apiserver.yaml | sed 's/^ */    /'

echo; echo "## 4. 같은 파드를 NodePort 로 열면 (Mac 에서 노드 lima1 주소마다)"
cat <<'Y' | $K apply -n $NS -f - 2>&1 | sed 's/^/  /'
apiVersion: v1
kind: Service
metadata: {name: np-demo}
spec:
  type: NodePort
  selector: {app: web}
  ports: [{port: 80, targetPort: 80}]
Y
NP=$($K get svc np-demo -n $NS -o jsonpath='{.spec.ports[0].nodePort}')
sleep 3
echo "  np-demo nodePort=$NP clusterIP=$($K get svc np-demo -n $NS -o jsonpath='{.spec.clusterIP}') externalTrafficPolicy=$($K get svc np-demo -n $NS -o jsonpath='{.spec.externalTrafficPolicy}')"
for ip in 192.168.64.2 192.168.64.3 192.168.64.4 192.168.64.5; do c "Mac → $ip:$NP (NodePort)" curl -sS -m 3 http://$ip:$NP; done

echo; echo "## 5. Mac 은 각 대역으로 가는 패킷을 어느 인터페이스로 보내나 (route -n get 의 interface 줄)"
for ip in $PIP $CIP 192.168.64.5; do printf '  %-16s %s\n' $ip "$(route -n get $ip 2>/dev/null | grep interface | sed 's/^ *//')"; done

$K delete ns $NS --wait=false >/dev/null
echo; echo "(네임스페이스 $NS 삭제 요청)"
