#!/usr/bin/env bash
# Node to Node: worker1 파드 → worker3 파드 ping 이 지나는 길: 출발 노드 경로 조회, 도착 노드 eth0 의 IPIP 캡처, tunl0 카운터 (Mac 에서 실행)
cd "$(dirname "$0")/../.."
K="./lab kubectl"; NS=ch05
echo "# 27 다른 노드 파드로 가는 길 ($(date '+%F %T %Z'))"
$K run src1 -n $NS --image=busybox:1.37 --overrides='{"spec":{"nodeName":"k8s-worker1"}}' --command -- sleep 3600 >/dev/null
$K run dst3 -n $NS --image=busybox:1.37 --overrides='{"spec":{"nodeName":"k8s-worker3"}}' --command -- sleep 3600 >/dev/null
$K wait pod/src1 pod/dst3 -n $NS --for=condition=Ready --timeout=60s >/dev/null
S=$($K get pod src1 -n $NS -o jsonpath='{.status.podIP}'); D=$($K get pod dst3 -n $NS -o jsonpath='{.status.podIP}')
echo "  src1 $S (worker1) → dst3 $D (worker3)"
echo; echo "## worker1 에서 dst3 로 가는 경로 (ip route get)"; limactl shell k8s-worker1 -- ip route get $D | head -1 | sed 's/^/  /'
echo; echo "## worker3 에서 dst3 로 가는 경로"; limactl shell k8s-worker3 -- ip route get $D | head -1 | sed 's/^/  /'
t3(){ limactl shell k8s-worker3 -- cat /sys/class/net/tunl0/statistics/rx_packets; }
r0=$(t3)
limactl shell k8s-worker3 -- sudo timeout 8 tcpdump -ni eth0 -c 4 'ip proto 4' > /tmp/ch05-27.cap 2>/dev/null &
sleep 2
$K exec src1 -n $NS -- ping -c 3 -i 0.3 -q $D | tail -2 | sed 's/^/  /'
wait
echo; echo "## worker3 eth0 캡처 (ip proto 4 = IPIP): 바깥 헤더는 노드 IP, 안쪽은 파드 IP"; sed 's/^/  /' /tmp/ch05-27.cap; rm -f /tmp/ch05-27.cap
echo "  worker3 tunl0 rx_packets: $r0 → $(t3)"
$K delete pod src1 dst3 -n $NS --grace-period=1 --wait=false >/dev/null
