#!/usr/bin/env bash
# 만들 때 YAML 에 status 를 적으면 어떻게 되나: status.phase: Running 을 넣고 server dry-run (Mac 에서 실행)
# 실습 저장소 루트에서 실행한다. 네임스페이스 blog-59 만 만들고 지운다. 객체는 dry-run 이라 저장되지 않는다.
K="./lab kubectl"; NS=blog-59
echo "# 59 status 를 적어 보내면 ($(date '+%F %T %Z'))"
$K create ns $NS >/dev/null
echo; echo "## 보낸 status: {phase: Running, message: written-by-me}"
cat <<Y | $K apply -n $NS --dry-run=server -o jsonpath='  저장될 status: {.status}{"\n"}' -f - 2>&1
apiVersion: v1
kind: Pod
metadata: {name: status-demo}
spec:
  containers: [{name: c, image: busybox:1.37, command: ["sleep", "3600"]}]
status:
  phase: Running
  message: written-by-me
Y
$K delete ns $NS --wait=false >/dev/null
