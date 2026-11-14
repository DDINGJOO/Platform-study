#!/usr/bin/env bash
# kubelet 이 노드에서 하는 일: 설정·포트, 죽은 컨테이너 다시 띄우기, 정적 파드와 미러 파드 (Mac 에서 실행)
cd "$(dirname "$0")/../.."   # 실습 저장소 루트 (./lab 이 있는 곳)
K="./lab kubectl"; ts(){ date '+%T'; }
echo "# E14 kubelet ($(date '+%F %T %Z'))"
echo; echo "## 1. kubelet 설정 파일 (worker1 /var/lib/kubelet/config.yaml 에서 골라 봄)"
./lab ssh 1 -- sudo grep -E '^(staticPodPath|cgroupDriver|clusterDNS|clusterDomain|rotateCertificates|serverTLSBootstrap):|^  anonymous:|^    enabled:|^  webhook:|^  mode:|^- 10' /var/lib/kubelet/config.yaml
echo; echo "## 2. kubelet 이 여는 포트 (worker1)"
./lab ssh 1 -- sudo ss -ltnp | awk 'NR==1 || /kubelet/' | awk '{print $4, $6}'
echo "인증서 없이 10250 에 요청: $(./lab ssh master -- curl -sk -o /dev/null -w '%{http_code}' https://192.168.104.3:10250/pods)"
echo "노드 안에서 healthz(10248): $(./lab ssh 1 -- curl -s http://127.0.0.1:10248/healthz)"
echo; echo "## 3. 컨테이너가 죽으면 kubelet 이 같은 파드 안에서 다시 띄움 (restartPolicy: Always)"
P=$($K get pod -l app=myweb --field-selector spec.nodeName=k8s-worker1 -o jsonpath='{.items[0].metadata.name}')
UID0=$($K get pod $P -o jsonpath='{.metadata.uid}'); IP0=$($K get pod $P -o jsonpath='{.status.podIP}')
CID=$($K get pod $P -o jsonpath='{.status.containerStatuses[0].containerID}'); CID=${CID#containerd://}
PID=$(./lab ssh 1 -- sudo crictl inspect -o go-template --template '{{.info.pid}}' $CID)
echo "$(ts) $P uid=${UID0:0:8} ip=$IP0 restarts=$($K get pod $P -o jsonpath='{.status.containerStatuses[0].restartCount}') 컨테이너 pid=$PID"
echo "$(ts) worker1# kill -9 $PID   (nginx master)"; ./lab ssh 1 -- sudo kill -9 $PID
for i in 1 2 3 4; do sleep 3; echo "$(ts) restarts=$($K get pod $P -o jsonpath='{.status.containerStatuses[0].restartCount}') state=$($K get pod $P -o jsonpath='{.status.containerStatuses[0].state}' | cut -c1-60) uid=$($K get pod $P -o jsonpath='{.metadata.uid}' | cut -c1-8) ip=$($K get pod $P -o jsonpath='{.status.podIP}')"; done
echo "lastState: $($K get pod $P -o jsonpath='{.status.containerStatuses[0].lastState.terminated.reason} exitCode={.status.containerStatuses[0].lastState.terminated.exitCode}')"
$K get events --field-selector involvedObject.name=$P --sort-by=.lastTimestamp --no-headers | tail -3 | awk '{$1=""; print}' | cut -c1-140
echo; echo "## 4. 정적 파드: 파일이 원본, API 의 파드는 거울(미러 파드)"
S=kube-scheduler-k8s-master
$K -n kube-system get pod $S -o jsonpath='  config.source={.metadata.annotations.kubernetes\.io/config\.source} config.mirror={.metadata.annotations.kubernetes\.io/config\.mirror} owner={.metadata.ownerReferences[0].kind}/{.metadata.ownerReferences[0].name}{"\n"}'
echo "  staticPodPath 의 파일: $(./lab ssh master -- sudo ls /etc/kubernetes/manifests | paste -sd' ' -)"
SP0=$(./lab ssh master -- pgrep -xo kube-scheduler); U0=$($K -n kube-system get pod $S -o jsonpath='{.metadata.uid}')
echo "$(ts) 지우기 전: 파드 uid=${U0:0:8} | kube-scheduler pid=$SP0"
echo "$(ts) mac\$ kubectl -n kube-system delete pod $S"; $K -n kube-system delete pod $S --wait=false >/dev/null
for i in 1 2 3; do sleep 3; echo "$(ts) 파드: $($K -n kube-system get pod $S --no-headers 2>&1 | awk '{print $2, $3, $5}') uid=$($K -n kube-system get pod $S -o jsonpath='{.metadata.uid}' 2>/dev/null | cut -c1-8) | kube-scheduler pid=$(./lab ssh master -- pgrep -xo kube-scheduler)"; done
