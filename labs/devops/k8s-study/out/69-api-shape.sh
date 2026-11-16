#!/usr/bin/env bash
# 2018·2019 사이드카 설계의 필드(sidecar: true, lifecycle.type)와 2023 설계의 필드(initContainers[].restartPolicy)를 v1.37.2 API 서버가 어떻게 받나 (Mac 에서 실행)
# 실습 저장소 루트에서 실행한다. 네임스페이스 blog-69 를 만들고 요청은 모두 --dry-run=server 로 보낸다(파드를 만들지 않는다). 끝나면 네임스페이스를 지운다.
K="./lab kubectl"; NS=blog-69
$K create ns $NS >/dev/null 2>&1 || true
echo "# 사이드카 API 모양 ($(date '+%F %T %Z'))"
$K version 2>/dev/null | grep Server
try(){ echo; echo "## $1"; $K apply -n $NS --dry-run=server -f - 2>&1 | sed 's/^/  /'; }

cat <<'Y' | try "(1) 2018 첫 KEP 모양: containers 안에 sidecar: true"
apiVersion: v1
kind: Pod
metadata: {name: kep2018}
spec:
  containers:
  - {name: app, image: busybox:1.37, command: [sh, -c, 'sleep 5']}
  - {name: proxy, image: busybox:1.37, sidecar: true, command: [sh, -c, 'sleep 3600']}
Y

cat <<'Y' | try "(2) 2019 implementable 모양: containers 안에 lifecycle.type: Sidecar"
apiVersion: v1
kind: Pod
metadata: {name: kep2019}
spec:
  containers:
  - {name: app, image: busybox:1.37, command: [sh, -c, 'sleep 5']}
  - {name: proxy, image: busybox:1.37, lifecycle: {type: Sidecar}, command: [sh, -c, 'sleep 3600']}
Y

cat <<'Y' | try "(3) 2023 KEP 모양: initContainers 안에 restartPolicy: Always (+ startupProbe)"
apiVersion: v1
kind: Pod
metadata: {name: kep2023}
spec:
  initContainers:
  - name: proxy
    image: busybox:1.37
    restartPolicy: Always
    command: [sh, -c, 'sleep 3600']
    startupProbe: {exec: {command: ['true']}}
  containers:
  - {name: app, image: busybox:1.37, command: [sh, -c, 'sleep 5']}
Y

cat <<'Y' | try "(4) restartPolicy 가 없는 보통 init 컨테이너에 startupProbe"
apiVersion: v1
kind: Pod
metadata: {name: plain-init-probe}
spec:
  initContainers:
  - name: setup
    image: busybox:1.37
    command: [sh, -c, 'echo setup']
    startupProbe: {exec: {command: ['true']}}
  containers:
  - {name: app, image: busybox:1.37, command: [sh, -c, 'sleep 5']}
Y

echo; echo "## (5) kubectl explain pod.spec.containers.lifecycle (필드 목록)"
$K explain pod.spec.containers.lifecycle 2>&1 | sed -n '/^FIELDS:/,$p' | grep -E '^  [a-zA-Z]' | sed 's/^/  /'

echo; echo "## (6) kubectl explain pod.spec.initContainers.restartPolicy"
$K explain pod.spec.initContainers.restartPolicy 2>&1 | sed 's/^/  /'

$K delete ns $NS --wait=true >/dev/null
echo; echo "# 정리: 네임스페이스 $NS 삭제 ($($K get ns $NS >/dev/null 2>&1 && echo 남음 || echo 없음))"
