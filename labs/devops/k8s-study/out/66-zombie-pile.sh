#!/usr/bin/env bash
# kubectl exec로 백그라운드 자식을 남기고 빠지기를 20번 하면, PID 1이 누구냐에 따라 좀비가 쌓이나 (Mac 에서 실행)
# 네임스페이스 why-pid1만 쓴다. 이미지: busybox:1.37, alpine:3.20(tini-static 받기용 init 컨테이너)
# 비교: z-sleep(sleep이 PID 1) / z-tini(tini가 PID 1) / z-share(shareProcessNamespace, pause가 PID 1)
cd "$(dirname "$0")/../../.."   # 실습 저장소 루트
K="./lab kubectl"; NS=why-pid1; N=20
$K get ns $NS >/dev/null 2>&1 || $K create ns $NS >/dev/null
cat <<'Y' | $K -n $NS apply -f - >/dev/null
apiVersion: v1
kind: Pod
metadata: {name: z-sleep, labels: {exp: zombie}}
spec:
  terminationGracePeriodSeconds: 0
  containers: [{name: c, image: "busybox:1.37", command: [sleep, infinity]}]
---
apiVersion: v1
kind: Pod
metadata: {name: z-tini, labels: {exp: zombie}}
spec:
  terminationGracePeriodSeconds: 0
  initContainers:
  - {name: get-tini, image: "alpine:3.20", command: [sh, -c, "apk add --no-cache tini-static >/dev/null && cp /sbin/tini-static /shared/tini"], volumeMounts: [{name: shared, mountPath: /shared}]}
  containers: [{name: c, image: "busybox:1.37", command: [/shared/tini, --, sleep, infinity], volumeMounts: [{name: shared, mountPath: /shared}]}]
  volumes: [{name: shared, emptyDir: {}}]
---
apiVersion: v1
kind: Pod
metadata: {name: z-share, labels: {exp: zombie}}
spec:
  terminationGracePeriodSeconds: 0
  shareProcessNamespace: true
  containers: [{name: c, image: "busybox:1.37", command: [sleep, infinity]}]
Y
$K -n $NS wait --for=condition=Ready pod -l exp=zombie --timeout=180s >/dev/null

count(){ # 파드 → "좀비 수 / 컨테이너 cgroup pids.current"
  $K -n $NS exec $1 -c c -- sh -c 'z=0; for s in /proc/[0-9]*/stat; do set -- $(cat $s 2>/dev/null); [ "$3" = Z ] && z=$((z+1)); done; echo "좀비 $z개 / pids.current $(cat /sys/fs/cgroup/pids.current)"' 2>/dev/null
}
echo "# 좀비 쌓이기: kubectl exec로 sh -c 'sleep 1 &'를 ${N}번 ($(date '+%F %T %Z'))"
echo "# exec 된 sh는 바로 끝나고, 1초 뒤 끝나는 sleep은 부모(sh)를 잃은 고아가 된다 → 커널이 그 PID 네임스페이스의 PID 1에게 넘긴다"
echo
echo "## 시작 전"
for p in z-sleep z-tini z-share; do printf "  %-8s %s\n" $p "$(count $p)"; done
for p in z-sleep z-tini z-share; do
  for i in $(seq $N); do $K -n $NS exec $p -c c -- sh -c 'sleep 1 >/dev/null 2>&1 &' >/dev/null 2>&1; done
done
sleep 3
echo; echo "## ${N}번 뒤 (마지막 exec 후 3초)"
for p in z-sleep z-tini z-share; do printf "  %-8s %s\n" $p "$(count $p)"; done
echo; echo "## z-sleep의 ps (앞 6줄)"
$K -n $NS exec z-sleep -c c -- ps -o pid,ppid,stat,args 2>/dev/null | head -7 | sed 's/^/  /'
echo; echo "## 노드에서 본 z-sleep의 좀비 (호스트 PID, 부모 = 컨테이너의 sleep infinity)"
NODE=$($K -n $NS get pod z-sleep -o jsonpath='{.spec.nodeName}')
CID=$($K -n $NS get pod z-sleep -o jsonpath='{.status.containerStatuses[0].containerID}' | sed 's#containerd://##')
limactl shell $NODE -- sudo bash -c "
P=\$(crictl inspect $CID | jq -r .info.pid)
echo \"  $NODE: 컨테이너 PID 1의 호스트 PID = \$P (\$(cat /proc/\$P/comm)), 그 자식 중 Z 상태: \$(ps -o stat= --ppid \$P | grep -c Z)개\"
ps -o pid,ppid,stat,comm --ppid \$P | head -4 | sed 's/^/    /'
"
$K -n $NS delete pod -l exp=zombie --grace-period=0 --force >/dev/null 2>&1
echo; echo "# 파드 정리 완료"
