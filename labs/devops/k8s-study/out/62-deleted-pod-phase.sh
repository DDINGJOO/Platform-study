#!/usr/bin/env bash
# 지우는 중인 파드가 깨끗하게(exit 0) 끝나면 phase 는? restartPolicy Always vs Never (Mac 에서 실행)
cd "$(dirname "$0")/../.."
K="./lab kubectl"; NS=ch05
echo "# 20 지우는 중 exit 0 으로 끝난 파드의 phase ($(date '+%F %T %Z'))"
for rp in Always Never; do
  P=del-$(echo $rp | tr A-Z a-z)
  $K run $P -n $NS --image=busybox:1.37 --restart=$rp --command -- sh -c 'trap "exit 0" TERM; while true; do sleep 1; done' >/dev/null
  $K wait pod/$P -n $NS --for=condition=Ready --timeout=60s >/dev/null
  echo; echo "## restartPolicy: $rp — delete 후 객체가 사라지기 전 마지막 상태"
  $K get pod $P -n $NS -w -o jsonpath='{.status.phase} {.status.containerStatuses[0].state.terminated.exitCode} {.status.containerStatuses[0].state.terminated.reason} del={.metadata.deletionTimestamp}{"\n"}' > /tmp/ch05-20-$P.log 2>&1 &
  W=$!; sleep 1
  $K delete pod $P -n $NS --wait=true >/dev/null
  sleep 1; kill $W 2>/dev/null; wait $W 2>/dev/null
  awk '!seen[$0]++' /tmp/ch05-20-$P.log | sed 's/^/  phase exitCode reason: /'; rm -f /tmp/ch05-20-$P.log
done
