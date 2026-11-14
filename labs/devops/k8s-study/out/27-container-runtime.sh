#!/usr/bin/env bash
# 컨테이너 런타임(containerd)이 하는 일: 이미지 받기, 자원 할당·격리(cgroup), 수명 주기. kubelet 은 CRI(gRPC)로만 부른다 (Mac 에서 실행)
cd "$(dirname "$0")/../.."   # 실습 저장소 루트 (./lab 이 있는 곳)
K="./lab kubectl"; ts(){ date '+%T'; }
IMG=docker.io/library/busybox:1.36.1
echo "# E16 컨테이너 런타임과 CRI ($(date '+%F %T %Z'))"
echo; echo "## 1. kubelet 이 런타임을 찾는 곳 (CRI 엔드포인트) 과 CRI 버전"
./lab ssh 1 -- sudo sh -c 'grep containerRuntimeEndpoint /var/lib/kubelet/config.yaml; crictl version'
echo; echo "## 2. 시작 전 worker1 에 busybox:1.36.1 이미지: $(./lab ssh 1 -- sudo crictl images | grep -cE 'busybox +1\.36\.1')개"
S=$(date '+%F %T')
cat <<Y | $K apply -f - >/dev/null
apiVersion: v1
kind: Pod
metadata: {name: cri-demo}
spec:
  nodeSelector: {kubernetes.io/hostname: k8s-worker1}
  terminationGracePeriodSeconds: 5
  containers:
  - name: box
    image: $IMG
    command: ["sh","-c","sleep 3600"]
    resources:
      requests: {cpu: 200m, memory: 64Mi}
      limits:   {cpu: 200m, memory: 64Mi}
Y
echo "$(ts) kubectl apply cri-demo (busybox, cpu 200m / memory 64Mi, requests = limits)"
$K wait --for=condition=Ready pod/cri-demo --timeout=120s >/dev/null
echo "$(ts) Ready, qosClass=$($K get pod cri-demo -o jsonpath='{.status.qosClass}')"
echo; echo "## 3. containerd 로그에 찍힌 CRI 호출 (생성)"
./lab ssh 1 -- sudo journalctl -u containerd --since "$S" --no-pager -o cat | grep -E 'RunPodSandbox|PullImage|ImageCreate|CreateContainer|StartContainer' | grep -vE 'ImageUpdate' | sed -E 's/^time="[0-9-]+T([0-9:.]{12})[0-9]*\+09:00" level=info msg=/\1 /' | cut -c1-170
echo; echo "## 4. 자원 할당·격리: 노드의 cgroup 파일"
CID=$($K get pod cri-demo -o jsonpath='{.status.containerStatuses[0].containerID}'); CID=${CID#containerd://}
./lab ssh 1 -- sudo CID=$CID bash -s <<'R'
PID=$(crictl inspect -o go-template --template '{{.info.pid}}' $CID)
CG=$(cut -d: -f3 /proc/$PID/cgroup)
echo "컨테이너 pid=$PID"
echo "cgroup 경로: $CG"
echo "cpu.max    = $(cat /sys/fs/cgroup$CG/cpu.max)     (100ms 마다 20ms = 0.2 CPU)"
echo "memory.max = $(cat /sys/fs/cgroup$CG/memory.max)  (64Mi = 67108864)"
echo "컨테이너 안에서 본 프로세스: $(nsenter -t $PID -p -m ps -o pid,comm 2>/dev/null | tr -s ' ' | paste -sd'|' -)"
echo "컨테이너 hostname(uts) = $(nsenter -t $PID -u hostname), 노드 hostname = $(hostname)"
R
echo; echo "## 5. 메모리 한도를 넘기면 커널이 죽인다 (OOMKilled)"
$K exec cri-demo -- sh -c 'head -c 100m /dev/zero | tail' 2>&1 | tail -1
sleep 3
echo "$(ts) restarts=$($K get pod cri-demo -o jsonpath='{.status.containerStatuses[0].restartCount}') lastState=$($K get pod cri-demo -o jsonpath='{.status.containerStatuses[0].lastState.terminated.reason} exitCode={.status.containerStatuses[0].lastState.terminated.exitCode}')"
echo "worker1 dmesg: $(./lab ssh 1 -- sudo dmesg | grep -iE 'oom-kill|Memory cgroup out of memory' | tail -1 | cut -c1-160)"
echo; echo "## 6. 삭제할 때의 CRI 호출"
S2=$(date '+%F %T'); echo "$(ts) kubectl delete pod cri-demo (terminationGracePeriodSeconds 5)"; $K delete pod cri-demo >/dev/null; echo "$(ts) 삭제 끝"; sleep 2
./lab ssh 1 -- sudo journalctl -u containerd --since "$S2" --no-pager -o cat | grep -E 'StopContainer|StopPodSandbox|TearDown|RemoveContainer|RemovePodSandbox' | grep -v 'returns successfully' | sed -E 's/^time="[0-9-]+T([0-9:.]{12})[0-9]*\+09:00" level=info msg=/\1 /' | cut -c1-150
echo "이미지는 남아 있음: $(./lab ssh 1 -- sudo crictl images | grep busybox | awk '{print $1":"$2, $NF}')"
