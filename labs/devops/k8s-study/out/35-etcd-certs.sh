#!/usr/bin/env bash
# 35편: etcd 가 받아 주는 클라이언트 인증서(etcd-ca 서명)는 어디에 몇 개 있나. 조회만 한다.
# 실습 저장소 루트(./lab 이 있는 곳)에서 실행한다.
echo "# etcd-ca 가 서명한 인증서는 어디에 있나 ($(date '+%F %T %Z'))"
echo
echo "## 1. k8s-master: etcd-ca 가 서명한 인증서 (subject / issuer / 확장 키 용도)"
./lab ssh master -- sudo bash -s <<'R'
for c in /etc/kubernetes/pki/etcd/*.crt /etc/kubernetes/pki/apiserver-etcd-client.crt; do
  printf '  %-28s %s | %s\n' "${c#/etc/kubernetes/pki/}" "$(openssl x509 -noout -subject -issuer -nameopt compat -in $c | tr '\n' ' ')" "$(openssl x509 -noout -ext extendedKeyUsage -in $c 2>/dev/null | tail -1 | sed 's/^ *//')"
done
echo "  etcd 의 클라이언트 인증서를 쓰는 정적 파드 플래그:"
grep -h -- '--etcd-' /etc/kubernetes/manifests/*.yaml | sed 's/^ */    /'
R
echo
echo "## 2. 워커의 /etc/kubernetes/pki"
for n in 1 2 3; do ./lab ssh $n -- sudo bash -s <<'R'
echo "  [$(hostname | sed 's/^lima-//')] $(ls /etc/kubernetes/pki | tr '\n' ' ')"
R
done
