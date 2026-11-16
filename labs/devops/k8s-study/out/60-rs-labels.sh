#!/usr/bin/env bash
# ReplicaSet 은 무엇을 세나: 라벨이 맞는 파드를 세서 맞춘다 (Mac 에서 실행)
cd "$(dirname "$0")/../.."
K="./lab kubectl"; NS=ch05
show(){ $K get pod -n $NS -l 'app in (rs-demo),!skip' --show-labels 2>/dev/null >/dev/null; $K get pod -n $NS -o custom-columns='    NAME:.metadata.name,STATUS:.status.phase,APP:.metadata.labels.app,OWNER:.metadata.ownerReferences[0].name,DEL:.metadata.deletionTimestamp' | grep -E 'NAME|rs-demo|bare'; }
echo "# 10 ReplicaSet 과 라벨 ($(date '+%F %T %Z'))"
cat <<'Y' | $K apply -n $NS -f - >/dev/null
apiVersion: apps/v1
kind: ReplicaSet
metadata: {name: rs-demo}
spec:
  replicas: 3
  selector: {matchLabels: {app: rs-demo}}
  template:
    metadata: {labels: {app: rs-demo}}
    spec: {containers: [{name: web, image: nginx:1.27-alpine}]}
Y
$K wait pod -n $NS -l app=rs-demo --for=condition=Ready --timeout=120s >/dev/null
echo; echo "## 0. replicas=3"; show
P1=$($K get pod -n $NS -l app=rs-demo -o jsonpath='{.items[0].metadata.name}')
echo; echo "## 1. 파드 하나 지우기 ($P1) → 다시 3개"
$K delete pod $P1 -n $NS --wait=false >/dev/null; sleep 3; show
echo; echo "## 2. 라벨만 같은 단독 파드(bare) 만들기 → RS 가 4개로 세고 하나를 지운다"
$K run bare -n $NS --image=nginx:1.27-alpine --labels=app=rs-demo >/dev/null; sleep 3; show
echo "  RS 이벤트:"; $K get events -n $NS --field-selector involvedObject.name=rs-demo --sort-by=.lastTimestamp -o custom-columns='    REASON:.reason,MSG:.message' --no-headers | tail -3
sleep 2
P2=$($K get pod -n $NS -l app=rs-demo --field-selector=status.phase=Running -o jsonpath='{.items[0].metadata.name}')
echo; echo "## 3. RS 파드 하나($P2)의 라벨을 바꾸기 → RS 에서 떨어져 나가고(owner 없음) 새 파드가 생긴다"
$K label pod $P2 -n $NS app=debug --overwrite >/dev/null; sleep 3
$K get pod -n $NS -o custom-columns='    NAME:.metadata.name,STATUS:.status.phase,APP:.metadata.labels.app,OWNER:.metadata.ownerReferences[0].name' | grep -E 'NAME|rs-demo|bare|debug'
$K delete rs rs-demo -n $NS >/dev/null; $K delete pod -n $NS -l app=debug --wait=false >/dev/null; $K delete pod bare -n $NS --ignore-not-found --wait=false >/dev/null
