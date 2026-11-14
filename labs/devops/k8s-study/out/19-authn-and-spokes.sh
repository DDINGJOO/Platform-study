#!/usr/bin/env bash
# 19편 보강: ① 인증 실패(401)와 인가 실패(403)를 나란히 ② 파드 네트워크에 있는 구성 요소도 결국 API 서버로 붙는가
# 조회만 한다(클러스터 상태를 바꾸지 않음). 실습 저장소 루트(./lab 이 있는 곳)에서 bash <이 스크립트> 로 실행
set -u
K="./lab kubectl"
API=https://192.168.104.1:6443/api/v1/namespaces/default/pods
echo "# 19편 보강: 401 과 403, API 서버에 붙는 다른 길 ($(date '+%F %T %Z'))"

echo; echo "## 1. 같은 GET 요청을 세 가지 자격으로 (worker1 에서 curl)"
for case in none bad; do
  if [ $case = none ]; then hdr=""; label="자격 없음(인증서·토큰 없이)"; else hdr="-H 'Authorization: Bearer not-a-real-token'"; label="가짜 토큰(Bearer not-a-real-token)"; fi
  out=$(./lab ssh 1 -- sh -c "curl -sk $hdr -w '\n%{http_code}' $API")
  code=$(printf '%s\n' "$out" | tail -1)
  msg=$(printf '%s\n' "$out" | sed '$d' | python3 -c 'import json,sys;d=json.load(sys.stdin);print(d.get("reason"),"|",d.get("message"))')
  echo "  $label → HTTP $code | $msg"
done
echo "  관리자 kubeconfig(클라이언트 인증서) → $($K get pods -n default --no-headers 2>&1 | wc -l | tr -d ' ')줄 (목록이 나옴)"

echo; echo "## 2. API 서버의 익명 인증 설정"
echo "  실행 플래그 중 --anonymous-auth: $($K -n kube-system get pod kube-apiserver-k8s-master -o jsonpath='{range .spec.containers[0].command[*]}{@}{"\n"}{end}' | grep -c -- '--anonymous-auth')개 (없으면 기본값)"
$K -n kube-system exec kube-apiserver-k8s-master -- kube-apiserver --help 2>/dev/null | grep -E -- '--anonymous-auth ' | sed 's/^ */  --help: /'
echo "  --enable-admission-plugins 설명 앞부분:"
$K -n kube-system exec kube-apiserver-k8s-master -- kube-apiserver --help 2>/dev/null | grep -E -- '--enable-admission-plugins strings' | sed 's/^ *//' | cut -c1-140 | sed 's/^/    /'

echo; echo "## 3. kubelet(10250) 에 자격 없이 (worker1 → worker1)"
echo "  curl -sk https://192.168.104.3:10250/pods → HTTP $(./lab ssh 1 -- curl -sk -o /dev/null -w '%{http_code}' https://192.168.104.3:10250/pods)"
echo "  kubelet 설정 authentication.anonymous.enabled: $(./lab ssh 1 -- sudo sh -c "grep -A1 'anonymous:' /var/lib/kubelet/config.yaml | tail -1 | tr -d ' '")"

echo; echo "## 4. kubernetes Service: 파드·노드 안 프로그램이 API 서버를 찾는 주소"
$K get svc kubernetes -n default --no-headers | awk '{print "  Service kubernetes "$3" "$5}'
$K get endpointslice -n default -l kubernetes.io/service-name=kubernetes --no-headers | awk '{print "  EndpointSlice → "$4":"$3}'

echo; echo "## 5. 6443 대신 10.96.0.1:443 으로 붙는 것들 (established, 프로세스별)"
echo "[k8s-worker1 호스트 네트워크: calico-node]"
./lab ssh 1 -- sudo sh -c "ss -tnpH state established dst 10.96.0.1 | grep -o 'pid=[0-9]*' | cut -d= -f2 | while read p; do echo \"  10.96.0.1:443 ← pid \$p \$(tr '\0' ' ' < /proc/\$p/cmdline)\"; done"
for n in 2 3; do
  echo "[k8s-worker$n 의 CoreDNS 파드 네트워크 네임스페이스 안]"
  ./lab ssh $n -- sudo sh -c "for c in \$(crictl ps --name coredns -q); do p=\$(crictl inspect --output go-template --template '{{.info.pid}}' \$c); nsenter -t \$p -n ss -tnpH state established | awk '{print \"  \"\$3\" → \"\$4\"  \"\$5}'; done"
done
echo "[calico-kube-controllers 파드 네트워크 네임스페이스 안]"
node=$($K -n kube-system get pod -l k8s-app=calico-kube-controllers -o jsonpath='{.items[0].spec.nodeName}')
n=${node#k8s-worker}
./lab ssh $n -- sudo sh -c "for c in \$(crictl ps --name calico-kube-controllers -q); do p=\$(crictl inspect --output go-template --template '{{.info.pid}}' \$c); nsenter -t \$p -n ss -tnpH state established | awk '{print \"  \"\$3\" → \"\$4\"  \"\$5}'; done"
echo "  (calico-kube-controllers 가 뜬 노드: $node)"
