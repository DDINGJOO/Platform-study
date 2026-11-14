#!/usr/bin/env bash
# 27편 보강: 한도를 넘긴 프로세스가 PID 1 이 아닌데 왜 컨테이너 전체가 OOMKilled 로 다시 떴나 (memory.oom.group)
# Mac 에서 실행. 네임스페이스 w27 만 만들고 끝나면 지운다.
cd "${LAB:?실습 저장소(./lab 이 있는 곳) 경로를 LAB 에 넣는다}"
K="./lab kubectl"; ts(){ date '+%T'; }
echo "# 27편 보강 memory.oom.group ($(date '+%F %T %Z'))"
$K create ns w27 >/dev/null
cat <<Y | $K -n w27 apply -f - >/dev/null
apiVersion: v1
kind: Pod
metadata: {name: oom-demo}
spec:
  nodeSelector: {kubernetes.io/hostname: k8s-worker1}
  terminationGracePeriodSeconds: 5
  containers:
  - name: box
    image: docker.io/library/busybox:1.36.1
    command: ["sh","-c","sleep 3600"]
    resources:
      requests: {cpu: 200m, memory: 64Mi}
      limits:   {cpu: 200m, memory: 64Mi}
Y
$K -n w27 wait --for=condition=Ready pod/oom-demo --timeout=120s >/dev/null
echo "$(ts) w27/oom-demo Ready (worker1, busybox:1.36.1, cpu 200m / memory 64Mi, requests = limits)"

echo; echo "## 1. kubelet 설정의 singleProcessOOMKill (/configz, 값이 없으면 기본값)"
$K get --raw /api/v1/nodes/k8s-worker1/proxy/configz | python3 -c 'import json,sys;c=json.load(sys.stdin)["kubeletconfig"];print("  singleProcessOOMKill =", c.get("singleProcessOOMKill"))'

echo; echo "## 2. 컨테이너 cgroup 파일 (worker1)"
CID=$($K -n w27 get pod oom-demo -o jsonpath='{.status.containerStatuses[0].containerID}'); CID=${CID#containerd://}
./lab ssh 1 -- sudo CID=$CID bash -s <<'R'
PID=$(crictl inspect -o go-template --template '{{.info.pid}}' $CID)
CG=/sys/fs/cgroup$(cut -d: -f3 /proc/$PID/cgroup)
echo "  /sys/fs/cgroup 파일시스템 = $(stat -fc %T /sys/fs/cgroup)"
echo "  memory.oom.group = $(cat $CG/memory.oom.group)"
echo "  memory.max       = $(cat $CG/memory.max)"
echo "  컨테이너 안 프로세스: $(nsenter -t $PID -p -m ps -o pid,comm | tr -s ' ' | paste -sd'|' -)"
R

echo; echo "## 3. 한도를 넘기면 (kubectl exec 로 100MB 를 메모리에 쌓는 tail 을 띄움)"
N=$(./lab ssh 1 -- sudo sh -c 'dmesg | wc -l')
echo "$(ts) mac\$ kubectl -n w27 exec oom-demo -- sh -c 'head -c 100m /dev/zero | tail'"
$K -n w27 exec oom-demo -- sh -c 'head -c 100m /dev/zero | tail' >/dev/null 2>&1
sleep 3
echo "$(ts) restarts=$($K -n w27 get pod oom-demo -o jsonpath='{.status.containerStatuses[0].restartCount}') lastState=$($K -n w27 get pod oom-demo -o jsonpath='{.status.containerStatuses[0].lastState.terminated.reason} exitCode={.status.containerStatuses[0].lastState.terminated.exitCode}')"
echo "worker1 dmesg 새 줄 가운데 OOM 관련:"
./lab ssh 1 -- sudo sh -c "dmesg | tail -n +$((N+1))" | grep -E 'oom-kill:|Memory cgroup out of memory|memory.oom.group' | sed -E 's#Tasks in /[^ ]+#Tasks in <컨테이너 cgroup>#; s/cpuset=[^ ,]+/cpuset=<컨테이너>/; s/(oom|task)_memcg=[^ ,]+/\1_memcg=<cgroup>/g' | cut -c1-200

echo; echo "## 4. 정리"
$K delete ns w27 --wait=true >/dev/null && echo "$(ts) 네임스페이스 w27 삭제"
