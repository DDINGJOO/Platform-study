#!/usr/bin/env bash
# 36편: API 서버가 kubelet(10250)에 붙을 때 확인하지 않는 kubelet 서빙 인증서는 누가 서명했나. 조회만 한다.
# 실습 저장소 루트(./lab 이 있는 곳)에서 bash <이 스크립트> 로 실행
set -u
echo "# kubelet 서빙 인증서와 API 서버의 kubelet 관련 플래그 ($(date '+%F %T %Z'))"
echo; echo "## 1. API 서버 매니페스트의 kubelet 관련 플래그 (master)"
./lab ssh master -- sudo grep -- '--kubelet' /etc/kubernetes/manifests/kube-apiserver.yaml
echo "  --kubelet-certificate-authority 줄 수: $(./lab ssh master -- sudo grep -c -- '--kubelet-certificate-authority' /etc/kubernetes/manifests/kube-apiserver.yaml)"
for n in 1 2 3; do
  echo; echo "## 2-$n. worker$n 의 kubelet 서빙 인증서"
  ./lab ssh $n -- sudo bash -s <<'R'
echo "  serverTLSBootstrap 줄 수(/var/lib/kubelet/config.yaml): $(grep -c serverTLSBootstrap /var/lib/kubelet/config.yaml)"
openssl x509 -in /var/lib/kubelet/pki/kubelet.crt -noout -subject -issuer | sed 's/^/  /'
R
done
