#!/usr/bin/env bash
# 26편 보강 (조회만 한다, Mac 에서 실행)
#  1) 26-pstree 의 buildkitd, containerd-star 는 무엇인가
#  2) systemd cgroup 드라이버: 컨테이너마다 systemd scope 단위가 생기는가 (마스터)
#  3) 26-restart-runtime 끝의 loadgen RESTARTS 1 은 언제 생긴 것인가
cd "${LAB:?실습 저장소(./lab 이 있는 곳) 경로를 LAB 에 넣는다}"
K="./lab kubectl"
echo "# 26편 보강 ($(date '+%F %T %Z'))"
echo; echo "## 1·2. 마스터의 systemd 서비스와 컨테이너 scope"
./lab ssh master -- sudo bash -s <<'R'
for p in buildkitd containerd-star; do pid=$(pgrep -o "$p"); echo "$p: pid=$pid 실행 파일=$(tr '\0' ' ' < /proc/$pid/cmdline | awk '{print $1}') systemd 단위=$(ps -o unit= -p $pid)"; done
echo "cri-containerd-*.scope 단위 수: $(systemctl list-units --all --no-legend 'cri-containerd-*.scope' | wc -l)"
echo "containerd-shim-runc-v2 수: $(pgrep -c -f containerd-shim-runc-v2)"
echo "예: etcd 컨테이너의 cgroup = $(cut -d: -f3 /proc/$(pgrep -xo etcd)/cgroup)"
R
echo; echo "## 3. loadgen 의 마지막 종료 기록 (UTC)"
echo "loadgen 노드: $($K get pod loadgen -o jsonpath='{.spec.nodeName}'), 그 노드의 부팅 시각(KST): $(./lab ssh 1 -- uptime -s)"
$K get pod loadgen -o jsonpath='restartCount={.status.containerStatuses[0].restartCount} lastState.terminated: reason={.status.containerStatuses[0].lastState.terminated.reason} finishedAt={.status.containerStatuses[0].lastState.terminated.finishedAt} / 지금 state.running.startedAt={.status.containerStatuses[0].state.running.startedAt}{"\n"}'
echo; echo "## 4. 26-oci 의 process.args 는 어디서 왔나 (Deployment 의 command·args 와 이미지 설정)"
echo "myweb Deployment: command=[$($K get deploy myweb -o jsonpath='{.spec.template.spec.containers[0].command}')] args=[$($K get deploy myweb -o jsonpath='{.spec.template.spec.containers[0].args}')]"
./lab ssh 1 -- sudo sh -c 'crictl inspecti -o json docker.io/library/nginx:1.25.1-alpine' | python3 -c 'import json,sys;c=json.load(sys.stdin)["info"]["imageSpec"]["config"];print("nginx:1.25.1-alpine 이미지 설정: Entrypoint =",c.get("Entrypoint"),"/ Cmd =",c.get("Cmd"))'
echo; echo "## 5. 마스터 부팅 시각과 컨테이너 프로세스 시작 시각 (26-pstree 의 PID 크기 차이)"
./lab ssh master -- sh -c 'echo "부팅: $(uptime -s)"; ps -o pid,lstart,comm -p $(pgrep -xo etcd),$(pgrep -xo kube-proxy),$(pgrep -xo kube-apiserver),$(pgrep -xo kube-scheduler),$(pgrep -f -o kube-controller-manager)'
