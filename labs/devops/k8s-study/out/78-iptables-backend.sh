#!/usr/bin/env bash
# 노드의 iptables 명령은 어느 백엔드로 규칙을 쓰나 (iptables 모드 kube-proxy 의 규칙이 nft 에도 보이는 이유) (Mac 에서 실행, 조회만 한다)
echo "# 78 노드의 iptables 백엔드 ($(date '+%F %T %Z'))"
for n in k8s-master k8s-worker1 k8s-worker2 k8s-worker3; do
  printf '  %-12s %s\n' $n "$(limactl shell $n -- sudo iptables --version)"
done
