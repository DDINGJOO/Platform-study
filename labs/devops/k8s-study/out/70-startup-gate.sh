#!/usr/bin/env bash
# 다음 컨테이너를 붙잡는 것은 무엇인가: 사이드카의 postStart 훅, readinessProbe, startupProbe를 한 파드에서 비교 (Mac 에서 실행)
# 네임스페이스 why-sidecar만 쓴다.
#   hook    : postStart 훅이 5초 걸린다 (Istio holdApplicationUntilProxyStarts가 쓰던 방식과 같은 모양)
#   notready: readinessProbe가 늘 실패한다 (startupProbe 없음)
#   slow    : 10초 뒤에야 startupProbe가 성공한다
#   init2   : 보통 init 컨테이너, 그 다음 app
cd "$(dirname "$0")/../../.."   # 실습 저장소 루트
K="./lab kubectl"; NS=why-sidecar; P=gate
$K create ns $NS >/dev/null 2>&1 || true
echo "# 사이드카가 다음 컨테이너 시작을 붙잡는 조건 ($(date '+%F %T %Z'))"
cat <<'Y' | $K apply -n $NS -f - >/dev/null || exit 1
apiVersion: v1
kind: Pod
metadata: {name: gate}
spec:
  initContainers:
  - name: hook
    image: busybox:1.37
    restartPolicy: Always
    command: [sh, -c, 'while true; do sleep 1; done']
    lifecycle:
      postStart: {exec: {command: [sh, -c, 'sleep 5']}}
  - name: notready
    image: busybox:1.37
    restartPolicy: Always
    command: [sh, -c, 'while true; do sleep 1; done']
    readinessProbe: {exec: {command: ['false']}, periodSeconds: 2}
  - name: slow
    image: busybox:1.37
    restartPolicy: Always
    command: [sh, -c, 'sleep 10; touch /tmp/up; while true; do sleep 1; done']
    startupProbe: {exec: {command: [test, -f, /tmp/up]}, periodSeconds: 1, failureThreshold: 60}
  - name: init2
    image: busybox:1.37
    command: [sh, -c, 'echo init2 done']
  containers:
  - name: app
    image: busybox:1.37
    command: [sh, -c, 'while true; do sleep 1; done']
Y
sleep 35
echo
echo "## 컨테이너별 시작 시각 (startedAt, UTC) / started / ready"
$K get pod $P -n $NS -o json | jq -r '
  .status as $s | (($s.initContainerStatuses // []) + ($s.containerStatuses // []))[]
  | "  \(.name | .+"        " | .[0:9]) startedAt=\(.state.running.startedAt // .state.terminated.startedAt // "-")  started=\(.started)  ready=\(.ready)\(if .state.terminated then "  (terminated exit=\(.state.terminated.exitCode))" else "" end)"'
echo
echo "## 파드 조건 (lastTransitionTime, UTC)"
$K get pod $P -n $NS -o json | jq -r '.status.conditions | sort_by(.lastTransitionTime)[] | "  \(.lastTransitionTime)  \(.type)=\(.status)\(if .reason then " (\(.reason))" else "" end)"'
echo
echo "## kubectl get pod"
$K get pod $P -n $NS | sed 's/^/  /'
echo
echo "## 이벤트 (시간순)"
$K get events -n $NS --field-selector involvedObject.name=$P --sort-by=.firstTimestamp -o custom-columns='TIME:.firstTimestamp,REASON:.reason,MSG:.message' | sed 's/^/  /' | grep -v 'Pulled\|Created container' | head -20
$K delete pod $P -n $NS --grace-period=1 --wait=false >/dev/null
