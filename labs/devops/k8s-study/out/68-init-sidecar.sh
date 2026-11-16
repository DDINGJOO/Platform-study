#!/usr/bin/env bash
# init 컨테이너 순서와 사이드카 두 방식: 네이티브(initContainers + restartPolicy: Always) vs 옛 방식(containers 에 같이) (Mac 에서 실행)
cd "$(dirname "$0")/../.."
K="./lab kubectl"; NS=ch05
st(){ $K get pod $1 -n $NS -o go-template='{{range .status.initContainerStatuses}}    init/{{.name}}: {{range $k,$v := .state}}{{$k}}{{if $v.startedAt}} start={{$v.startedAt}}{{end}}{{if $v.finishedAt}} end={{$v.finishedAt}}{{end}}{{if $v.reason}} ({{$v.reason}}){{end}}{{end}}{{"\n"}}{{end}}{{range .status.containerStatuses}}    main/{{.name}}: {{range $k,$v := .state}}{{$k}}{{if $v.startedAt}} start={{$v.startedAt}}{{end}}{{if $v.finishedAt}} end={{$v.finishedAt}}{{end}}{{if $v.reason}} ({{$v.reason}}){{end}}{{end}}{{"\n"}}{{end}}'; }
echo "# 12 init 컨테이너와 사이드카 ($(date '+%F %T %Z'))"
cat <<'Y' | $K apply -n $NS -f - >/dev/null
apiVersion: v1
kind: Pod
metadata: {name: native-sidecar}
spec:
  restartPolicy: Never
  initContainers:
  - {name: init1, image: busybox:1.37, command: [sh, -c, "sleep 2"]}
  - {name: logger, image: busybox:1.37, restartPolicy: Always, command: [sh, -c, "while true; do sleep 1; done"]}
  - {name: init2, image: busybox:1.37, command: [sh, -c, "sleep 2"]}
  containers:
  - {name: app, image: busybox:1.37, command: [sh, -c, "sleep 5; exit 0"]}
---
apiVersion: v1
kind: Pod
metadata: {name: old-sidecar}
spec:
  restartPolicy: Never
  containers:
  - {name: app, image: busybox:1.37, command: [sh, -c, "sleep 5; exit 0"]}
  - {name: logger, image: busybox:1.37, command: [sh, -c, "while true; do sleep 1; done"]}
Y
sleep 30
for p in native-sidecar old-sidecar; do
  echo; echo "## $p (30초 뒤) phase=$($K get pod $p -n $NS -o jsonpath='{.status.phase}')  kubectl READY/STATUS: $($K get pod $p -n $NS --no-headers | awk '{print $2, $3}')"
  st $p
done
$K delete pod native-sidecar old-sidecar -n $NS --grace-period=1 --wait=false >/dev/null
