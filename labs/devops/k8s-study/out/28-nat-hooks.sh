#!/usr/bin/env bash
# 28편 보강: 패킷이 KUBE-SERVICES 에 들어가는 입구(PREROUTING·OUTPUT)와 KUBE-MARK-MASQ 표시가 쓰이는 곳(KUBE-POSTROUTING) (Mac 에서 실행, worker1 조회만)
cd "$(dirname "$0")/../.."   # 실습 저장소 루트 (./lab 이 있는 곳)
echo "# worker1 nat 표의 kube-proxy 입구·출구 규칙 ($(date '+%F %T %Z'), Mac 에서 ./lab ssh 1 로 조회)"
echo "worker1\$ sudo iptables-save -t nat | grep -E '^-A (KUBE-MARK-MASQ|KUBE-POSTROUTING)|^-A POSTROUTING .*KUBE|^-A (OUTPUT|PREROUTING) .*KUBE-SERVICES'"
./lab ssh 1 -- sudo bash -s <<'R'
iptables-save -t nat 2>/dev/null | grep -E '^-A (KUBE-MARK-MASQ|KUBE-POSTROUTING)|^-A POSTROUTING .*KUBE|^-A (OUTPUT|PREROUTING) .*KUBE-SERVICES'
R
