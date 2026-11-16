#!/usr/bin/env bash
# 핸들러 없는 PID 1(sleep infinity)에 SIGTERM·SIGKILL을 컨테이너 안(같은 PID 네임스페이스)과 노드(조상 네임스페이스)에서 각각 보내 본다 (Mac 에서 실행)
# 네임스페이스 why-pid1만 쓴다. 이미지: busybox:1.37. 노드에서는 그 컨테이너의 PID 1 하나에만 kill을 보낸다.
cd "$(dirname "$0")/../../.."   # 실습 저장소 루트
K="./lab kubectl"; NS=why-pid1
$K get ns $NS >/dev/null 2>&1 || $K create ns $NS >/dev/null
cat <<'Y' | $K -n $NS apply -f - >/dev/null
apiVersion: v1
kind: Pod
metadata: {name: k-sleep, labels: {exp: kill}}
spec:
  restartPolicy: Never
  terminationGracePeriodSeconds: 0
  containers: [{name: c, image: "busybox:1.37", command: [sleep, infinity]}]
Y
$K -n $NS wait --for=condition=Ready pod/k-sleep --timeout=120s >/dev/null
N=$($K -n $NS get pod k-sleep -o jsonpath='{.spec.nodeName}')
CID=$($K -n $NS get pod k-sleep -o jsonpath='{.status.containerStatuses[0].containerID}' | sed 's#containerd://##')
HP=$(limactl shell $N -- sudo crictl inspect $CID | python3 -c 'import json,sys; print(json.load(sys.stdin)["info"]["pid"])')
state(){ $K -n $NS get pod k-sleep -o jsonpath='{.status.phase} running={.status.containerStatuses[0].state.running.startedAt} terminated={.status.containerStatuses[0].state.terminated.exitCode}/{.status.containerStatuses[0].state.terminated.reason}'; }
alive(){ limactl shell $N -- sh -c "test -d /proc/$HP && echo '호스트 PID $HP 살아 있음 ('\$(cat /proc/$HP/comm)')' || echo '호스트 PID $HP 없음'"; }
echo "# PID 1에게 보낸 신호: 같은 네임스페이스 vs 조상 네임스페이스 ($(date '+%F %T %Z'))"
echo "# 파드 k-sleep, 노드 $N, 컨테이너 PID 1(sleep infinity) = 호스트 PID $HP, SigCgt=$($K -n $NS exec k-sleep -- awk '/SigCgt/{print $2}' /proc/1/status)"
echo; echo "## 1. 컨테이너 안에서: kill -TERM 1"
$K -n $NS exec k-sleep -- sh -c 'kill -TERM 1; echo "  kill 종료코드 $?"'; sleep 1; echo "  $(alive) / $(state)"
echo; echo "## 2. 컨테이너 안에서: kill -KILL 1"
$K -n $NS exec k-sleep -- sh -c 'kill -KILL 1; echo "  kill 종료코드 $?"'; sleep 1; echo "  $(alive) / $(state)"
echo; echo "## 3. 노드(호스트 PID 네임스페이스 = 조상)에서: kill -TERM $HP"
limactl shell $N -- sudo sh -c "kill -TERM $HP; echo \"  kill 종료코드 \$?\""; sleep 1; echo "  $(alive) / $(state)"
echo; echo "## 4. 노드에서: kill -KILL $HP"
limactl shell $N -- sudo sh -c "kill -KILL $HP; echo \"  kill 종료코드 \$?\""; sleep 2; echo "  $(alive) / $(state)"
$K -n $NS delete pod k-sleep --grace-period=0 --force >/dev/null 2>&1
echo; echo "# 파드 정리 완료"
