#!/usr/bin/env bash
# 실습 저장소의 shared/why/02-pod-and-pause/01-pod-sandbox.sh 를 옮긴 것. 실습 저장소 루트에서 실행한다.
# 확인: 파드 = 샌드박스(pause) + 앱 컨테이너. pause 가 붙잡는 네임스페이스, netns 파일, 앱 컨테이너 재시작 때 샌드박스 유지 여부 (조회만, worker1)
# 조회만 한다(파드 생성·설정 변경 없음). Mac 에서 실행: bash shared/why/02-pod-and-pause/01-pod-sandbox.sh | tee shared/why/02-pod-and-pause/01-pod-sandbox.txt
set -u
cd <home>/orca/workspaces/k8s/tang

echo "# 01 파드 샌드박스와 pause ($(date '+%Y-%m-%d %H:%M:%S %Z'))"
echo
echo "## 0. mac\$ kubectl: 관찰할 파드 (worker1)"
./lab kubectl get pod -n default myweb-859c4764d4-scshl -o wide --no-headers 2>&1 | awk '{print "  myweb-859c4764d4-scshl  restarts="$4" ip="$6" node="$7}'
./lab kubectl get pod -n kube-system kube-state-metrics-849dd5cd8d-zzpgc -o jsonpath='  kube-state-metrics-849dd5cd8d-zzpgc  restartCount={.status.containerStatuses[0].restartCount} ip={.status.podIP} lastTerminated={.status.containerStatuses[0].lastState.terminated.reason}/{.status.containerStatuses[0].lastState.terminated.finishedAt}{"\n"}'
echo "  shareProcessNamespace=true 인 파드 수(클러스터 전체): $(./lab kubectl get pods -A -o json | jq '[.items[] | select(.spec.shareProcessNamespace==true)] | length')"
echo "  myweb-859c4764d4-scshl 의 조건 (PodReadyToStartContainers = 샌드박스 준비 완료, 1.37 GA):"
./lab kubectl get pod -n default myweb-859c4764d4-scshl -o jsonpath='{range .status.conditions[*]}    {.type}={.status} {.lastTransitionTime}{"\n"}{end}'
echo

./lab ssh worker1 -- sudo bash -s <<'R'
MYWEB_POD=$(crictl pods --name myweb-859c4764d4-scshl --state ready -q | head -1)
KSM_POD=$(crictl pods --name kube-state-metrics-849dd5cd8d-zzpgc --state ready -q | head -1)
KP_POD=$(crictl pods --name kube-proxy --state ready -q | head -1)

echo "## 1. 런타임과 pause 이미지 (CRI ImageService, containerd 설정)"
crictl version | sed 's/^/  /'
crictl images | awk 'NR==1 || /pause/' | sed 's/^/  /'
echo "  containerd config dump:"
containerd config dump 2>/dev/null | grep -E "pinned_images|^ +sandbox = |sandboxer = |disable_pause_image_pull" | sed 's/^/    /'
echo "  CRI 가 pinned=true 로 알려 주는 이미지(kubelet 이미지 GC 가 건너뜀): $(crictl images -o json | jq -c '[.images[] | select(.pinned==true) | .repoTags[]]')  / 나머지 $(crictl images -o json | jq '[.images[] | select(.pinned!=true)] | length')개는 pinned=false"
P=$(crictl inspectp "$MYWEB_POD" | jq -r .info.pid)
echo "  pause 바이너리 버전 (샌드박스 rootfs 의 /pause -v): $(/run/containerd/io.containerd.runtime.v2.task/k8s.io/$MYWEB_POD/rootfs/pause -v 2>&1)"
echo

echo "## 2. Ready 샌드박스 수 = pause 프로세스 수"
echo "  crictl pods --state ready : $(crictl pods --state ready -q | wc -l)"
echo "  pgrep -x pause            : $(pgrep -x pause | wc -l)"
echo "  pause RSS 합계            : $(ps -o rss= -C pause | awk '{s+=$1} END {print s" KiB"}')"
echo "  pause 프로세스 (PID PPID 부모 USER RSS(KiB) STAT oom_score_adj):"
for p in $(pgrep -x pause); do
  pp=$(ps -o ppid= -p $p | tr -d ' ')
  printf "    %-7s %-7s %-16s %-6s %-5s %-4s %s\n" $p $pp "$(ps -o comm= -p $pp)" "$(ps -o user= -p $p)" "$(ps -o rss= -p $p | tr -d ' ')" "$(ps -o stat= -p $p)" "$(cat /proc/$p/oom_score_adj)"
done
echo

echo "## 3. 한 파드 안: pause 와 nginx 의 네임스페이스 비교 (myweb-859c4764d4-scshl, 샌드박스 ${MYWEB_POD:0:13})"
C=$(crictl ps --pod "$MYWEB_POD" --name nginx -q | head -1)
A=$(crictl inspect "$C" | jq -r .info.pid)
echo "  pause pid=$P (부모 $(ps -o comm= -p $(ps -o ppid= -p $P | tr -d ' ')))  nginx pid=$A (부모 $(ps -o comm= -p $(ps -o ppid= -p $A | tr -d ' ')))"
printf "  %-7s %-22s %-22s %s\n" ns pause nginx 같은가
for ns in net ipc uts pid mnt cgroup; do
  a=$(readlink /proc/$P/ns/$ns); b=$(readlink /proc/$A/ns/$ns)
  [ "$a" = "$b" ] && s=같음 || s=다름
  printf "  %-7s %-22s %-22s %s\n" $ns "$a" "$b" $s
done
echo "  NSpid(호스트 PID → 자기 PID 네임스페이스 안 PID): pause '$(grep NSpid /proc/$P/status | cut -f2-)'  nginx '$(grep NSpid /proc/$A/status | cut -f2-)'"
echo "  oom_score_adj: pause $(cat /proc/$P/oom_score_adj), nginx $(cat /proc/$A/oom_score_adj)"
echo "  cgroup: pause $(cut -d: -f3 /proc/$P/cgroup)"
echo "          nginx $(cut -d: -f3 /proc/$A/cgroup)"
echo

echo "## 4. 네트워크 네임스페이스는 파일로도 붙잡혀 있다 (containerd 가 먼저 만들고 bind mount)"
crictl inspectp "$MYWEB_POD" | jq -r '.info.runtimeSpec.linux.namespaces[] | "  pause spec namespace: \(.type) \(.path // "(새로 만듦)")"'
NETNS=$(crictl inspectp "$MYWEB_POD" | jq -r '.info.runtimeSpec.linux.namespaces[] | select(.type=="network") | .path')
echo "  $NETNS inode=$(stat -L -c %i $NETNS)   /proc/$P/ns/net inode=$(stat -L -c %i /proc/$P/ns/net)"
echo "  ip netns identify $P → $(ip netns identify $P)"
echo "  findmnt: $(findmnt -n -o TARGET,SOURCE,FSTYPE $NETNS | head -1)"
echo "  /var/run/netns 파일 수 $(ls /var/run/netns | wc -l) / Ready 샌드박스 중 hostNetwork 아닌 것 $(for s in $(crictl pods --state ready -q); do crictl inspectp $s | jq -r .status.linux.namespaces.options.network; done | grep -c POD)"
echo "  CRI 가 본 파드 IP $(crictl inspectp "$MYWEB_POD" | jq -r .status.network.ip), 그 netns 안 eth0: $(ip netns exec $(basename $NETNS) ip -4 -o addr show eth0 | awk '{print $4}')"
echo "  nginx 컨테이너 spec 의 네임스페이스 경로 (pause PID 의 /proc 경로로 들어간다):"
crictl inspect "$C" | jq -r '.info.runtimeSpec.linux.namespaces[] | "    \(.type) \(.path // "(새로 만듦)")"'
echo

echo "## 5. hostNetwork 파드에도 pause 는 있다 (kube-proxy, 샌드박스 ${KP_POD:0:13})"
KP=$(crictl inspectp "$KP_POD" | jq -r .info.pid)
echo "  CRI namespace options: $(crictl inspectp "$KP_POD" | jq -c .status.linux.namespaces.options)"
echo "  pause pid=$KP net=$(readlink /proc/$KP/ns/net)  호스트 PID1 net=$(readlink /proc/1/ns/net)"
echo

echo "## 6. 앱 컨테이너가 재시작해도 샌드박스(pause)·IP 는 그대로 (kube-state-metrics, 샌드박스 ${KSM_POD:0:13})"
crictl inspectp "$KSM_POD" | jq -r '"  샌드박스 attempt=\(.status.metadata.attempt) created=\(.status.createdAt) ip=\(.status.network.ip) pause pid=\(.info.pid)"'
echo "  pause 프로세스 시작 시각: $(ps -o lstart= -p $(crictl inspectp "$KSM_POD" | jq -r .info.pid))"
echo "  같은 POD ID 안의 컨테이너 (crictl ps -a --pod):"
crictl ps -a --pod "$KSM_POD" -o json | jq -r '.containers | sort_by(.metadata.attempt)[] | "    container \(.id[0:13]) attempt=\(.metadata.attempt) state=\(.state) createdAt(ns)=\(.createdAt) podSandboxId=\(.podSandboxId[0:13])"'
echo "  컨테이너 ID 별 시작 시각:"
for c in $(crictl ps -a --pod "$KSM_POD" -q); do
  crictl inspect "$c" | jq -r '"    \(.status.id[0:13]) attempt=\(.status.metadata.attempt) startedAt=\(.status.startedAt) finishedAt=\(.status.finishedAt) exitCode=\(.status.exitCode) reason=\(.status.reason)"'
done
echo

echo "## 7. 노드(VM) 재부팅 뒤에는 샌드박스가 새로 생겼다 (같은 파드 이름, NotReady 옛 샌드박스와 Ready 새 샌드박스)"
crictl pods -o json | jq -r '.items | group_by(.metadata.name)[] | select(length>1) | .[] | "  \(.metadata.name) sandbox=\(.id[0:13]) attempt=\(.metadata.attempt) state=\(.state) createdAt(ns)=\(.createdAt)"'
echo "  (옛 NotReady 샌드박스의 IP):"
for s in $(crictl pods --state notready -q); do crictl inspectp $s | jq -r '"    \(.status.metadata.name) attempt=\(.status.metadata.attempt) ip=\(.status.network.ip // "-") pid=\(.info.pid)"'; done
echo "  지금 IP:"
for s in $(crictl pods --state ready -q); do crictl inspectp $s | jq -r 'select(.status.linux.namespaces.options.network=="POD") | "    \(.status.metadata.name) attempt=\(.status.metadata.attempt) ip=\(.status.network.ip)"'; done
echo "  worker1 부팅 시각: $(uptime -s)"
R
