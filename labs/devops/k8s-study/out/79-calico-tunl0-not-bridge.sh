#!/usr/bin/env bash
# Calico 노드에 파드를 잇는 브리지가 있나: 브리지 목록, tunl0 의 종류, 파드별 /32 경로와 다른 노드 블록 경로 (Mac 에서 실행)
cd "$(dirname "$0")/../.."
K="./lab kubectl"; NS=ch05; N=k8s-worker3
echo "# 25 Calico: tunl0 는 브리지인가 ($(date '+%F %T %Z')), 노드 $N"
for i in 1 2; do $K run pp$i -n $NS --image=busybox:1.37 --overrides="{\"spec\":{\"nodeName\":\"$N\"}}" --command -- sleep 3600 >/dev/null; done
$K wait pod/pp1 pod/pp2 -n $NS --for=condition=Ready --timeout=60s >/dev/null
$K get pod pp1 pp2 -n $NS -o custom-columns='  POD:.metadata.name,IP:.status.podIP,NODE:.spec.nodeName' 
S(){ limactl shell $N -- "$@"; }
echo; echo "## 노드의 브리지 인터페이스 (ip -br link show type bridge)"; S ip -br link show type bridge | sed 's/^/  /'; echo "  (줄 수: $(S ip -br link show type bridge | wc -l))"
echo; echo "## tunl0 의 종류 (ip -d link show tunl0)"; S ip -d link show tunl0 | sed -n '1,3p' | sed 's/^/  /'
echo; echo "## 이 노드 파드로 가는 경로: 파드마다 caliXXXX 로 /32"
for p in pp1 pp2; do ip=$($K get pod $p -n $NS -o jsonpath='{.status.podIP}'); echo "  $(S ip route get $ip | head -1)"; done
echo; echo "## 다른 노드의 파드 블록으로 가는 경로: tunl0 (IPIP)"; S ip route | grep tunl0 | sed 's/^/  /'
echo; echo "## 파드 안에서 본 eth0 와 기본 경로"; $K exec pp1 -n $NS -- sh -c 'ip -4 -o addr show eth0; ip route' | sed 's/^/  /'
$K delete pod pp1 pp2 -n $NS --grace-period=1 --wait=false >/dev/null
