#!/usr/bin/env bash
# 25-eviction.txt 의 강제 삭제(17:30:49 KST) 직후 worker3 에서 파드 IP 경로가 비어 있던 이유: worker3 calico-node(Felix) 로그에서 그 시각 줄을 찾는다 (Mac 에서 실행, 조회만)
cd "$(dirname "$0")/../.."   # 실습 저장소 루트 (./lab 이 있는 곳)
K="./lab kubectl"
CN=$($K -n kube-system get pod -l k8s-app=calico-node --field-selector spec.nodeName=k8s-worker3 -o jsonpath='{.items[0].metadata.name}')
echo "# worker3 Felix 가 강제 삭제된 파드의 경로를 걷어 낸 기록 ($(date '+%F %T %Z')), calico-node 파드 $CN, 로그 시각은 UTC (KST = UTC+9)"
echo "## 강제 삭제 시각(08:30:49Z) 앞뒤로 bn4k8(10.244.100.228)·zjdrs(10.244.100.251) 관련 줄"
$K -n kube-system logs "$CN" -c calico-node --since=3h 2>&1 \
  | grep -E '08:30:4[0-9]|08:30:5[0-9]' \
  | grep -E 'bn4k8|zjdrs|10\.244\.100\.(228|251)' \
  | grep -E 'Local endpoint deleted|WorkloadEndpointRemove|RouteRemove|Workload removed|Removing conntrack' \
  | sed -E 's/\[INFO\]\[[0-9]+\] //' | cut -c1-200
