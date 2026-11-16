#!/usr/bin/env bash
# 파드 하나의 생명주기: phase · conditions · 컨테이너 상태가 바뀌는 순서와 지울 때 걸리는 시간 (Mac 에서 실행)
cd "$(dirname "$0")/../.."
K="./lab kubectl"; NS=ch05
now(){ perl -MTime::HiRes=time -e 'printf "%.1f", time'; }
T0=$(now); el(){ perl -e "printf '+%5.1fs', $(now)-$T0"; }
GT='{{.status.phase}} | {{range .status.conditions}}{{.type}}={{.status}} {{end}}| {{range .status.containerStatuses}}{{range $k,$v := .state}}{{$k}}{{if $v.reason}}({{$v.reason}}){{end}}{{if $v.exitCode}} exit={{$v.exitCode}}{{end}}{{end}} ready={{.ready}} restarts={{.restartCount}}{{end}}'
watch_pod(){ # $1 파드, $2 멈출 조건(정규식), $3 최대 초
  local last="" cur end=$(( $(date +%s) + $3 ))
  while [ $(date +%s) -lt $end ]; do
    cur=$($K get pod $1 -n $NS -o go-template="$GT" 2>/dev/null) || cur="(없음)"
    [ "$cur" != "$last" ] && { echo "  $(el) $cur"; last=$cur; }
    echo "$cur" | grep -Eq "$2" && return 0
    sleep 0.3
  done; echo "  $(el) (시간 초과)"
}
echo "# 02 파드 생명주기 관찰 ($(date '+%F %T %Z')), 네임스페이스 $NS"
$K create ns $NS --dry-run=client -o yaml | $K apply -f - >/dev/null

echo; echo "## A. 오래 도는 파드(nginx)가 Ready 가 될 때까지 — 바뀔 때만 한 줄"
echo "  표기: phase | conditions | 컨테이너 상태"
$K delete pod life-nginx -n $NS --ignore-not-found --wait >/dev/null
T0=$(now); $K run life-nginx -n $NS --image=nginx:1.27-alpine >/dev/null
watch_pod life-nginx 'Ready=True' 120
echo; echo "  노드: $($K get pod life-nginx -n $NS -o jsonpath='{.spec.nodeName}')"
echo "  conditions 의 lastTransitionTime (초 단위):"
$K get pod life-nginx -n $NS -o jsonpath='{range .status.conditions[*]}    {.lastTransitionTime}  {.type}={.status}{"\n"}{end}' | sort
echo "  이벤트:"
$K get events -n $NS --field-selector involvedObject.name=life-nginx --sort-by=.lastTimestamp -o custom-columns='    TIME:.lastTimestamp,REASON:.reason,FROM:.source.component,MSG:.message' --no-headers

echo; echo "## B. 끝나는 파드(restartPolicy: Never) — exit 0 과 exit 1"
for code in 0 1; do
  p=life-exit$code; $K delete pod $p -n $NS --ignore-not-found --wait >/dev/null
  echo "  [$p] sh -c 'sleep 3; exit $code'"
  T0=$(now); $K run $p -n $NS --image=busybox:1.37 --restart=Never -- sh -c "sleep 3; exit $code" >/dev/null
  watch_pod $p 'Succeeded|Failed' 120
  echo "    terminated: $($K get pod $p -n $NS -o jsonpath='reason={.status.containerStatuses[0].state.terminated.reason} exitCode={.status.containerStatuses[0].state.terminated.exitCode}')"
done

echo; echo "## C. 지울 때 걸리는 시간 — SIGTERM 을 받으면 끝나는 nginx vs 신호를 처리하지 않는 PID 1 sleep"
$K delete pod life-sleep -n $NS --ignore-not-found --wait >/dev/null
$K run life-sleep -n $NS --image=busybox:1.37 --restart=Never --command -- sleep infinity >/dev/null
$K wait pod/life-sleep -n $NS --for=condition=Ready --timeout=120s >/dev/null
for p in life-nginx life-sleep; do
  echo "  [$p] PID 1 = $($K exec $p -n $NS -- cat /proc/1/cmdline 2>/dev/null | tr '\0' ' ')"
  T0=$(now); $K delete pod $p -n $NS --wait=false >/dev/null
  sleep 1
  echo "    $(el) kubectl get STATUS 열: $($K get pod $p -n $NS --no-headers 2>/dev/null | awk '{print $3}') / .status.phase: $($K get pod $p -n $NS -o jsonpath='{.status.phase}' 2>/dev/null) / deletionGracePeriodSeconds: $($K get pod $p -n $NS -o jsonpath='{.metadata.deletionGracePeriodSeconds}' 2>/dev/null)"
  while $K get pod $p -n $NS >/dev/null 2>&1; do sleep 0.3; done
  echo "    $(el) 객체 사라짐"
done
$K delete pod life-exit0 life-exit1 -n $NS --ignore-not-found >/dev/null
