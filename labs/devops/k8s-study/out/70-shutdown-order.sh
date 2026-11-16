#!/usr/bin/env bash
# 사이드카 두 개와 앱 컨테이너가 어떤 순서로 끝나나: (a) 앱이 스스로 끝날 때 (b) 파드를 지울 때 (c) 유예 시간이 모자랄 때 (Mac 에서 실행)
# 네임스페이스 why-sidecar만 쓴다. 사이드카 s1(먼저 선언), s2(나중 선언). 각 컨테이너는 신호를 받은 시각을 로그로 남긴다.
cd "$(dirname "$0")/../../.."   # 실습 저장소 루트
K="./lab kubectl"; NS=why-sidecar
apply(){ $K apply -n $NS -f - >/dev/null || { echo "apply 실패"; exit 1; }; }
$K create ns $NS >/dev/null 2>&1 || true
TMP=$(mktemp -d)

# 사이드카: TERM을 받으면 2초 정리 후 exit 0. preStop은 PID 1의 stdout에 한 줄 남긴다.
sidecar(){ # $1=이름 $2=TERM 뒤 정리 시간(초)
cat <<Y
  - name: $1
    image: busybox:1.37
    restartPolicy: Always
    env: [{name: SC, value: $1}]
    command: [sh, -c, 'trap "echo \$SC got-TERM; sleep $2; echo \$SC exit-0; exit 0" TERM; echo \$SC start; while true; do sleep 1 & wait \$!; done']
    lifecycle:
      preStop: {exec: {command: [sh, -c, 'echo "\$SC preStop-hook" > /proc/1/fd/1']}}
Y
}
# 로그를 런타임 타임스탬프(노드 시각, KST)와 함께 한 줄로 합친다
merge(){ cat "$@" | sort | awk '{split($1,t,"T"); printf "    %s  %s\n", substr(t[2],1,12), substr($0, index($0,$2))}'; }
# watch로 남긴 마지막 상태에서 컨테이너별 종료 시각과 exit code
final(){ jq -s -r '[.[] | select(.status.containerStatuses != null)] | last | .status as $s
  | (($s.initContainerStatuses // []) + ($s.containerStatuses // []))[]
  | "    \(.name): finishedAt=\(.state.terminated.finishedAt // .lastState.terminated.finishedAt // "-") exit=\(.state.terminated.exitCode // .lastState.terminated.exitCode // "-") reason=\(.state.terminated.reason // "-")"' "$1"; }
follow(){ # 파드 $1의 컨테이너 로그를 백그라운드로 따라간다
  for c in s1 s2 app; do $K logs -f --timestamps -n $NS $1 -c $c > $TMP/$1-$c.log 2>/dev/null & done
}

echo "# 사이드카 종료 순서 ($(date '+%F %T %Z'))"
$K version 2>/dev/null | grep Server

echo; echo "## (a) restartPolicy: Never, 앱이 8초 뒤 스스로 exit 0"
cat <<Y | apply || exit 1
apiVersion: v1
kind: Pod
metadata: {name: order-a}
spec:
  restartPolicy: Never
  initContainers:
$(sidecar s1 2)
$(sidecar s2 2)
  containers:
  - {name: app, image: busybox:1.37, command: [sh, -c, 'echo app start; sleep 8; echo app exit-0']}
Y
$K wait -n $NS --for=condition=Ready pod/order-a --timeout=60s >/dev/null 2>&1
follow order-a
for i in $(seq 1 30); do ph=$($K get pod order-a -n $NS -o jsonpath='{.status.phase}'); [ "$ph" = Succeeded ] || [ "$ph" = Failed ] && break; sleep 2; done
sleep 1
echo "  phase=$ph"
echo "  로그(kubectl logs --timestamps, 노드 시각 KST +09:00):"; merge $TMP/order-a-*.log
$K get pod order-a -n $NS -o json > $TMP/a.json; echo "  컨테이너 상태:"; final $TMP/a.json

echo; echo "## (b) restartPolicy: Always, 파드 삭제. 앱은 TERM을 받고 6초 동안 정리한 뒤 exit 0 (유예 30초)"
cat <<Y | apply || exit 1
apiVersion: v1
kind: Pod
metadata: {name: order-b}
spec:
  initContainers:
$(sidecar s1 2)
$(sidecar s2 2)
  containers:
  - name: app
    image: busybox:1.37
    command: [sh, -c, 'trap "echo app got-TERM-draining-6s; sleep 6; echo app exit-0; exit 0" TERM; echo app start; while true; do sleep 1 & wait \$!; done']
Y
$K wait -n $NS --for=condition=Ready pod/order-b --timeout=60s >/dev/null
follow order-b
$K get pod order-b -n $NS -w -o json > $TMP/b-watch.json 2>/dev/null &
sleep 2
echo "  $(date -u '+%T') UTC kubectl delete pod order-b"
$K delete pod order-b -n $NS --wait=true >/dev/null
sleep 1
echo "  로그(kubectl logs --timestamps, 노드 시각 KST +09:00):"; merge $TMP/order-b-*.log
echo "  마지막으로 본 컨테이너 상태:"; final $TMP/b-watch.json

echo; echo "## (c) 유예 6초, 앱은 TERM을 무시, 사이드카는 TERM 뒤 5초 정리 (모자람)"
cat <<Y | apply || exit 1
apiVersion: v1
kind: Pod
metadata: {name: order-c}
spec:
  terminationGracePeriodSeconds: 6
  initContainers:
$(sidecar s1 5)
$(sidecar s2 5)
  containers:
  - name: app
    image: busybox:1.37
    command: [sh, -c, 'trap "echo app got-TERM-ignored" TERM; echo app start; while true; do sleep 1 & wait \$!; done']
Y
$K wait -n $NS --for=condition=Ready pod/order-c --timeout=60s >/dev/null
follow order-c
$K get pod order-c -n $NS -w -o json > $TMP/c-watch.json 2>/dev/null &
sleep 2
echo "  $(date -u '+%T') UTC kubectl delete pod order-c"
$K delete pod order-c -n $NS --wait=true >/dev/null
sleep 1
echo "  로그(kubectl logs --timestamps, 노드 시각 KST +09:00):"; merge $TMP/order-c-*.log
echo "  마지막으로 본 컨테이너 상태:"; final $TMP/c-watch.json

$K delete pod order-a -n $NS --wait=false >/dev/null 2>&1
kill $(jobs -p) 2>/dev/null; rm -rf $TMP
