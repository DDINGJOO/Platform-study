#!/usr/bin/env bash
# 컨트롤 플레인 HA 와 워커 용량: 지금 클러스터는 HA 인가, 워커 한 대가 빠지면 남은 노드에 들어가나 (Mac 에서 실행)
cd "$(dirname "$0")/../.."   # 실습 저장소 루트 (./lab 이 있는 곳)
K="./lab kubectl"
E=(-n kube-system exec etcd-k8s-master -- etcdctl --endpoints=https://127.0.0.1:2379 --cacert=/etc/kubernetes/pki/etcd/ca.crt --cert=/etc/kubernetes/pki/etcd/server.crt --key=/etc/kubernetes/pki/etcd/server.key)
echo "# E23 HA 여부와 워커 용량 ($(date '+%F %T %Z'))"
echo; echo "## 1. kubeadm ClusterConfiguration (kube-system/kubeadm-config)"
$K -n kube-system get cm kubeadm-config -o jsonpath='{.data.ClusterConfiguration}' | grep -nE 'controlPlaneEndpoint|etcd:|local:|external:|dataDir|kubernetesVersion|podSubnet|serviceSubnet' | sed 's/^/  /'
echo "  controlPlaneEndpoint 줄 수: $($K -n kube-system get cm kubeadm-config -o jsonpath='{.data.ClusterConfiguration}' | grep -c controlPlaneEndpoint)"
echo; echo "## 2. etcd 멤버와 컨트롤 플레인 노드"
$K "${E[@]}" member list -w table
echo "  control-plane 노드: $($K get nodes -l node-role.kubernetes.io/control-plane --no-headers | awk '{print $1}' | paste -sd' ' -)"
echo "  kubeconfig 의 API 서버 주소: $($K config view --minify -o jsonpath='{.clusters[0].cluster.server}')"
echo; echo "## 3. 워커별 할당 가능 자원과 requests 합 (kubectl describe node 의 Allocated resources)"
for n in k8s-worker1 k8s-worker2 k8s-worker3; do
  a=$($K get node $n -o jsonpath='cpu={.status.allocatable.cpu} memory={.status.allocatable.memory} pods={.status.allocatable.pods}')
  r=$($K describe node $n | awk '/Allocated resources/{f=1} f&&/^  cpu/{c=$2" "$3} f&&/^  memory/{m=$2" "$3} END{print "requests cpu "c" | memory "m}')
  p=$($K get pods -A --field-selector spec.nodeName=$n --no-headers | wc -l | tr -d ' ')
  echo "  $n: allocatable $a | $r | 파드 ${p}개"
done
echo; echo "## 4. 노드 토폴로지 라벨 (존·리전)"
$K get nodes -L topology.kubernetes.io/zone,topology.kubernetes.io/region --no-headers | awk '{print "  "$1, "zone="($6==""?"<none>":$6), "region="($7==""?"<none>":$7)}'
echo; echo "## 5. requests 를 안 적은 파드 (스케줄러 계산에는 0 으로 들어감)"
$K get pods -A -o json | python3 -c '
import json,sys
d=json.load(sys.stdin)["items"]; none=[]
for p in d:
    cs=p["spec"]["containers"]
    if all(not (c.get("resources",{}).get("requests")) for c in cs):
        o=(p["metadata"].get("ownerReferences") or [{}])[0].get("kind"); n=p["metadata"]["name"]
        n=n.rsplit("-",2)[0] if o=="ReplicaSet" else n.rsplit("-",1)[0] if o in ("DaemonSet","Job") else n
        none.append(p["metadata"]["namespace"]+"/"+n)
print("  전체 파드", len(d), "개 중 requests 없는 파드", len(none), "개")
import collections; [print("   ", k, v) for k,v in collections.Counter(none).most_common(8)]'
