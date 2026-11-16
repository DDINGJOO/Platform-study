#!/usr/bin/env bash
# 2016년 이슈 #25908의 모양 그대로: 사이드카가 붙은 Job이 끝나나 (네이티브 vs 옛 방식), 그리고 Job 완료 시각에 사이드카 종료가 들어가나 (Mac 에서 실행)
# 네임스페이스 why-sidecar만 쓴다. 사이드카는 TERM을 받으면 3초 정리하고 exit 0.
cd "$(dirname "$0")/../../.."   # 실습 저장소 루트
K="./lab kubectl"; NS=why-sidecar
$K create ns $NS >/dev/null 2>&1 || true
echo "# 사이드카가 붙은 Job ($(date '+%F %T %Z'))"
SIDE='trap "echo side got-TERM; sleep 3; echo side exit-0; exit 0" TERM; echo side start; while true; do sleep 1 & wait $!; done'
cat <<Y | $K apply -n $NS -f - >/dev/null || exit 1
apiVersion: batch/v1
kind: Job
metadata: {name: job-native}
spec:
  backoffLimit: 0
  template:
    spec:
      restartPolicy: Never
      initContainers:
      - {name: side, image: busybox:1.37, restartPolicy: Always, command: [sh, -c, '$SIDE']}
      containers:
      - {name: work, image: busybox:1.37, command: [sh, -c, 'echo work start; sleep 5; echo work done']}
---
apiVersion: batch/v1
kind: Job
metadata: {name: job-old}
spec:
  backoffLimit: 0
  template:
    spec:
      restartPolicy: Never
      containers:
      - {name: work, image: busybox:1.37, command: [sh, -c, 'echo work start; sleep 5; echo work done']}
      - {name: side, image: busybox:1.37, command: [sh, -c, '$SIDE']}
Y
sleep 45
for j in job-native job-old; do
  echo; echo "## $j (생성 후 약 45초)"
  $K get job $j -n $NS -o json | jq -r '"    job: active=\(.status.active // 0) succeeded=\(.status.succeeded // 0) startTime=\(.status.startTime) completionTime=\(.status.completionTime // "-") conditions=\([.status.conditions[]? | select(.status=="True") | .type] | join(","))"'
  pod=$($K get pod -n $NS -l job-name=$j -o name | head -1)
  $K get -n $NS $pod -o json | jq -r '"    pod: phase=\(.status.phase)",
    (((.status.initContainerStatuses // []) + (.status.containerStatuses // []))[]
    | "    \(.name): \(.state | keys[0]) finishedAt=\(.state.terminated.finishedAt // "-") exit=\(.state.terminated.exitCode // "-")")'
done
echo; echo "## kubectl get job,pod"
$K get job,pod -n $NS -l 'job-name in (job-native,job-old)' 2>/dev/null | sed 's/^/  /'
$K get job -n $NS job-native job-old | sed 's/^/  /'
$K delete job job-native job-old -n $NS --wait=false >/dev/null
