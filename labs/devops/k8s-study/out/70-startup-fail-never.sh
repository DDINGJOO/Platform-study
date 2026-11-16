#!/usr/bin/env bash
# restartPolicy: Never 파드에서 사이드카가 시작 단계(startupProbe)에 실패하면 파드가 Failed가 되나, 사이드카만 다시 뜨나 (Mac 에서 실행)
# 네임스페이스 why-sidecar만 쓴다. KEP-753은 2024-10(enh PR #4880) 전까지 "Never면 시작 단계 실패 사이드카는 재시작하지 않고 파드 실패"라고 적었었다.
cd "$(dirname "$0")/../../.."   # 실습 저장소 루트
K="./lab kubectl"; NS=why-sidecar; P=startfail
$K create ns $NS >/dev/null 2>&1 || true
echo "# Never 파드 + startupProbe가 늘 실패하는 사이드카 ($(date '+%F %T %Z'))"
cat <<'Y' | $K apply -n $NS -f - >/dev/null || exit 1
apiVersion: v1
kind: Pod
metadata: {name: startfail}
spec:
  restartPolicy: Never
  initContainers:
  - name: side
    image: busybox:1.37
    restartPolicy: Always
    command: [sh, -c, 'while true; do sleep 1; done']
    startupProbe: {exec: {command: ['false']}, periodSeconds: 2, failureThreshold: 2}
  containers:
  - {name: app, image: busybox:1.37, command: [sh, -c, 'echo app ran']}
Y
for t in 15 45; do
  sleep $(( t == 15 ? 15 : 30 ))
  echo; echo "## 생성 후 약 ${t}초"
  $K get pod $P -n $NS -o json | jq -r '"  phase=\(.status.phase)",
    (((.status.initContainerStatuses // []) + (.status.containerStatuses // []))[]
    | "  \(.name): restartCount=\(.restartCount) state=\(.state | keys[0])\(if .state.waiting.reason then "(\(.state.waiting.reason))" else "" end) started=\(.started) lastExit=\(.lastState.terminated.exitCode // "-")")'
  $K get pod $P -n $NS --no-headers | awk '{print "  kubectl: READY=" $2 " STATUS=" $3 " RESTARTS=" $4}'
done
echo; echo "## 이벤트"
$K get events -n $NS --field-selector involvedObject.name=$P --sort-by=.lastTimestamp -o custom-columns='LAST:.lastTimestamp,COUNT:.count,REASON:.reason,MSG:.message' | grep -v 'Pulled\|Scheduled' | sed 's/^/  /'
$K delete pod $P -n $NS --grace-period=1 --wait=false >/dev/null
