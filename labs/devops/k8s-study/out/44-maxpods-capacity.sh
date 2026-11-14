#!/usr/bin/env bash
# 실습 저장소의 shared/why/03-max-pods-110/01-maxpods-capacity.sh 를 옮긴 것. 실습 저장소 루트에서 실행한다.
# 03 maxPods 110: 노드 파드 상한(capacity/allocatable.pods, kubelet maxPods), podCIDR(/24), Calico IPAM 블록(/26), 노드별 파드 수(hostNetwork 구분), PLEG relist 시간, kubelet/containerd 자원 사용량을 조회만 한다
# 실습 저장소 루트(./lab 이 있는 곳)에서 bash shared/why/03-max-pods-110/01-maxpods-capacity.sh 로 실행 (Mac). 아무것도 바꾸지 않는다.
set -u
K="./lab kubectl"
NODES="k8s-master k8s-worker1 k8s-worker2 k8s-worker3"
ssh_name() { case "$1" in k8s-master) echo master;; k8s-worker1) echo worker1;; k8s-worker2) echo worker2;; k8s-worker3) echo worker3;; esac; }

echo "# 03 maxPods 110 조회 ($(date '+%F %T %Z')), Mac 에서 ./lab 으로 조회만"

echo; echo "## 1. 노드 객체: podCIDR, capacity/allocatable 의 pods, cpu"
$K get nodes -o custom-columns='NODE:.metadata.name,PODCIDR:.spec.podCIDR,CAP_PODS:.status.capacity.pods,ALLOC_PODS:.status.allocatable.pods,CPU:.status.capacity.cpu,MEM:.status.capacity.memory,KUBELET:.status.nodeInfo.kubeletVersion'

echo; echo "## 2. kubelet 설정: 파일(/var/lib/kubelet/config.yaml) 의 maxPods 줄 vs 실행 중 값(/configz)"
for n in $NODES; do
  f=$(./lab ssh "$(ssh_name $n)" -- sudo grep -i maxPods /var/lib/kubelet/config.yaml 2>/dev/null)
  c=$($K get --raw "/api/v1/nodes/$n/proxy/configz" | python3 -c 'import json,sys; k=json.load(sys.stdin)["kubeletconfig"]; print("maxPods=%s podPidsLimit=%s podsPerCore=%s" % (k.get("maxPods"), k.get("podPidsLimit"), k.get("podsPerCore",0)))')
  echo "  $n | 파일: [${f}] (비어 있으면 기본값) | configz: $c"
done

echo; echo "## 3. 노드에 /24 를 나눠 주는 쪽: kube-controller-manager 플래그와 kubeadm podSubnet"
./lab ssh master -- sudo grep -E -- '--(allocate-node-cidrs|cluster-cidr|node-cidr-mask-size)' /etc/kubernetes/manifests/kube-controller-manager.yaml
echo "  (--node-cidr-mask-size 줄이 없으면 IPv4 기본값 24)"
$K -n kube-system get cm kubeadm-config -o jsonpath='{.data.ClusterConfiguration}' | grep -E 'podSubnet|serviceSubnet' | sed 's/^/  kubeadm-config: /'

echo; echo "## 4. Calico 가 실제로 쓰는 것: IPPool blockSize, IPAMConfig, 노드별 블록(affinity)과 사용 칸 수"
$K get ippools.crd.projectcalico.org -o custom-columns='POOL:.metadata.name,CIDR:.spec.cidr,BLOCKSIZE:.spec.blockSize,IPIP:.spec.ipipMode'
$K get ipamconfigs.crd.projectcalico.org default -o jsonpath='  IPAMConfig: strictAffinity={.spec.strictAffinity} autoAllocateBlocks={.spec.autoAllocateBlocks} maxBlocksPerHost=[{.spec.maxBlocksPerHost}] (비어 있으면 미설정)'; echo
$K get ipamblocks.crd.projectcalico.org -o json | python3 -c '
import json,sys
rows=[]
for b in json.load(sys.stdin)["items"]:
    s=b["spec"]; used=sum(1 for a in s.get("allocations",[]) if a is not None)
    rows.append((s.get("affinity",""), s["cidr"], used, len(s.get("allocations",[]))))
for r in sorted(rows): print("  %-22s %-18s 사용 %3d / %d" % r)'
echo "  블록 첫 칸은 노드의 IPIP 터널 주소(tunl0)가 쓴다:"
$K get nodes -o custom-columns='  NODE:.metadata.name,IPIP_TUNNEL_ADDR:.metadata.annotations.projectcalico\.org/IPv4IPIPTunnelAddr' | sed 's/^/  /'

echo; echo "## 5. 노드별 파드 수: maxPods 는 hostNetwork 파드도 센다, 파드 IP 는 hostNetwork 가 아닌 파드만 쓴다"
$K get pods -A -o json | python3 -c '
import json,sys,collections
tot=collections.Counter(); hn=collections.Counter(); ds=collections.Counter()
for p in json.load(sys.stdin)["items"]:
    if p["status"].get("phase") in ("Succeeded","Failed"): continue
    n=p["spec"].get("nodeName","(미배치)"); tot[n]+=1
    if p["spec"].get("hostNetwork"): hn[n]+=1
    if any(o.get("kind")=="DaemonSet" for o in p["metadata"].get("ownerReferences",[])): ds[n]+=1
print("  %-12s %5s %12s %14s %10s %18s" % ("NODE","파드","hostNetwork","IP쓰는파드","DaemonSet","110 대비 남은 자리"))
for n in sorted(tot): print("  %-12s %5d %12d %14d %10d %18d" % (n, tot[n], hn[n], tot[n]-hn[n], ds[n], 110-tot[n]))'

echo; echo "## 6. PLEG relist (kubelet /metrics, 1초마다 컨테이너 런타임에 전체 목록을 다시 묻는 루프)"
for n in $NODES; do
  $K get --raw "/api/v1/nodes/$n/proxy/metrics" | python3 -c '
import sys,re
n=sys.argv[1]; m={}; b=[]
for l in sys.stdin:
    if l.startswith("#"): continue
    k,_,v=l.strip().rpartition(" ")
    m[k]=v
    if l.startswith("kubelet_pleg_relist_duration_seconds_bucket"): b.append((re.search(r"le=\"([^\"]+)\"",l).group(1), float(v)))
cnt=float(m.get("kubelet_pleg_relist_duration_seconds_count",0)); s=float(m.get("kubelet_pleg_relist_duration_seconds_sum",0))
ic=float(m.get("kubelet_pleg_relist_interval_seconds_count",0)); isum=float(m.get("kubelet_pleg_relist_interval_seconds_sum",0))
p99=next((le for le,c in b if cnt and c>=0.99*cnt),"?")
print("  %-12s relist %d회, 평균 %.2f ms, 99%%가 %s 초 이하 | relist 간격 평균 %.3f 초 | running_pods=%s running_containers(running)=%s" % (n, cnt, (s/cnt*1000 if cnt else 0), p99, (isum/ic if ic else 0), m.get("kubelet_running_pods","?"), m.get("kubelet_running_containers{container_state=\"running\"}","?")))' "$n"
done

echo; echo "## 7. 노드 에이전트 자원 (ps: RSS MiB, 누적 CPU 비율)"
for n in $NODES; do
  ./lab ssh "$(ssh_name $n)" -- sudo bash -s <<'R' | sed "s/^/  $n | /"
for p in kubelet containerd; do ps -C "$p" -o rss=,pcpu=,etime= | awk -v p="$p" '{printf "%s RSS=%.0fMiB CPU=%s%% 가동=%s  ", p, $1/1024, $2, $3}'; done
echo "| containerd-shim 수=$(pgrep -c -f containerd-shim)"
R
done

echo; echo "## 8. 한 줄 비교 (노드 하나 기준)"
echo "  maxPods(kubelet) = 110  |  podCIDR /24 = 256 주소(쿠버네티스가 나눈 대역, Calico IPAM 은 이걸 안 씀)  |  Calico 블록 /26 = 64 주소(모자라면 블록을 더 받음)"
