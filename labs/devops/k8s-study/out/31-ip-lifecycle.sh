#!/usr/bin/env bash
# 파드 IP 는 언제 누가 할당하고 언제 반납하나: kubelet → containerd → CNI(calico) → calico-ipam → IPAM 블록·핸들 (Mac 에서 실행)
cd "$(dirname "$0")/../.."   # 실습 저장소 루트 (./lab 이 있는 곳)
K="./lab kubectl"; ts(){ date '+%T'; }
BLK=$($K get blockaffinities.crd.projectcalico.org -o jsonpath='{range .items[?(@.spec.node=="k8s-worker1")]}{.spec.cidr}{end}')
BN=$(echo "$BLK" | tr './' '--')
blk(){ $K get ipamblocks.crd.projectcalico.org $BN -o json | python3 -c '
import json,sys;b=json.load(sys.stdin)["spec"];a=b["allocations"]
print("블록", b["cidr"], "사용", "%d/%d," % (sum(x is not None for x in a), len(a)), "미할당", len(b["unallocated"]))'; }
hcnt(){ $K get ipamhandles.crd.projectcalico.org --no-headers | wc -l | tr -d ' '; }
cali(){ ./lab ssh 1 -- sh -c "ip -br link | grep -c '^cali'"; }
echo "# E9 파드 IP 의 할당과 반납 ($(date '+%F %T %Z')), worker1 블록 $BLK"
echo; echo "## 0. worker1 의 CNI 설정 (/etc/cni/net.d/10-calico.conflist 요약)"
./lab ssh 1 -- sudo python3 -c "import json;c=json.load(open('/etc/cni/net.d/10-calico.conflist'));p=c['plugins'][0];print('name=',c['name'],'| plugin type=',p['type'],'| ipam type=',p['ipam']['type'],'| datastore=',p['datastore_type'],'| 그다음 plugin=',c['plugins'][1]['type'])"
echo "CNI 바이너리: $(./lab ssh 1 -- ls /opt/cni/bin | grep -E '^calico' | paste -sd' ' -)"
echo; echo "## 1. 만들기 전"
echo "$(ts) $(blk) | IPAM 핸들 $(hcnt)개 | worker1 cali 인터페이스 $(cali)개"
echo; echo "## 2. 파드 생성 (worker1 고정)"
echo "$(ts) mac\$ kubectl run ipam-demo --image=registry.k8s.io/pause:3.10.2 (nodeSelector hostname=k8s-worker1)"
$K run ipam-demo --image=registry.k8s.io/pause:3.10.2 --image-pull-policy=IfNotPresent \
  --overrides='{"spec":{"nodeSelector":{"kubernetes.io/hostname":"k8s-worker1"}}}' >/dev/null
$K wait --for=condition=Ready pod/ipam-demo --timeout=60s >/dev/null
IP=$($K get pod ipam-demo -o jsonpath='{.status.podIP}'); CID=$($K get pod ipam-demo -o jsonpath='{.metadata.annotations.cni\.projectcalico\.org/containerID}')
echo "$(ts) 파드 IP $IP"
echo "파드 annotation (Calico CNI 가 붙임):"
$K get pod ipam-demo -o json | python3 -c 'import json,sys;a=json.load(sys.stdin)["metadata"]["annotations"];[print("  ",k,"=",v[:20]+"…" if k.endswith("containerID") else v) for k,v in a.items() if "projectcalico" in k]'
echo; echo "## 3. 할당 기록: IPAM 핸들과 블록"
echo "$(ts) $(blk) | IPAM 핸들 $(hcnt)개 | worker1 cali 인터페이스 $(cali)개"
H="k8s-pod-network.$CID"; echo "핸들 이름: k8s-pod-network.${CID:0:12}… → $($K get ipamhandles.crd.projectcalico.org "$H" -o jsonpath='{.spec.block}' 2>&1)"
$K get ipamblocks.crd.projectcalico.org $BN -o json | IP="$IP" python3 -c '
import json,sys,os,ipaddress;b=json.load(sys.stdin)["spec"];ip=ipaddress.ip_address(os.environ["IP"])
o=int(ip)-int(ipaddress.ip_network(b["cidr"]).network_address);i=b["allocations"][o];at=b["attributes"][i]
print("블록의 %d번 칸 → attributes[%d] handle=%s… secondary=%s" % (o, i, at["handle_id"][:28], at.get("secondary")))'
echo; echo "## 4. worker1 노드 안: veth(cali*) 와 /32 경로"
./lab ssh 1 -- sh -c "ip route show $IP; ip -br link show \$(ip route show $IP | awk '{print \$3}')"
echo "worker1 → $IP ping: $(./lab ssh 1 -- ping -c1 -W1 $IP | grep -oE '[0-9]+ received')"
echo; echo "## 5. CNI 로그 (/var/log/calico/cni/cni.log, ADD)"
./lab ssh 1 -- sudo grep "${CID:0:12}" /var/log/calico/cni/cni.log | grep -E 'ADD|assigned|Calico CNI IPAM|Wrote updated|Populated endpoint' | cut -c1-200 | head -8
echo; echo "## 6. 파드 삭제"
echo "$(ts) mac\$ kubectl delete pod ipam-demo"; $K delete pod ipam-demo --wait=true >/dev/null
echo "$(ts) $(blk) | IPAM 핸들 $(hcnt)개 | worker1 cali 인터페이스 $(cali)개"
echo "핸들 조회: $($K get ipamhandles.crd.projectcalico.org "$H" 2>&1 | head -1 | cut -c1-80)"
echo "worker1 의 $IP 경로: [$(./lab ssh 1 -- ip route show $IP)]"
echo; echo "## 7. CNI 로그 (DEL)"
./lab ssh 1 -- sudo grep "${CID:0:12}" /var/log/calico/cni/cni.log | grep -E 'DEL|Releas|release' | cut -c1-200 | head -8
