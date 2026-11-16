#!/usr/bin/env bash
# 컨테이너마다 PID 1이 누구이고, 그 PID 1이 어떤 신호에 핸들러를 걸었나(/proc/1/status SigCgt·SigIgn) (Mac 에서 실행)
# 네임스페이스 why-pid1만 쓴다. 파드는 이 스크립트 끝에서 지운다(네임스페이스는 남김).
# 이미지: busybox:1.37, nginx:1.27-alpine, alpine:3.20(tini-static를 apk로 받아 emptyDir로 넘기는 init 컨테이너)
cd "$(dirname "$0")/../../.."   # 실습 저장소 루트
K="./lab kubectl"; NS=why-pid1
$K get ns $NS >/dev/null 2>&1 || $K create ns $NS >/dev/null

pod(){ # 이름, shareProcessNamespace, 이미지, command(JSON), [tini 여부]
  local name=$1 share=$2 image=$3 cmd=$4 tini=$5
  if [ -n "$tini" ]; then
cat <<Y
---
apiVersion: v1
kind: Pod
metadata: {name: $name, labels: {exp: pid1}}
spec:
  terminationGracePeriodSeconds: 30
  shareProcessNamespace: $share
  initContainers:
  - {name: get-tini, image: "alpine:3.20", command: [sh, -c, "apk add --no-cache tini-static >/dev/null && cp /sbin/tini-static /shared/tini"], volumeMounts: [{name: shared, mountPath: /shared}]}
  containers:
  - {name: c, image: "$image", command: $cmd, volumeMounts: [{name: shared, mountPath: /shared}]}
  volumes: [{name: shared, emptyDir: {}}]
Y
  else
cat <<Y
---
apiVersion: v1
kind: Pod
metadata: {name: $name, labels: {exp: pid1}}
spec:
  terminationGracePeriodSeconds: 30
  shareProcessNamespace: $share
  containers:
  - {name: c, image: "$image", command: $cmd}
Y
  fi
}

{
pod a-sleep        false busybox:1.37 '["sleep","infinity"]'
pod b-sh-c         false busybox:1.37 '["sh","-c","sleep infinity"]'
pod c-sh-c-2cmds   false busybox:1.37 '["sh","-c","sleep infinity; echo bye"]'
pod d-trap-fg      false busybox:1.37 '["sh","-c","trap \"exit 0\" TERM; sleep infinity; echo bye"]'
pod e-trap-wait    false busybox:1.37 '["sh","-c","trap \"exit 0\" TERM; sleep infinity & wait"]'
pod f-nginx        false nginx:1.27-alpine '["/docker-entrypoint.sh","nginx","-g","daemon off;"]'
pod g-share        true  busybox:1.37 '["sleep","infinity"]'
pod h-tini         false busybox:1.37 '["/shared/tini","--","sleep","infinity"]' tini
} | $K -n $NS apply -f - >/dev/null
$K -n $NS wait --for=condition=Ready pod -l exp=pid1 --timeout=180s >/dev/null

decode(){ python3 -c '
import sys
names="HUP INT QUIT ILL TRAP ABRT BUS FPE KILL USR1 SEGV USR2 PIPE ALRM TERM STKFLT CHLD CONT STOP TSTP TTIN TTOU URG XCPU XFSZ VTALRM PROF WINCH IO PWR SYS".split()
v=int(sys.argv[1],16); out=[]
for i in range(64):
    if v>>i & 1:
        n=i+1; out.append(names[n-1] if n<=31 else "RT%d"%n)
print(" ".join(out) if out else "없음")' "$1"; }

echo "# PID 1과 신호 마스크 ($(date '+%F %T %Z'))"
echo "# 노드 커널 $(limactl shell k8s-worker1 -- uname -r 2>/dev/null), 컨테이너 런타임 $($K get node k8s-worker1 -o jsonpath='{.status.nodeInfo.containerRuntimeVersion}')"
for p in a-sleep b-sh-c c-sh-c-2cmds d-trap-fg e-trap-wait f-nginx g-share h-tini; do
  echo; echo "## $p  command: $($K -n $NS get pod $p -o jsonpath='{.spec.containers[0].command}')  shareProcessNamespace=$($K -n $NS get pod $p -o jsonpath='{.spec.shareProcessNamespace}')"
  echo "  ps (컨테이너 안):"
  $K -n $NS exec $p -c c -- ps -o pid,ppid,stat,args 2>/dev/null | grep -v ' ps -o ' | sed 's/^/    /'
  # PID 1과, PID 1이 아닌 sleep/nginx가 있으면 그것도
  for pid in $($K -n $NS exec $p -c c -- sh -c 'echo 1; for d in /proc/[0-9]*; do n=${d#/proc/}; [ "$n" = 1 ] && continue; c=$(cat $d/comm 2>/dev/null); case $c in sleep|nginx) echo $n; break;; esac; done' 2>/dev/null); do
    st=$($K -n $NS exec $p -c c -- cat /proc/$pid/status 2>/dev/null)
    comm=$(echo "$st" | awk '/^Name:/{print $2}')
    first=1
    for k in SigBlk SigIgn SigCgt; do   # Blk=막아 둔(대기열에 쌓이는) 신호, Ign=무시, Cgt=핸들러를 건 신호
      v=$(echo "$st" | awk -v k="$k:" '$1==k{print $2}')
      if [ $first = 1 ]; then printf "  PID %-3s %-6s %s=%s (%s)\n" "$pid" "$comm" "$k" "$v" "$(decode $v)"; first=0
      else printf "  %-10s %-6s %s=%s (%s)\n" "" "" "$k" "$v" "$(decode $v)"; fi
    done
  done
done

echo; echo "## 이미지 설정의 STOPSIGNAL (노드 containerd가 본 값)"
for img in docker.io/library/busybox:1.37 docker.io/library/nginx:1.27-alpine; do
  N=$($K -n $NS get pod f-nginx -o jsonpath='{.spec.nodeName}')
  s=$(limactl shell $N -- sudo crictl inspecti $img 2>/dev/null | python3 -c 'import json,sys; c=json.load(sys.stdin)["info"]["imageSpec"]["config"]; print("StopSignal=%s Entrypoint=%s Cmd=%s" % (c.get("StopSignal","(없음)"), c.get("Entrypoint"), c.get("Cmd")))')
  echo "  $img: $s"
done

$K -n $NS delete pod -l exp=pid1 --grace-period=0 --force >/dev/null 2>&1
echo; echo "# 파드 정리 완료"
