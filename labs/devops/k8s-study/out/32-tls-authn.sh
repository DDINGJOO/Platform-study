#!/usr/bin/env bash
# 32편: 관문 0(TLS)과 관문 1(인증). 같은 API 서버에 자격을 바꿔 가며 요청하고, 인증서 안의 이름과 그룹을 본다.
# 조회만 한다(클러스터 상태를 바꾸지 않음). 실습 저장소 루트(./lab 이 있는 곳)에서 bash <이 스크립트> 로 실행
set -u
K="./lab kubectl"
echo "# 32편: TLS 와 인증 ($(date '+%F %T %Z'), Mac 에서 실습 저장소 루트로 bash 32-tls-authn.sh 실행, 조회만)"

echo; echo "## 1. 관문 0 TLS: 클라이언트가 먼저 API 서버 인증서를 확인한다 (worker1 에서)"
./lab ssh 1 -- bash -s <<'R'
API=https://192.168.104.1:6443
echo "worker1\$ curl -sS $API/version                      # CA 를 주지 않으면"
curl -sS $API/version 2>&1 | head -1
echo "worker1\$ curl -sS http://192.168.104.1:6443/version    # TLS 없이 평문으로 보내면"
curl -sS http://192.168.104.1:6443/version 2>&1 | head -1; echo
echo "worker1\$ curl -sS --cacert /etc/kubernetes/pki/ca.crt $API/version | grep gitVersion"
curl -sS --cacert /etc/kubernetes/pki/ca.crt $API/version | grep gitVersion
echo "worker1\$ openssl s_client -connect 192.168.104.1:6443 | openssl x509 -noout -subject -issuer   # API 서버가 내민 인증서"
openssl s_client -connect 192.168.104.1:6443 </dev/null 2>/dev/null | openssl x509 -noout -subject -issuer
R

echo; echo "## 2. 관문 1 인증: 클라이언트 인증서의 CN 은 사용자 이름, O 는 그룹"
echo "master\$ (admin.conf 의 client-certificate-data 를 풀어) openssl x509 -noout -subject -issuer -enddate -ext extendedKeyUsage"
./lab ssh master -- sudo bash -s <<'R'
awk '/client-certificate-data/{print $2}' /etc/kubernetes/admin.conf | base64 -d | openssl x509 -noout -subject -issuer -enddate -ext extendedKeyUsage
R
echo "mac\$ kubectl auth whoami   (같은 인증서가 든 kubeconfig)"
$K auth whoami -o jsonpath='Username {.status.userInfo.username}{"\n"}Groups   {.status.userInfo.groups}{"\n"}'
echo "mac\$ kubectl get clusterrolebinding kubeadm:cluster-admins -o jsonpath='{.roleRef.kind}/{.roleRef.name} ← {.subjects}'"
$K get clusterrolebinding kubeadm:cluster-admins -o jsonpath='{.roleRef.kind}/{.roleRef.name} ← {.subjects}{"\n"}'
echo
echo "worker1\$ sudo openssl x509 -in /var/lib/kubelet/pki/kubelet-client-current.pem -noout -subject -issuer   (kubelet 이 쓰는 인증서)"
./lab ssh 1 -- sudo openssl x509 -in /var/lib/kubelet/pki/kubelet-client-current.pem -noout -subject -issuer
echo "worker1\$ sudo kubectl --kubeconfig /etc/kubernetes/kubelet.conf auth whoami"
./lab ssh 1 -- sudo kubectl --kubeconfig /etc/kubernetes/kubelet.conf auth whoami -o jsonpath='Username {.status.userInfo.username}{"\n"}Groups   {.status.userInfo.groups}{"\n"}'

echo; echo "## 3. 같은 경로에 자격을 바꿔 보낸다 (worker1 에서 curl, CA 확인은 함)"
./lab ssh 1 -- bash -s <<'R'
API=https://192.168.104.1:6443
C="curl -s --cacert /etc/kubernetes/pki/ca.crt"
for path in /version /livez /readyz /healthz /api /api/v1/namespaces/default/pods; do
  a=$($C -o /dev/null -w '%{http_code}' $API$path)
  b=$($C -o /dev/null -w '%{http_code}' -H 'Authorization: Bearer not-a-real-token' $API$path)
  printf '  %-32s 자격 없음 → %s   가짜 토큰 → %s\n' "$path" "$a" "$b"
done
echo "자격 없음 /api/v1/namespaces/default/pods 응답:"
$C $API/api/v1/namespaces/default/pods | python3 -c 'import json,sys;d=json.load(sys.stdin);print("  ",d["code"],d["reason"],"|",d["message"])'
echo "가짜 토큰 /version 응답:"
$C -H 'Authorization: Bearer not-a-real-token' $API/version | python3 -c 'import json,sys;d=json.load(sys.stdin);print("  ",d["code"],d["reason"],"|",d["message"])'
R

echo; echo "## 4. 익명 사용자가 열어 볼 수 있는 경로를 정한 기본 바인딩"
for b in system:public-info-viewer system:discovery system:basic-user; do
  echo "mac\$ kubectl get clusterrolebinding $b -o jsonpath='{.subjects[*].name}'"
  echo "  $($K get clusterrolebinding $b -o jsonpath='{.subjects[*].name}')"
done
echo "mac\$ kubectl get clusterrole system:public-info-viewer -o jsonpath='{.rules}'"
$K get clusterrole system:public-info-viewer -o jsonpath='{.rules}'; echo
echo "mac\$ kubectl auth can-i --list --as=system:anonymous --as-group=system:unauthenticated   (익명 사용자에게 자기 권한 목록을 묻게 하면)"
$K auth can-i --list --as=system:anonymous --as-group=system:unauthenticated

echo; echo "## 5. 익명 요청이 켜져 있는 설정과 그것을 쓰는 곳"
echo "  API 서버 실행 플래그 중 --anonymous-auth: $($K -n kube-system get pod kube-apiserver-k8s-master -o jsonpath='{range .spec.containers[0].command[*]}{@}{"\n"}{end}' | grep -c -- '--anonymous-auth')개"
$K -n kube-system exec kube-apiserver-k8s-master -- kube-apiserver --help 2>/dev/null | grep -E -- '--anonymous-auth ' | sed 's/^ */  --help: /'
echo "master\$ sudo grep -A6 -E 'livenessProbe|readinessProbe|startupProbe' /etc/kubernetes/manifests/kube-apiserver.yaml   (kubelet 이 API 서버 정적 파드를 검사하는 요청)"
./lab ssh master -- sudo grep -A6 -E 'livenessProbe|readinessProbe|startupProbe' /etc/kubernetes/manifests/kube-apiserver.yaml | grep -E 'Probe|host|path|port|scheme'
echo "master\$ sudo grep -B1 -A2 'name: probe-port' /etc/kubernetes/manifests/kube-apiserver.yaml"
./lab ssh master -- sudo grep -B1 -A2 'name: probe-port' /etc/kubernetes/manifests/kube-apiserver.yaml
echo "  프로브 정의 안의 httpHeaders 줄 수: $(./lab ssh master -- sudo grep -c httpHeaders /etc/kubernetes/manifests/kube-apiserver.yaml)"
