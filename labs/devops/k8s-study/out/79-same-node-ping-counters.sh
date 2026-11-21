#!/usr/bin/env bash
# 같은 노드 파드끼리 ping 하면 tunl0 를 지나가나: ping 20번 전후 tunl0 와 두 파드의 cali 인터페이스 패킷 수 비교 (Mac 에서 실행)
cd "$(dirname "$0")/../.."
K="./lab kubectl"; NS=ch05; N=k8s-worker3
echo "# 25b 같은 노드 파드 ping 과 인터페이스 카운터 ($(date '+%F %T %Z')), 노드 $N"
for i in 1 2; do $K run pp$i -n $NS --image=busybox:1.37 --overrides="{\"spec\":{\"nodeName\":\"$N\"}}" --command -- sleep 3600 >/dev/null; done
$K wait pod/pp1 pod/pp2 -n $NS --for=condition=Ready --timeout=60s >/dev/null
IP1=$($K get pod pp1 -n $NS -o jsonpath='{.status.podIP}'); IP2=$($K get pod pp2 -n $NS -o jsonpath='{.status.podIP}')
S(){ limactl shell $N -- "$@"; }
C1=$(S ip route get $IP1 | grep -o 'dev [^ ]*' | cut -d' ' -f2); C2=$(S ip route get $IP2 | grep -o 'dev [^ ]*' | cut -d' ' -f2)
echo "  pp1 $IP1 ↔ $C1 / pp2 $IP2 ↔ $C2"
cnt(){ for d in tunl0 $C1 $C2; do echo -n "$d rx=$(S cat /sys/class/net/$d/statistics/rx_packets) tx=$(S cat /sys/class/net/$d/statistics/tx_packets)  "; done; echo; }
echo "  전: $(cnt)"
$K exec pp1 -n $NS -- ping -c 20 -i 0.2 -q $IP2 | tail -2 | sed 's/^/  /'
echo "  후: $(cnt)"
$K delete pod pp1 pp2 -n $NS --grace-period=1 --wait=false >/dev/null
