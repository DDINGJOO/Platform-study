#!/usr/bin/env bash
# 네이티브 사이드카 파드는 앱이 끝난 뒤 언제 끝나나: 신호를 무시하는 사이드카 vs SIGTERM 에 바로 끝나는 사이드카 (Mac 에서 실행)
cd "$(dirname "$0")/../.."
K="./lab kubectl"; NS=ch05
for kind in ignore trap; do
  if [ $kind = ignore ]; then CMD='while true; do sleep 1; done'; else CMD='trap "exit 0" TERM; while true; do sleep 1; done'; fi
  P=sidecar-$kind
  cat <<Y | $K apply -n $NS -f - >/dev/null
apiVersion: v1
kind: Pod
metadata: {name: $P}
spec:
  restartPolicy: Never
  initContainers:
  - {name: logger, image: busybox:1.37, restartPolicy: Always, command: [sh, -c, '$CMD']}
  containers:
  - {name: app, image: busybox:1.37, command: [sh, -c, "sleep 5; exit 0"]}
Y
  for i in $(seq 1 45); do ph=$($K get pod $P -n $NS -o jsonpath='{.status.phase}'); [ "$ph" = Succeeded ] || [ "$ph" = Failed ] && break; sleep 2; done
  echo; echo "## $P  사이드카 명령: $CMD"
  echo "  phase=$ph"
  $K get pod $P -n $NS -o go-template='{{range .status.containerStatuses}}  app    end={{.state.terminated.finishedAt}} exit={{.state.terminated.exitCode}}{{"\n"}}{{end}}{{range .status.initContainerStatuses}}  logger end={{.state.terminated.finishedAt}} exit={{.state.terminated.exitCode}} reason={{.state.terminated.reason}}{{"\n"}}{{end}}'
done
$K delete pod sidecar-ignore sidecar-trap -n $NS --wait=false >/dev/null
