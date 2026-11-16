#!/usr/bin/env bash
# PID 1 모양이 다른 파드 9개를 한꺼번에 지우고, 각각 몇 초 만에 사라지는지·종료 코드·노드 containerd가 보낸 신호를 본다 (Mac 에서 실행)
# 네임스페이스 why-pid1만 쓴다. 이미지: busybox:1.37, nginx:1.27-alpine, alpine:3.20(tini-static 받기용 init 컨테이너)
cd "$(dirname "$0")/../../.."   # 실습 저장소 루트
K="./lab kubectl"; NS=why-pid1
now(){ perl -MTime::HiRes=time -e 'printf "%.3f", time'; }
$K get ns $NS >/dev/null 2>&1 || $K create ns $NS >/dev/null

pod(){ # 이름, grace, shareProcessNamespace, 이미지, command(JSON), [tini]
  local name=$1 grace=$2 share=$3 image=$4 cmd=$5 tini=$6
  echo "---"
  echo "apiVersion: v1"
  echo "kind: Pod"
  echo "metadata: {name: $name, labels: {exp: del}}"
  echo "spec:"
  echo "  terminationGracePeriodSeconds: $grace"
  echo "  shareProcessNamespace: $share"
  if [ -n "$tini" ]; then
    echo "  initContainers:"
    echo "  - {name: get-tini, image: \"alpine:3.20\", command: [sh, -c, \"apk add --no-cache tini-static >/dev/null && cp /sbin/tini-static /shared/tini\"], volumeMounts: [{name: shared, mountPath: /shared}]}"
    echo "  volumes: [{name: shared, emptyDir: {}}]"
    echo "  containers:"
    echo "  - {name: c, image: \"$image\", command: $cmd, volumeMounts: [{name: shared, mountPath: /shared}]}"
  else
    echo "  containers:"
    echo "  - {name: c, image: \"$image\", command: $cmd}"
  fi
}
PODS="a-sleep b-sh-c c-sh-c-2cmds d-trap-fg e-trap-wait f-nginx g-share h-tini i-sleep-grace5"
{
pod a-sleep        30 false busybox:1.37 '["sleep","infinity"]'
pod b-sh-c         30 false busybox:1.37 '["sh","-c","sleep infinity"]'
pod c-sh-c-2cmds   30 false busybox:1.37 '["sh","-c","sleep infinity; echo bye"]'
pod d-trap-fg      30 false busybox:1.37 '["sh","-c","trap \"exit 0\" TERM; sleep infinity; echo bye"]'
pod e-trap-wait    30 false busybox:1.37 '["sh","-c","trap \"exit 0\" TERM; sleep infinity & wait"]'
pod f-nginx        30 false nginx:1.27-alpine '["/docker-entrypoint.sh","nginx","-g","daemon off;"]'
pod g-share        30 true  busybox:1.37 '["sleep","infinity"]'
pod h-tini         30 false busybox:1.37 '["/shared/tini","--","sleep","infinity"]' tini
pod i-sleep-grace5  5 false busybox:1.37 '["sleep","infinity"]'
} | $K -n $NS apply -f - >/dev/null
$K -n $NS wait --for=condition=Ready pod -l exp=del --timeout=180s >/dev/null
sleep 2

echo "# PID 1 모양별 파드 삭제 시간 ($(date '+%F %T %Z'))"
W=$(mktemp -d); trap 'rm -rf $W' EXIT   # 파드별 상태를 파일로 (macOS bash 3.2에 연관 배열이 없어서)
for p in $PODS; do
  $K -n $NS get pod $p -o jsonpath='{.spec.nodeName}{"\n"}' > $W/$p.node
  $K -n $NS get pod $p -o jsonpath='{.status.containerStatuses[0].containerID}' | sed 's#containerd://##' > $W/$p.cid
done
OFFS=""
for n in $(cat $W/*.node | sort -u); do
  a=$(now); v=$(limactl shell $n -- date +%s.%N); b=$(now); perl -e "printf '%.3f', $v - ($a+$b)/2" > $W/$n.off
  OFFS="$OFFS $n=$(cat $W/$n.off)s"
done
echo "# 노드 시계 - Mac 시계:$OFFS"

# watch 스트림으로 이벤트마다 (Mac 시각, 종류, 이름, 종료 코드, 이유)를 받는다
( $K -n $NS get pods -l exp=del -w --output-watch-events -o jsonpath='{.type} {.object.metadata.name} {.object.status.containerStatuses[0].state.terminated.exitCode} {.object.status.containerStatuses[0].state.terminated.reason}{"\n"}' 2>/dev/null \
  | while IFS= read -r l; do echo "$(now) $l"; done > $W/watch ) &
WP=$!
sleep 1
T0=$(now)
$K -n $NS delete pod -l exp=del --wait=false >/dev/null
echo "# +0.0s 9개 한꺼번에 delete 요청 (grace는 각 파드 spec 값)"
until [ -z "$($K -n $NS get pods -l exp=del -o name 2>/dev/null)" ]; do sleep 1; perl -e "exit !($(now)-$T0 > 70)" && break; done
sleep 1; pkill -P $WP 2>/dev/null; kill $WP 2>/dev/null; wait $WP 2>/dev/null
for p in $PODS; do
  awk -v p=$p -v t0=$T0 '$3==p && $2=="DELETED" && !g {printf "%.1f\n", $1-t0; g=1}' $W/watch > $W/$p.gone
  awk -v p=$p -v t0=$T0 '$3==p && $4!="" && !g {printf "%.1f exit=%s reason=%s\n", $1-t0, $4, $5; g=1}' $W/watch > $W/$p.term
done

echo; echo "파드 / 사라짐 / 컨테이너 종료(watch 첫 등장) / 노드 / containerd 로그(삭제 요청 기준)"
for p in $PODS; do
  n=$(cat $W/$p.node); o=$(cat $W/$n.off); id=$(cat $W/$p.cid)
  logs=$(limactl shell $n -- sudo journalctl -u containerd --since "$(date -r $(( ${T0%.*} - 3 )) '+%F %T')" --no-pager -o short-unix 2>/dev/null | grep "$id" \
    | grep -E 'Stop container|Kill container' | while read -r ts rest; do
      w=$(echo "$rest" | grep -oE 'with signal [a-z ]+|Kill container' | head -1 | sed 's/with signal /신호 /; s/Kill container/SIGKILL/')
      perl -e "printf '+%.1fs %s / ', $ts - $o - $T0, '$w'"
    done)
  printf "%-15s %-8s %-30s %-12s %s\n" "$p" "+$(cat $W/$p.gone 2>/dev/null || echo '?')s" "+$(cat $W/$p.term 2>/dev/null || echo '?')" "$n" "${logs% / }"
done
echo
echo "# 메모: 종료 코드 137 = 128+9(SIGKILL), 143 = 128+15(SIGTERM 기본 동작으로 죽음), 0 = 스스로 exit 0"
echo "# 메모: 사라짐 = watch에 DELETED 이벤트가 온 시각, 종료 = watch에 terminated 상태가 처음 실린 시각 (둘 다 Mac 시계, 삭제 요청 기준)"
