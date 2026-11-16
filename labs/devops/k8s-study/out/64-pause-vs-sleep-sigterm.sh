#!/usr/bin/env bash
# 같은 파드의 pause(SIGTERM 핸들러 있음)와 앱 PID 1 sleep(핸들러 없음)에 노드에서 똑같이 kill -TERM 을 보내면 어떻게 되나 (Mac 에서 실행)
# 실습 저장소 루트에서 실행한다. 네임스페이스 blog-64 만 쓰고 끝나면 지운다. 이미지: busybox:1.37
# 기본 파드(shareProcessNamespace 없음)라서 pause 와 sleep 은 각자 자기 PID 네임스페이스의 PID 1 이다.
K="./lab kubectl"; NS=blog-64; P=ps-sleep
now(){ perl -MTime::HiRes=time -e 'printf "%.3f", time'; }
$K get ns $NS >/dev/null 2>&1 || $K create ns $NS >/dev/null
cat <<'Y' | $K -n $NS apply -f - >/dev/null
apiVersion: v1
kind: Pod
metadata: {name: ps-sleep}
spec:
  terminationGracePeriodSeconds: 30
  containers: [{name: c, image: "busybox:1.37", command: [sleep, infinity]}]
Y
$K -n $NS wait --for=condition=Ready pod/$P --timeout=120s >/dev/null
N=$($K -n $NS get pod $P -o jsonpath='{.spec.nodeName}')
CID=$($K -n $NS get pod $P -o jsonpath='{.status.containerStatuses[0].containerID}' | sed 's#containerd://##')
SB=$(limactl shell $N -- sudo crictl pods --name $P --namespace $NS -q | head -1)
PP=$(limactl shell $N -- sudo crictl inspectp $SB | python3 -c 'import json,sys; print(json.load(sys.stdin)["info"]["pid"])')
AP=$(limactl shell $N -- sudo crictl inspect $CID | python3 -c 'import json,sys; print(json.load(sys.stdin)["info"]["pid"])')
info(){ # 호스트 PID → "comm NSpid=호스트/안 SigCgt=값 (해석)" 또는 "없음"
  limactl shell $N -- sh -c "cat /proc/$1/comm /proc/$1/status 2>/dev/null" | python3 -c '
import sys
L=sys.stdin.read().splitlines()
if not L: print("없음"); sys.exit()
d={}
for l in L[1:]:
    k,_,v=l.partition(":"); d[k]=v.split()
names="HUP INT QUIT ILL TRAP ABRT BUS FPE KILL USR1 SEGV USR2 PIPE ALRM TERM STKFLT CHLD CONT STOP TSTP TTIN TTOU URG XCPU XFSZ VTALRM PROF WINCH IO PWR SYS".split()
c=d["SigCgt"][0]; v=int(c,16); h=[names[i] for i in range(31) if v>>i & 1]
print("%s NSpid=%s SigCgt=%s (%s)" % (L[0], "/".join(d["NSpid"]), c, " ".join(h) if h else "없음"))'
}
show(){ info $1; }
a=$(now); v=$(limactl shell $N -- date +%s.%N); b=$(now); OFF=$(perl -e "printf '%.3f', $v - ($a+$b)/2")
echo "# pause vs 앱 PID 1: 노드에서 보낸 SIGTERM ($(date '+%F %T %Z'))"
echo "# 파드 $P, 노드 $N (노드 시계 - Mac = ${OFF}s)"
echo "  pause 호스트 PID $PP: $(show $PP)"
echo "  sleep 호스트 PID $AP: $(show $AP)"
echo "  (NSpid 는 '호스트 PID/자기 네임스페이스 안의 PID'. 둘 다 끝이 1 이면 각자 자기 PID 네임스페이스의 PID 1)"

echo; echo "## 1. 노드에서 kill -TERM $AP (앱 sleep)"
limactl shell $N -- sudo sh -c "kill -TERM $AP; echo \"  kill 종료코드 \$?\""
sleep 1; echo "  1초 뒤 sleep: $(show $AP)"

echo; echo "## 2. 노드에서 kill -TERM $PP (pause)"
T0=$(now)
limactl shell $N -- sudo sh -c "kill -TERM $PP; echo \"  kill 종료코드 \$?\""
for i in $(seq 1 20); do
  [ "$(info $PP)" = 없음 ] && { perl -e "printf \"  +%.1fs pause 호스트 PID $PP 없음\n\", $(now)-$T0"; break; }
  sleep 0.2
done
echo "  sleep: $(show $AP)"

echo; echo "## 3. 그 뒤 60초 동안 이 파드의 샌드박스와 컨테이너 (kill -TERM pause 기준)"
for t in 5 15 30 45 60; do
  while perl -e "exit !($(now)-$T0 < $t)"; do sleep 0.5; done
  printf "  +%2ss  %s / restartCount=%s / 앱 sleep 호스트 PID $AP: %s\n" $t \
    "$(limactl shell $N -- sudo crictl pods --name $P --namespace $NS -o json | python3 -c 'import json,sys; print(" ".join("%s:%s" % (p["id"][:12], p["state"]) for p in json.load(sys.stdin)["items"]))')" \
    "$($K -n $NS get pod $P -o jsonpath='{.status.containerStatuses[0].restartCount}')" \
    "$(info $AP | cut -d' ' -f1)"
done
echo "  이벤트:"
$K -n $NS get events --field-selector involvedObject.name=$P --sort-by=.lastTimestamp -o custom-columns='REASON:.reason,COUNT:.count,MESSAGE:.message' --no-headers | sed 's/^/    /'
echo "  containerd 로그(앱 컨테이너, kill -TERM pause 기준, 노드 시계 보정):"
limactl shell $N -- sudo journalctl -u containerd --since "$(date -r $(( ${T0%.*} - 2 )) '+%F %T')" --no-pager -o short-unix 2>/dev/null | grep "$CID" \
  | grep -E 'Stop container|Kill container' | while read -r ts rest; do
    perl -e "printf '    +%5.1fs  ', $ts - $OFF - $T0"; echo "$rest" | sed -E 's/.*msg="//; s/"$//; s/[0-9a-f]{64}/<cid>/g; s/\\"/"/g'
  done
$K delete ns $NS --wait=true >/dev/null 2>&1
echo; echo "# 네임스페이스 $NS 삭제"
