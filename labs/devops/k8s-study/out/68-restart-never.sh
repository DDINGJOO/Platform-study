#!/usr/bin/env bash
# 파드 restartPolicy: Never에서 사이드카가 죽으면: 네이티브 사이드카는 다시 뜨고 파드는 Succeeded, 옛 방식은 그대로 죽고 Failed (Mac 에서 실행)
# 네임스페이스 why-sidecar만 쓴다. 두 파드 모두 사이드카가 4초마다 exit 1로 죽고, 앱은 40초 뒤 exit 0.
cd "$(dirname "$0")/../../.."   # 실습 저장소 루트
K="./lab kubectl"; NS=why-sidecar
$K create ns $NS >/dev/null 2>&1 || true
echo "# restartPolicy: Never와 죽는 사이드카 ($(date '+%F %T %Z'))"
cat <<'Y' | $K apply -n $NS -f - >/dev/null || exit 1
apiVersion: v1
kind: Pod
metadata: {name: never-native}
spec:
  restartPolicy: Never
  initContainers:
  - {name: crashy, image: busybox:1.37, restartPolicy: Always, command: [sh, -c, 'echo crashy start; sleep 4; echo crashy exit-1; exit 1']}
  containers:
  - {name: app, image: busybox:1.37, command: [sh, -c, 'sleep 40; echo app exit-0']}
---
apiVersion: v1
kind: Pod
metadata: {name: never-old}
spec:
  restartPolicy: Never
  containers:
  - {name: app, image: busybox:1.37, command: [sh, -c, 'sleep 40; echo app exit-0']}
  - {name: crashy, image: busybox:1.37, command: [sh, -c, 'echo crashy start; sleep 4; echo crashy exit-1; exit 1']}
Y
st(){ $K get pod $1 -n $NS -o json | jq -r '
  "    phase=\(.status.phase)",
  (((.status.initContainerStatuses // []) + (.status.containerStatuses // []))[]
  | "    \(.name): restartCount=\(.restartCount) state=\(.state | keys[0])\(if .state.waiting.reason then "(\(.state.waiting.reason))" elif .state.terminated then "(exit=\(.state.terminated.exitCode) reason=\(.state.terminated.reason) msg=\(.state.terminated.message // "-"))" else "" end) lastExit=\(.lastState.terminated.exitCode // "-")")'; }
T0=$(date +%s)
echo; echo "## 3초마다 (경과초 | never-native: phase crashy[재시작수 상태 lastExit] app | never-old: phase crashy app)"
row(){ $K get pod $1 -n $NS -o json | jq -r '[.status.phase] + [((.status.initContainerStatuses // []) + (.status.containerStatuses // []))[] | "\(.name)[\(.restartCount) \(.state | keys[0])\(if .state.terminated then ":\(.state.terminated.exitCode)" elif .state.waiting.reason then ":\(.state.waiting.reason)" else "" end) last=\(.lastState.terminated.exitCode // "-")]"] | join(" ")'; }
for i in $(seq 1 22); do
  printf "  %3ss | %s | %s\n" $(( $(date +%s) - T0 )) "$(row never-native)" "$(row never-old)"
  ph=$($K get pod never-native -n $NS -o jsonpath='{.status.phase}'); [ "$ph" = Succeeded ] && [ $i -gt 15 ] && break
  sleep 3
done
echo; echo "## 마지막 상태"
for p in never-native never-old; do echo "  $p"; st $p; done
echo; echo "## never-native 이벤트"
$K get events -n $NS --field-selector involvedObject.name=never-native --sort-by=.lastTimestamp -o custom-columns='LAST:.lastTimestamp,COUNT:.count,REASON:.reason,MSG:.message' | sed 's/^/  /'
echo; echo "## kubectl get pod"
$K get pod never-native never-old -n $NS | sed 's/^/  /'
$K delete pod never-native never-old -n $NS --wait=false >/dev/null
