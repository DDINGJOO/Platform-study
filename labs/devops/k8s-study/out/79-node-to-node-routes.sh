#!/usr/bin/env bash
# Node to Node: "클러스터의 라우팅 테이블"은 어디 있나: 노드마다 커널 라우팅 표, 그 근거인 Calico 블록 소유(blockaffinities) (Mac 에서 실행)
cd "$(dirname "$0")/../.."
K="./lab kubectl"
echo "# 26 노드 간 경로 ($(date '+%F %T %Z'))"
echo; echo "## Calico 가 노드마다 나눠 준 파드 블록 (blockaffinities CR = 클러스터에 저장된 원본)"
$K get blockaffinities.crd.projectcalico.org -o custom-columns='  NODE:.spec.node,CIDR:.spec.cidr,STATE:.spec.state' 2>&1
echo; echo "## 노드 IP"
$K get nodes -o custom-columns='  NODE:.metadata.name,INTERNAL-IP:.status.addresses[?(@.type=="InternalIP")].address' 
for n in k8s-master k8s-worker1 k8s-worker2 k8s-worker3; do
  echo; echo "## $n 의 커널 라우팅 표 중 파드 대역"
  limactl shell $n -- ip route | grep -E '^10\.244\.|^blackhole 10\.244' | grep -v ' dev cali' | sed 's/^/  /'
  echo "  (자기 파드 /32 경로 수: $(limactl shell $n -- ip route | grep -c ' dev cali'))"
done
echo; echo "## 경로를 누가 넣나: proto 번호와 노드의 BGP 데몬"
limactl shell k8s-worker3 -- sh -c 'grep -E "^(12|80)\b" /etc/iproute2/rt_protos /usr/share/iproute2/rt_protos 2>/dev/null; pgrep -a bird | head -2' | sed 's/^/  /'
