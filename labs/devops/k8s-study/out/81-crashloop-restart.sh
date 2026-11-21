#!/usr/bin/env bash
# kubelet 이 "재시작"하는 건 파드인가 컨테이너인가: 2초 뒤 exit 1 하는 컨테이너를 3분 동안 보며 파드 이름·UID·IP 와 컨테이너 재시작 간격(백오프)을 기록 (Mac 에서 실행)
cd "$(dirname "$0")/../.."
K="./lab kubectl"; NS=ch05; P=crashy
echo "# 29 CrashLoopBackOff 와 재시작 ($(date '+%F %T %Z'))"
$K run $P -n $NS --image=busybox:1.37 --restart=Always --command -- sh -c 'echo "start $(date +%T)"; sleep 2; exit 1' >/dev/null
T0=$(date +%s); last=""
echo "  경과  STATUS            restarts  파드UID(앞 8자) IP               lastState.finishedAt → state.running.startedAt"
while [ $(( $(date +%s)-T0 )) -lt 200 ]; do
  o=$($K get pod $P -n $NS -o go-template='{{(index .status.containerStatuses 0).restartCount}}|{{printf "%.8s" .metadata.uid}}|{{.status.podIP}}|{{with (index .status.containerStatuses 0).lastState.terminated}}{{.finishedAt}}{{end}}|{{with (index .status.containerStatuses 0).state.running}}{{.startedAt}}{{end}}{{with (index .status.containerStatuses 0).state.waiting}}waiting:{{.reason}}{{end}}' 2>/dev/null)
  st=$($K get pod $P -n $NS --no-headers 2>/dev/null | awk '{print $3}')
  cur="$st|$o"; [ "$cur" != "$last" ] && { IFS='|' read -r rc uid ip fin run <<< "$o"; printf '  +%3ss  %-17s %-9s %-15s %-16s %s → %s\n' $(( $(date +%s)-T0 )) "$st" "$rc" "$uid" "$ip" "${fin:--}" "${run:--}"; last=$cur; }
  sleep 1
done
echo; echo "## 컨테이너가 다시 시작된 시각(로그의 start 줄은 마지막 실행만 남는다), kubelet 이벤트"
$K get events -n $NS --field-selector involvedObject.name=$P,reason=BackOff -o custom-columns='  COUNT:.count,FIRST:.firstTimestamp,LAST:.lastTimestamp,MSG:.message' --no-headers | head -3
$K delete pod $P -n $NS --grace-period=1 --wait=false >/dev/null
