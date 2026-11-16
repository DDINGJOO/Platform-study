#!/usr/bin/env bash
# terminationGracePeriodSeconds는 어디서부터 세나: preStop이 있을 때 정지 신호·SIGKILL이 언제 가는지 (Mac 에서 실행)
# 네임스페이스 why-pid1만 쓴다. 이미지: busybox:1.37. preStop은 sleep 액션(컨테이너 안 바이너리 불필요)과 exec "sleep 45"
cd "$(dirname "$0")/../../.."   # 실습 저장소 루트
K="./lab kubectl"; NS=why-pid1
now(){ perl -MTime::HiRes=time -e 'printf "%.3f", time'; }
$K get ns $NS >/dev/null 2>&1 || $K create ns $NS >/dev/null
pod(){ # 이름, preStop 핸들러(YAML flow), command(JSON)
cat <<Y
---
apiVersion: v1
kind: Pod
metadata: {name: $1, labels: {exp: prestop}}
spec:
  terminationGracePeriodSeconds: 30
  containers:
  - name: c
    image: busybox:1.37
    command: $3
    lifecycle: {preStop: $2}
Y
}
PODS="p10-sleep p45-exec p10-trap"
echo "# preStop과 grace period ($(date '+%F %T %Z'))"
echo "# 먼저: preStop sleep 액션을 grace보다 길게(45s) 주면 API 서버가 받아 주나 (server-side dry-run)"
pod p45-sleep '{sleep: {seconds: 45}}' '["sleep","infinity"]' | $K -n $NS create --dry-run=server -f - 2>&1 | sed 's/^/#   /'
{
pod p10-sleep '{sleep: {seconds: 10}}' '["sleep","infinity"]'
pod p45-exec  '{exec: {command: [sleep, "45"]}}' '["sleep","infinity"]'
pod p10-trap  '{sleep: {seconds: 10}}' '["sh","-c","trap \"exit 0\" TERM; sleep infinity & wait"]'
} | $K -n $NS apply -f - >/dev/null
$K -n $NS wait --for=condition=Ready pod -l exp=prestop --timeout=120s >/dev/null
sleep 2
echo "# 세 파드 모두 terminationGracePeriodSeconds: 30"
echo "#   p10-sleep: preStop sleep 10s, PID 1 = sleep infinity(SIGTERM 무시)"
echo "#   p45-exec : preStop exec \"sleep 45\"(grace보다 김, exec는 위 검증을 안 받는다), PID 1 = sleep infinity"
echo "#   p10-trap : preStop sleep 10s, PID 1 = sh(trap TERM + wait, SIGTERM에 바로 exit 0)"
W=$(mktemp -d); trap 'rm -rf $W' EXIT
for p in $PODS; do
  $K -n $NS get pod $p -o jsonpath='{.spec.nodeName}{"\n"}' > $W/$p.node
  $K -n $NS get pod $p -o jsonpath='{.status.containerStatuses[0].containerID}' | sed 's#containerd://##' > $W/$p.cid
done
for n in $(sort -u $W/*.node); do a=$(now); v=$(limactl shell $n -- date +%s.%N); b=$(now); perl -e "printf '%.3f', $v - ($a+$b)/2" > $W/$n.off; done
T0=$(now)
$K -n $NS delete pod -l exp=prestop --wait=false >/dev/null
echo "# +0.0s delete 요청"
sleep 1
echo "# deletionTimestamp(API 서버가 정한 '이때까지') - 요청 시각:"
for p in $PODS; do
  dt=$($K -n $NS get pod $p -o jsonpath='{.metadata.deletionTimestamp} {.metadata.deletionGracePeriodSeconds}' 2>/dev/null)
  [ -n "$dt" ] && perl -MTime::Local -e 'my ($d,$g)=split / /, $ARGV[0]; $d=~/(\d+)-(\d+)-(\d+)T(\d+):(\d+):(\d+)Z/; my $e=timegm($6,$5,$4,$3,$2-1,$1); printf "#   %-10s deletionTimestamp=%s (요청 +%.0fs), deletionGracePeriodSeconds=%s\n", $ARGV[1], $d, $e-$ARGV[2], $g' "$dt" $p $T0
done
until [ -z "$($K -n $NS get pods -l exp=prestop -o name 2>/dev/null)" ]; do sleep 0.5; perl -e "exit !($(now)-$T0 > 70)" && break; done
echo "# +$(perl -e "printf '%.1f', $(now)-$T0")s 세 파드 모두 사라짐"
for p in $PODS; do
  n=$(cat $W/$p.node); o=$(cat $W/$n.off); id=$(cat $W/$p.cid)
  echo; echo "## $p (노드 $n, 노드-Mac=${o}s)"
  limactl shell $n -- sudo journalctl -u containerd -u kubelet --since "$(date -r $(( ${T0%.*} - 3 )) '+%F %T')" --no-pager -o short-unix 2>/dev/null \
    | grep -E "$id|$p" | grep -E 'StopContainer for .* with timeout|Stop container .* with signal|Kill container|StopContainer for .* returns|Pod removed broadcasted|PreStop' \
    | while read -r ts rest; do
      perl -e "printf \"  node +%5.1fs  \", $ts - $o - $T0"
      echo "$rest" | sed -E 's/^[^:]*: //; s/.*msg="//; s/" *$//; s/[0-9a-f]{64}/<cid>/g; s/\\"/"/g' | cut -c1-190
    done
done
