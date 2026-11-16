#!/usr/bin/env bash
# 사이드카를 containers 에 같이 넣던 옛 방식의 우회책이 v1.37.2 에서 어떻게 동작하나: 끝남 파일, postStart 순서, preStop sleep (Mac 에서 실행)
# 실습 저장소 루트에서 실행한다. 네임스페이스 blog-68 만 쓰고 끝나면 지운다.
#   (a) Job: work 가 끝날 때 emptyDir 에 파일을 남기고 side 가 그 파일을 보고 스스로 끝난다 (#25908 의 2016 년 답)
#   (b) 파드: proxy 를 containers 맨 앞에 두고 postStart 훅이 5초 걸리게 한다 (Istio holdApplicationUntilProxyStarts 모양)
#   (c) 파드 삭제: app 은 TERM 뒤 4초 정리, proxy 는 TERM 즉시 종료 (preStop 없음)
#   (d) (c)와 같고 proxy 에 preStop sleep 6 만 더한다
K="./lab kubectl"; NS=blog-68
$K create ns $NS >/dev/null 2>&1 || true
TMP=$(mktemp -d)
echo "# 옛 방식 사이드카 우회책 ($(date '+%F %T %Z'))"
$K version 2>/dev/null | grep Server

echo; echo "## (a) 끝남 파일로 맞춘 Job (containers 에 work, side)"
cat <<'Y' | $K apply -n $NS -f - >/dev/null || exit 1
apiVersion: batch/v1
kind: Job
metadata: {name: job-donefile}
spec:
  backoffLimit: 0
  template:
    spec:
      restartPolicy: Never
      volumes: [{name: sig, emptyDir: {}}]
      containers:
      - name: work
        image: busybox:1.37
        volumeMounts: [{name: sig, mountPath: /sig}]
        command: [sh, -c, 'trap "touch /sig/main-done" EXIT; echo work start; sleep 5; echo work done']
      - name: side
        image: busybox:1.37
        volumeMounts: [{name: sig, mountPath: /sig}]
        command: [sh, -c, 'echo side start; while [ ! -f /sig/main-done ]; do sleep 1; done; echo side saw main-done; exit 0']
Y
sleep 25
$K get job job-donefile -n $NS -o json | jq -r '"  job: succeeded=\(.status.succeeded // 0) startTime=\(.status.startTime) completionTime=\(.status.completionTime // "-") conditions=\([.status.conditions[]? | select(.status=="True") | .type] | join(","))"'
pod=$($K get pod -n $NS -l job-name=job-donefile -o name | head -1)
$K get -n $NS $pod -o json | jq -r '"  pod: phase=\(.status.phase)", (.status.containerStatuses[] | "  \(.name): finishedAt=\(.state.terminated.finishedAt // "-") exit=\(.state.terminated.exitCode // "-")")'
echo "  side 로그:"; $K logs -n $NS $pod -c side | sed 's/^/    /'

echo; echo "## (b) postStart 5초 훅을 단 proxy 를 맨 앞에 둔 파드 vs 맨 뒤에 둔 파드 (startedAt, UTC)"
for order in first last; do
  PROXY='{name: proxy, image: busybox:1.37, command: [sh, -c, "while true; do sleep 1; done"], lifecycle: {postStart: {exec: {command: [sh, -c, "sleep 5"]}}}}'
  APP='{name: app, image: busybox:1.37, command: [sh, -c, "while true; do sleep 1; done"]}'
  if [ $order = first ]; then C1=$PROXY; C2=$APP; else C1=$APP; C2=$PROXY; fi
  cat <<Y | $K apply -n $NS -f - >/dev/null || exit 1
apiVersion: v1
kind: Pod
metadata: {name: hook-$order}
spec:
  terminationGracePeriodSeconds: 1
  containers:
  - $C1
  - $C2
Y
done
sleep 20
for order in first last; do
  echo "  hook-$order (containers 순서: $($K get pod hook-$order -n $NS -o jsonpath='{.spec.containers[*].name}'))"
  $K get pod hook-$order -n $NS -o json | jq -r '.status.containerStatuses[] | "    \(.name): startedAt=\(.state.running.startedAt // "-")"'
done
$K get events -n $NS --field-selector involvedObject.name=hook-first --sort-by=.firstTimestamp -o custom-columns='TIME:.firstTimestamp,REASON:.reason,MSG:.message' | grep -E 'TIME|Started' | sed 's/^/  /'
$K delete pod hook-first hook-last -n $NS --wait=false >/dev/null

stop_case(){ # $1=파드 이름 $2=yes 면 proxy 에 preStop sleep 6
  if [ "$2" = yes ]; then PRE='lifecycle: {preStop: {exec: {command: [sh, -c, "echo proxy preStop-sleep-6 > /proc/1/fd/1; sleep 6"]}}}'; else PRE=''; fi
  cat <<Y | $K apply -n $NS -f - >/dev/null || exit 1
apiVersion: v1
kind: Pod
metadata: {name: $1}
spec:
  containers:
  - name: app
    image: busybox:1.37
    command: [sh, -c, 'trap "echo app got-TERM-draining-4s; sleep 4; echo app exit-0; exit 0" TERM; echo app start; while true; do sleep 1 & wait \$!; done']
  - name: proxy
    image: busybox:1.37
    command: [sh, -c, 'trap "echo proxy got-TERM; echo proxy exit-0; exit 0" TERM; echo proxy start; while true; do sleep 1 & wait \$!; done']
    $PRE
Y
  $K wait -n $NS --for=condition=Ready pod/$1 --timeout=60s >/dev/null
  for c in app proxy; do $K logs -f --timestamps -n $NS $1 -c $c > $TMP/$1-$c.log 2>/dev/null & done
  $K get pod $1 -n $NS -w -o json > $TMP/$1-watch.json 2>/dev/null &
  sleep 2
  echo "  $(date -u '+%T') UTC kubectl delete pod $1"
  $K delete pod $1 -n $NS --wait=true >/dev/null
  sleep 1
  echo "  로그(kubectl logs --timestamps, 노드 시각 KST +09:00):"
  cat $TMP/$1-*.log | sort | awk '{split($1,t,"T"); printf "    %s  %s\n", substr(t[2],1,12), substr($0, index($0,$2))}'
  echo "  마지막으로 본 컨테이너 상태:"
  jq -s -r '[.[] | select(.status.containerStatuses != null)] | last | .status.containerStatuses[] | "    \(.name): finishedAt=\(.state.terminated.finishedAt // "-") exit=\(.state.terminated.exitCode // "-")"' $TMP/$1-watch.json
}
echo; echo "## (c) 파드 삭제, proxy 에 preStop 없음 (app 은 TERM 뒤 4초 정리, 유예 30초)"
stop_case stop-plain no
echo; echo "## (d) 파드 삭제, proxy 에 preStop sleep 6"
stop_case stop-prestop yes

kill $(jobs -p) 2>/dev/null; rm -rf $TMP
$K delete job job-donefile -n $NS --wait=false >/dev/null 2>&1
$K delete ns $NS --wait=true >/dev/null
echo; echo "# 정리: 네임스페이스 $NS 삭제 ($($K get ns $NS >/dev/null 2>&1 && echo 남음 || echo 없음))"
