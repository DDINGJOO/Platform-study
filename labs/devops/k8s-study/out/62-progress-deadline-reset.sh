#!/usr/bin/env bash
# progressDeadlineSeconds 30 인데 왜 76초 만에 실패했나: 파드가 잠깐씩 Ready 가 될 때마다 진행으로 쳐서 시계가 다시 시작되는지 (Mac 에서 실행)
# 근거 소스: sources/k8s-v1.37.2-deployment-progress-excerpt.go (DeploymentProgressing 이 ReadyReplicas 증가를 진행으로 본다)
cd "$(dirname "$0")/../.."
K="./lab kubectl"; NS=ch05; D=deadline-demo
echo "# 18 progress deadline 이 다시 시작되는가 ($(date '+%F %T %Z')), minReadySeconds 10, progressDeadlineSeconds 30"
cat <<Y | $K apply -n $NS -f - >/dev/null
apiVersion: apps/v1
kind: Deployment
metadata: {name: $D}
spec:
  replicas: 1
  minReadySeconds: 10
  progressDeadlineSeconds: 30
  selector: {matchLabels: {app: $D}}
  template:
    metadata: {labels: {app: $D}}
    spec:
      containers:
      - {name: web1, image: nginx:1.27-alpine}
      - {name: web2, image: nginx:1.27-alpine}
Y
T0=$(date +%s); last=""
echo "  경과  ready avail | Progressing 사유 (lastUpdateTime) | 파드 READY 재시작"
while [ $(( $(date +%s) - T0 )) -lt 150 ]; do
  r=$($K get deploy $D -n $NS -o jsonpath='{.status.readyReplicas}'); a=$($K get deploy $D -n $NS -o jsonpath='{.status.availableReplicas}')
  pc=$($K get deploy $D -n $NS -o jsonpath='{.status.conditions[?(@.type=="Progressing")].reason} ({.status.conditions[?(@.type=="Progressing")].lastUpdateTime})')
  pod=$($K get pod -n $NS -l app=$D --no-headers 2>/dev/null | awk '{print $2, "restarts="$4}')
  cur="ready=${r:-0} avail=${a:-0} | $pc | $pod"
  [ "$cur" != "$last" ] && { printf '  +%3ss  %s\n' $(( $(date +%s) - T0 )) "$cur"; last=$cur; }
  echo "$pc" | grep -q ProgressDeadlineExceeded && break
  sleep 1
done
$K delete deploy $D -n $NS >/dev/null
