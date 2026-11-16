#!/usr/bin/env bash
# 파드 restartPolicy 와 보통 컨테이너 restartPolicy 를 다르게 주면 v1.37.2 가 경고 없이 받는지, 낮추는 쪽(Always→Never)과 올리는 쪽(Never→OnFailure)이 어떻게 도는지 (Mac 에서 실행)
# 실습 저장소 루트에서 실행한다. 네임스페이스 blog-71 만 쓰고 끝나면 지운다.
#   (1) dry-run=server 로 "파드 Never + 컨테이너 Always", "파드 OnFailure + 컨테이너 Always" 를 보내고 stderr 의 Warning 까지 남긴다
#   (2) always-never : 파드 Always, 보통 컨테이너 once 에 restartPolicy: Never (3초 뒤 exit 0), app 은 계속 돈다
#   (3) never-onfail : 파드 Never, 보통 컨테이너 app 에 restartPolicy: OnFailure (처음 두 번 exit 1, 세 번째 exit 0)
K="./lab kubectl"; NS=blog-71
$K create ns $NS >/dev/null 2>&1 || true
echo "# 파드·컨테이너 restartPolicy 조합 ($(date '+%F %T %Z'))"
$K version 2>/dev/null | grep Server

echo; echo "## (1) dry-run=server, stderr 포함 (Warning 이 있으면 여기에 찍힌다)"
for pp in Never OnFailure; do
  echo "  - 파드 restartPolicy: $pp, 보통 컨테이너 helper 에 restartPolicy: Always"
  cat <<Y | $K apply -n $NS --dry-run=server -f - 2>&1 | sed 's/^/    /'
apiVersion: v1
kind: Pod
metadata: {name: dry-$(echo $pp | tr 'A-Z' 'a-z')}
spec:
  restartPolicy: $pp
  containers:
  - {name: app, image: busybox:1.37, command: [sh, -c, 'sleep 5']}
  - {name: helper, image: busybox:1.37, restartPolicy: Always, command: [sh, -c, 'sleep 3']}
Y
done

cat <<'Y' | $K apply -n $NS -f - >/dev/null || exit 1
apiVersion: v1
kind: Pod
metadata: {name: always-never}
spec:
  restartPolicy: Always
  terminationGracePeriodSeconds: 1
  containers:
  - {name: app, image: busybox:1.37, command: [sh, -c, 'while true; do sleep 1; done']}
  - {name: once, image: busybox:1.37, restartPolicy: Never, command: [sh, -c, 'sleep 3; echo once exit-0']}
---
apiVersion: v1
kind: Pod
metadata: {name: never-onfail}
spec:
  restartPolicy: Never
  volumes: [{name: w, emptyDir: {}}]
  containers:
  - name: app
    image: busybox:1.37
    restartPolicy: OnFailure
    volumeMounts: [{name: w, mountPath: /w}]
    command: [sh, -c, 'n=$(cat /w/n 2>/dev/null || echo 0); n=$((n+1)); echo $n > /w/n; echo "run $n"; if [ $n -lt 3 ]; then echo exit-1; exit 1; fi; echo exit-0']
Y
st(){ $K get pod $1 -n $NS -o json | jq -r '
  "    phase=\(.status.phase)",
  (.status.containerStatuses[] | "    \(.name): restartCount=\(.restartCount) state=\(.state | keys[0])\(if .state.terminated then "(exit=\(.state.terminated.exitCode))" elif .state.waiting.reason then "(\(.state.waiting.reason))" else "" end) lastExit=\(.lastState.terminated.exitCode // "-")")'; }
for t in 30 60; do
  sleep 30
  echo; echo "## 생성 후 약 ${t}초"
  for p in always-never never-onfail; do
    echo "  $p (컨테이너 restartPolicy: $($K get pod $p -n $NS -o jsonpath='{range .spec.containers[*]}{.name}={.restartPolicy} {end}'))"
    st $p
  done
done
echo; echo "## kubectl get pod"
$K get pod always-never never-onfail -n $NS | sed 's/^/  /'

$K delete ns $NS --wait=true >/dev/null
echo; echo "# 정리: 네임스페이스 $NS 삭제 ($($K get ns $NS >/dev/null 2>&1 && echo 남음 || echo 없음))"
