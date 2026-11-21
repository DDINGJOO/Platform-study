#!/usr/bin/env bash
# 파드 conditions 의 실제 type 이름: 정상 파드의 conditions, 스케줄할 수 없는 파드에서 Unschedulable 은 type 인가 reason 인가 (Mac 에서 실행)
cd "$(dirname "$0")/../.."
K="./lab kubectl"; NS=ch05
echo "# 30 Pod conditions ($(date '+%F %T %Z'))"
echo; echo "## explain pod.status.conditions.type"; $K explain pod.status.conditions.type | sed -n '/DESCRIPTION/,$p' | sed 's/^/  /'
$K run cond-ok -n $NS --image=busybox:1.37 --command -- sleep 3600 >/dev/null
$K run cond-nonode -n $NS --image=busybox:1.37 --overrides='{"spec":{"nodeSelector":{"lab/none":"true"}}}' --command -- sleep 3600 >/dev/null
$K wait pod/cond-ok -n $NS --for=condition=Ready --timeout=60s >/dev/null; sleep 3
for p in cond-ok cond-nonode; do
  echo; echo "## $p  phase=$($K get pod $p -n $NS -o jsonpath='{.status.phase}')"
  $K get pod $p -n $NS -o jsonpath='{range .status.conditions[*]}  type={.type} status={.status} reason={.reason} {.message}{"\n"}{end}'
done
$K delete pod cond-ok cond-nonode -n $NS --grace-period=1 --wait=false >/dev/null
