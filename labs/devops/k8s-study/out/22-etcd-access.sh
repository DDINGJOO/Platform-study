#!/usr/bin/env bash
# 22편 보충: etcd 에 붙으려면 무엇이 필요한가, 데이터 파일은 어떻게 보호되나. 조회만 한다 (Mac 에서 실행)
cd "$(dirname "$0")/../.."   # 실습 저장소 루트 (./lab 이 있는 곳)
K="./lab kubectl"
echo "# 22편 보충: etcd 접근 조건과 데이터 파일 ($(date '+%F %T %Z'))"
echo; echo "## 1. etcd 플래그 (정적 파드 매니페스트의 command 에서 접속·인증·용량 관련만)"
$K -n kube-system get pod etcd-k8s-master -o jsonpath='{range .spec.containers[0].command[*]}{@}{"\n"}{end}' | grep -E 'listen-client|client-cert-auth|trusted-ca|cert-file|key-file|data-dir|quota' | grep -v peer | sed 's/^/  /'
echo "  --quota-backend-bytes 플래그 수: $($K -n kube-system get pod etcd-k8s-master -o jsonpath='{.spec.containers[0].command}' | grep -o quota-backend-bytes | wc -l | tr -d ' ')"
echo; echo "## 2. API 서버가 etcd 에 붙을 때 쓰는 플래그"
$K -n kube-system get pod kube-apiserver-k8s-master -o jsonpath='{range .spec.containers[0].command[*]}{@}{"\n"}{end}' | grep -E '^--etcd' | sed 's/^/  /'
echo "  --encryption-provider-config 플래그 수: $($K -n kube-system get pod kube-apiserver-k8s-master -o jsonpath='{.spec.containers[0].command}' | grep -o encryption-provider-config | wc -l | tr -d ' ')"
echo; echo "## 3. 두 인증서 비교 (마스터에서 openssl)"
./lab ssh master -- sudo bash -s <<'R'
for f in /etc/kubernetes/pki/apiserver-etcd-client.crt /etc/kubernetes/pki/etcd/server.crt; do
  echo "  $f"; openssl x509 -in $f -noout -subject -issuer -ext extendedKeyUsage | grep -v 'Extended Key Usage' | sed 's/^ */    /'
done
R
echo; echo "## 4. 클라이언트 인증서 없이 worker1 에서 etcd(192.168.104.1:2379) 에 붙어 보기"
./lab ssh 1 -- sudo bash -s <<'R'
echo "  worker1\$ curl -k https://192.168.104.1:2379/version"
curl -sk --max-time 5 https://192.168.104.1:2379/version; echo "  → curl 종료 코드 $?"
curl -vk --max-time 5 https://192.168.104.1:2379/version 2>&1 | grep -o 'alert certificate required' | head -1 | sed 's/^/  TLS: /'
echo "  worker1\$ ls /etc/kubernetes/pki/"; ls /etc/kubernetes/pki/ | sed 's/^/    /'
R
echo; echo "## 5. 마스터의 etcd 데이터 파일 권한"
./lab ssh master -- sudo bash -s <<'R'
stat -c '  %A %U:%G %n' /var/lib/etcd /var/lib/etcd/member /var/lib/etcd/member/snap /var/lib/etcd/member/snap/db
R
