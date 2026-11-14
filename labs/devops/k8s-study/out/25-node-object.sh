#!/usr/bin/env bash
# 노드도 API 객체다: kubelet 이 무엇을 얼마나 자주 보고하고, KCM 이 무엇을 기준으로 노드 가용성을 판단하나 (Mac 에서 실행)
cd "$(dirname "$0")/../.."   # 실습 저장소 루트 (./lab 이 있는 곳)
K="./lab kubectl"; ts(){ date '+%T'; }
N=k8s-worker1
echo "# E13 노드 객체와 하트비트 ($(date '+%F %T %Z'))"
echo; echo "## 1. Node 객체의 status.conditions ($N)"
$K get node $N -o jsonpath='{range .status.conditions[*]}{.type}{"\t"}{.status}{"\t"}{.reason}{"\t"}hb={.lastHeartbeatTime}{"\n"}{end}' | column -t
echo; echo "## 2. Node 객체의 그 밖의 필드"
$K get node $N -o jsonpath='capacity:    cpu={.status.capacity.cpu} memory={.status.capacity.memory} pods={.status.capacity.pods}{"\n"}allocatable: cpu={.status.allocatable.cpu} memory={.status.allocatable.memory} pods={.status.allocatable.pods}{"\n"}addresses:   {.status.addresses[*].address}{"\n"}nodeInfo:    kubelet={.status.nodeInfo.kubeletVersion} runtime={.status.nodeInfo.containerRuntimeVersion} os={.status.nodeInfo.osImage} kernel={.status.nodeInfo.kernelVersion}{"\n"}spec:        podCIDR={.spec.podCIDR} unschedulable={.spec.unschedulable} taints={.spec.taints}{"\n"}'
echo; echo "## 3. 하트비트 ① Lease (kube-node-lease 네임스페이스, 노드마다 하나)"
$K -n kube-node-lease get lease -o custom-columns='NAME:.metadata.name,HOLDER:.spec.holderIdentity,DURATION:.spec.leaseDurationSeconds,RENEW:.spec.renewTime'
echo "$N Lease renewTime 을 4초마다:"
for i in $(seq 1 7); do echo "  $(ts) renewTime=$($K -n kube-node-lease get lease $N -o jsonpath='{.spec.renewTime}') | Node Ready lastHeartbeatTime=$($K get node $N -o jsonpath='{.status.conditions[?(@.type=="Ready")].lastHeartbeatTime}')"; sleep 4; done
echo; echo "## 4. kubelet 쪽 주기 (실행 중인 kubelet 설정, /configz)"
$K get --raw /api/v1/nodes/$N/proxy/configz | python3 -c 'import json,sys;c=json.load(sys.stdin)["kubeletconfig"];[print(f"  {k} = {c.get(k)}") for k in ("nodeStatusUpdateFrequency","nodeStatusReportFrequency","nodeLeaseDurationSeconds","maxPods","evictionHard")]'
echo; echo "## 5. 판단하는 쪽: KCM node-lifecycle-controller 기본값 (kube-controller-manager --help)"
$K -n kube-system exec kube-controller-manager-k8s-master -- kube-controller-manager --help 2>/dev/null | grep -A1 -E -- '--node-monitor-grace-period|--node-monitor-period|--node-startup-grace-period|--node-eviction-rate ' | sed 's/^ *//' | grep -v '^--$'
echo "우리 KCM 에 이 플래그를 따로 준 것: $($K -n kube-system get pod kube-controller-manager-k8s-master -o jsonpath='{.spec.containers[0].command}' | tr ',' '\n' | grep -c node-monitor)개 (= 기본값 사용)"
echo; echo "## 6. 노드 객체를 고쳐서 관리하기: cordon (spec.unschedulable)"
echo "$(ts) mac\$ kubectl cordon k8s-worker3"; $K cordon k8s-worker3 >/dev/null
$K get node k8s-worker3 -o jsonpath='  spec.unschedulable={.spec.unschedulable} taints={.spec.taints[*].key}:{.spec.taints[*].effect}{"\n"}'
$K get node k8s-worker3 --no-headers | awk '{print "  "$1, $2}'
echo "$(ts) mac\$ kubectl uncordon k8s-worker3"; $K uncordon k8s-worker3 >/dev/null
$K get node k8s-worker3 -o jsonpath='  spec.unschedulable={.spec.unschedulable} taints={.spec.taints}{"\n"}'
