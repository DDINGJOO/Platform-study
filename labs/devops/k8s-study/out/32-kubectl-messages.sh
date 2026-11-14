#!/usr/bin/env bash
# 32편: 관문마다 kubectl 이 마지막에 보여 주는 오류 문구. worker1 에서 빈 kubeconfig(/dev/null)로 설정을 하나씩 바꿔 get pods 를 보낸다.
# (자격을 아예 주지 않으면 kubectl 이 사용자 이름을 물어 오므로, 모든 경우에 토큰은 실어 보낸다.)
# 조회만 한다(클러스터 상태를 바꾸지 않음). 실습 저장소 루트(./lab 이 있는 곳)에서 bash <이 스크립트> 로 실행
set -u
echo "# 32편: 관문별 kubectl 오류 문구 ($(date '+%F %T %Z'), Mac 에서 실습 저장소 루트로 bash 32-kubectl-messages.sh 실행, 조회만)"
./lab ssh 1 -- bash -s <<'R'
k() { kubectl --kubeconfig=/dev/null "$@" -n default get pods </dev/null 2>&1 | tail -1; }
echo
echo "## 관문 0 TLS: 서버 인증서를 확인할 CA 를 주지 않음 (토큰은 실음)"
echo "worker1\$ kubectl --kubeconfig=/dev/null --server=https://192.168.104.1:6443 --token=not-a-real-token -n default get pods"
k --server=https://192.168.104.1:6443 --token=not-a-real-token
echo
echo "## 관문 0 TLS: https 포트에 http 로"
echo "worker1\$ kubectl --kubeconfig=/dev/null --server=http://192.168.104.1:6443 --token=not-a-real-token -n default get pods"
k --server=http://192.168.104.1:6443 --token=not-a-real-token
echo
echo "## 관문 1 인증: CA 는 맞고 토큰이 틀림"
echo "worker1\$ kubectl --kubeconfig=/dev/null --server=https://192.168.104.1:6443 --certificate-authority=/etc/kubernetes/pki/ca.crt --token=not-a-real-token -n default get pods"
k --server=https://192.168.104.1:6443 --certificate-authority=/etc/kubernetes/pki/ca.crt --token=not-a-real-token
R
