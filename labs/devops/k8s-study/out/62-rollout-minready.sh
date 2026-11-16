#!/usr/bin/env bash
# 같은 망가진 배포(80 포트 nginx 둘): rollout status 가 성공이라 한 뒤 실제 상태, 그리고 minReadySeconds 를 주면 (Mac 에서 실행)
cd "$(dirname "$0")/../.."
K="./lab kubectl"; NS=ch05
mk(){ cat <<Y
apiVersion: apps/v1
kind: Deployment
metadata: {name: $1}
spec:
  replicas: 1
  minReadySeconds: $2
  progressDeadlineSeconds: 30
  selector: {matchLabels: {app: $1}}
  template:
    metadata: {labels: {app: $1}}
    spec:
      containers:
      - {name: web1, image: nginx:1.27-alpine}
      - {name: web2, image: nginx:1.27-alpine}
Y
}
cond(){ echo "  availableReplicas=$($K get deploy $1 -n $NS -o jsonpath='{.status.availableReplicas}') 파드: $($K get pod -n $NS -l app=$1 --no-headers | awk '{print $2, $3, "restarts="$4}')"; $K get deploy $1 -n $NS -o jsonpath='{range .status.conditions[*]}  {.type}={.status} {.reason}{"\n"}{end}'; }
echo "# 14b rollout status 와 minReadySeconds ($(date '+%F %T %Z'))"
for m in 0 10; do
  D=sp-minready$m
  echo; echo "## minReadySeconds: $m"
  mk $D $m | $K apply -n $NS -f - >/dev/null
  s=$(date +%s); out=$($K rollout status deploy/$D -n $NS --timeout=90s 2>&1); rc=$?
  echo "  rollout status: exit=$rc, $(( $(date +%s) - s ))초, 마지막 줄: $(echo "$out" | tail -1)"
  echo "  [rollout status 끝난 직후]"; cond $D
  sleep 30; echo "  [30초 뒤]"; cond $D
  $K delete deploy $D -n $NS >/dev/null
done
