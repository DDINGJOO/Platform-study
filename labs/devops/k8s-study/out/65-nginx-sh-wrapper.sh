#!/usr/bin/env bash
# nginx 를 sh -c 로 감쌌을 때 exec 유무에 따라 PID 1·신호 마스크·삭제 시간이 어떻게 달라지나 (Mac 에서 실행)
# 실습 저장소 루트에서 실행한다. 네임스페이스 blog-65 만 쓰고 끝나면 지운다. 이미지: nginx:1.27-alpine (이미지 STOPSIGNAL=SIGQUIT, sh 는 busybox)
K="./lab kubectl"; NS=blog-65
now(){ perl -MTime::HiRes=time -e 'printf "%.3f", time'; }
$K get ns $NS >/dev/null 2>&1 || $K create ns $NS >/dev/null
pod(){ # 이름, command(JSON)
  echo "---"
  echo "apiVersion: v1"
  echo "kind: Pod"
  echo "metadata: {name: $1, labels: {exp: wrap}}"
  echo "spec:"
  echo "  terminationGracePeriodSeconds: 30"
  echo "  containers:"
  echo "  - {name: c, image: \"nginx:1.27-alpine\", command: $2}"
}
PODS="w-direct w-sh-exec w-sh-noexec w-sh-tail"
{
pod w-direct    '["nginx","-g","daemon off;"]'
pod w-sh-exec   '["sh","-c","echo prep; exec nginx -g \"daemon off;\""]'
pod w-sh-noexec '["sh","-c","echo prep; nginx -g \"daemon off;\""]'
pod w-sh-tail   '["sh","-c","nginx -g \"daemon off;\"; echo bye"]'
} | $K -n $NS apply -f - >/dev/null
$K -n $NS wait --for=condition=Ready pod -l exp=wrap --timeout=180s >/dev/null
sleep 2
echo "# nginx 를 감싼 모양별 PID 1 과 삭제 시간 ($(date '+%F %T %Z'))"

decode(){ python3 -c '
import sys
names="HUP INT QUIT ILL TRAP ABRT BUS FPE KILL USR1 SEGV USR2 PIPE ALRM TERM STKFLT CHLD CONT STOP TSTP TTIN TTOU URG XCPU XFSZ VTALRM PROF WINCH IO PWR SYS".split()
v=int(sys.argv[1],16); out=[names[i] for i in range(31) if v>>i & 1]
print(" ".join(out) if out else "없음")' "$1"; }

echo; echo "## 1. PID 1 은 누구이고 어떤 신호를 무시(SigIgn)하거나 잡나(SigCgt)"
for p in $PODS; do
  st=$($K -n $NS exec $p -c c -- cat /proc/1/status 2>/dev/null)
  ign=$(echo "$st" | awk '$1=="SigIgn:"{print $2}'); cgt=$(echo "$st" | awk '$1=="SigCgt:"{print $2}')
  echo "  $p  command: $($K -n $NS get pod $p -o jsonpath='{.spec.containers[0].command}')"
  echo "    PID 1 = $($K -n $NS exec $p -c c -- cat /proc/1/cmdline 2>/dev/null | tr '\0' ' ')"
  echo "    SigIgn=$ign ($(decode $ign))  SigCgt=$cgt ($(decode $cgt))"
done

W=$(mktemp -d); trap 'rm -rf $W' EXIT
for p in $PODS; do
  $K -n $NS get pod $p -o jsonpath='{.spec.nodeName}{"\n"}' > $W/$p.node
  $K -n $NS get pod $p -o jsonpath='{.status.containerStatuses[0].containerID}' | sed 's#containerd://##' > $W/$p.cid
done
OFFS=""
for n in $(cat $W/*.node | sort -u); do
  a=$(now); v=$(limactl shell $n -- date +%s.%N); b=$(now); perl -e "printf '%.3f', $v - ($a+$b)/2" > $W/$n.off
  OFFS="$OFFS $n=$(cat $W/$n.off)s"
done
echo; echo "## 2. 네 파드를 한꺼번에 지운다 (노드 시계 - Mac 시계:$OFFS)"
( $K -n $NS get pods -l exp=wrap -w --output-watch-events -o jsonpath='{.type} {.object.metadata.name} {.object.status.containerStatuses[0].state.terminated.exitCode} {.object.status.containerStatuses[0].state.terminated.reason}{"\n"}' 2>/dev/null \
  | while IFS= read -r l; do echo "$(now) $l"; done > $W/watch ) &
WP=$!
sleep 1
T0=$(now)
$K -n $NS delete pod -l exp=wrap --wait=false >/dev/null
until [ -z "$($K -n $NS get pods -l exp=wrap -o name 2>/dev/null)" ]; do sleep 1; perl -e "exit !($(now)-$T0 > 70)" && break; done
sleep 1; pkill -P $WP 2>/dev/null; kill $WP 2>/dev/null; wait $WP 2>/dev/null
echo "  파드 / 사라짐 / 컨테이너 종료(watch 첫 등장) / 노드 / containerd 로그(삭제 요청 기준)"
for p in $PODS; do
  gone=$(awk -v p=$p -v t0=$T0 '$3==p && $2=="DELETED" && !g {printf "%.1f", $1-t0; g=1}' $W/watch)
  term=$(awk -v p=$p -v t0=$T0 '$3==p && $4!="" && !g {printf "%.1f exit=%s reason=%s", $1-t0, $4, $5; g=1}' $W/watch)
  n=$(cat $W/$p.node); o=$(cat $W/$n.off); id=$(cat $W/$p.cid)
  logs=$(limactl shell $n -- sudo journalctl -u containerd --since "$(date -r $(( ${T0%.*} - 3 )) '+%F %T')" --no-pager -o short-unix 2>/dev/null | grep "$id" \
    | grep -E 'Stop container|Kill container' | while read -r ts rest; do
      w=$(echo "$rest" | grep -oE 'with signal [a-z ]+|Kill container' | head -1 | sed 's/with signal /신호 /; s/Kill container/SIGKILL/')
      perl -e "printf '+%.1fs %s / ', $ts - $o - $T0, '$w'"
    done)
  printf "  %-12s %-8s %-30s %-12s %s\n" "$p" "+${gone:-?}s" "+${term:-?}" "$n" "${logs% / }"
done
$K delete ns $NS --wait=true >/dev/null 2>&1
echo
echo "# 메모: 137 = 128+9(SIGKILL), 0 = 스스로 exit 0. containerd 의 '신호 quit' 은 이미지 STOPSIGNAL(SIGQUIT)을 보냈다는 뜻"
echo "# 네임스페이스 $NS 삭제"
