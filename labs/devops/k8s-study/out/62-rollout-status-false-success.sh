#!/usr/bin/env bash
# apply 는 성공했는데 실제로는 망가진 배포를 클라이언트가 알아차리는 방법: rollout status + progressDeadlineSeconds (Mac 에서 실행)
cd "$(dirname "$0")/../.."
K="./lab kubectl"; NS=ch05
echo "# 14 망가진 배포와 rollout status ($(date '+%F %T %Z'))"
cat <<'Y' > /tmp/ch05-14.yaml
apiVersion: apps/v1
kind: Deployment
metadata: {name: same-port-deploy}
spec:
  replicas: 1
  progressDeadlineSeconds: 20
  selector: {matchLabels: {app: same-port-deploy}}
  template:
    metadata: {labels: {app: same-port-deploy}}
    spec:
      containers:
      - {name: web1, image: nginx:1.27-alpine}
      - {name: web2, image: nginx:1.27-alpine}
Y
echo; echo "## kubectl apply"; $K apply -n $NS -f /tmp/ch05-14.yaml 2>&1 | sed 's/^/  /'; echo "  exit=$?"
echo; echo "## kubectl rollout status (progressDeadlineSeconds: 20)"
s=$(date +%s); $K rollout status deploy/same-port-deploy -n $NS --timeout=90s 2>&1 | tail -2 | sed 's/^/  /'; rc=${PIPESTATUS[0]}
echo "  exit=$rc  걸린 시간 $(( $(date +%s) - s ))초"
echo; echo "## Deployment conditions"
$K get deploy same-port-deploy -n $NS -o jsonpath='{range .status.conditions[*]}  {.type}={.status} {.reason}: {.message}{"\n"}{end}'
$K delete deploy same-port-deploy -n $NS >/dev/null; rm -f /tmp/ch05-14.yaml
