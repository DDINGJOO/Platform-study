#!/usr/bin/env bash
# PID 1 이 SIGTERM 을 처리하지 않는 파드(sleep infinity)를 지우면 몇 초 만에 사라지나 — 3회, watch 이벤트와 노드 로그로 교차 확인 (Mac 에서 실행)
cd "$(dirname "$0")/../.."
K="./lab kubectl"; NS=ch05; P=life-sleep
now(){ perl -MTime::HiRes=time -e 'printf "%.3f", time'; }
echo "# 04 sleep infinity 파드 삭제 시간 3회 ($(date '+%F %T %Z'))"
for run in 1 2 3; do
  $K delete pod $P -n $NS --ignore-not-found --wait >/dev/null
  $K run $P -n $NS --image=busybox:1.37 --restart=Never --command -- sleep infinity >/dev/null
  $K wait pod/$P -n $NS --for=condition=Ready --timeout=120s >/dev/null
  N=$($K get pod $P -n $NS -o jsonpath='{.spec.nodeName}')
  # 노드 시계 - Mac 시계
  a=$(now); v=$(limactl shell $N -- date +%s.%N); b=$(now); OFF=$(perl -e "printf '%.3f', $v - ($a+$b)/2")
  echo; echo "## ${run}회차 노드 $N (노드 시계 - Mac = ${OFF}s)"
  T0=$(now)
  ( $K get pod $P -n $NS -w --output-watch-events --no-headers 2>&1 | while IFS= read -r l; do perl -e "printf '    watch +%5.1fs  ', $(now)-$T0"; echo "$l"; done ) &
  WP=$!
  sleep 0.5; T0=$(now); $K delete pod $P -n $NS --wait=false >/dev/null
  echo "    +  0.0s delete 요청 보냄"
  while :; do
    s=$(now); $K get pod $P -n $NS >/dev/null 2>&1; rc=$?; e=$(now)
    perl -e "exit !($e-$s > 1)" && perl -e "printf \"    get 호출 하나가 %.1fs 걸림 (+%.1fs 에 시작)\n\", $e-$s, $s-$T0"
    [ $rc -ne 0 ] && break; sleep 0.3
  done
  perl -e "printf \"    +%5.1fs get 이 NotFound\n\", $e-$T0"
  sleep 1; pkill -P $WP 2>/dev/null; kill $WP 2>/dev/null; wait $WP 2>/dev/null
  since=$(date -r ${T0%.*} '+%H:%M:%S')
  limactl shell $N -- sudo journalctl -u containerd -u kubelet --since "$(date -r $(( ${T0%.*} - 5 )) '+%H:%M:%S')" --no-pager -o short-unix 2>/dev/null \
    | grep -E 'Kill container|StopContainer for .* returns|Pod removed broadcasted' | while read -r ts rest; do
      what=$(echo "$rest" | grep -oE 'Kill container|StopContainer for|Pod removed broadcasted' | head -1)
      perl -e "my \$d=$ts - $OFF - $T0; printf \"    node +%5.1fs  %s\n\", \$d, '$what' if \$d > 0"
    done | awk '!seen[$0]++' | head -6
done
$K delete pod $P -n $NS --ignore-not-found >/dev/null
