#!/usr/bin/env bash
# 템플릿(이미지)을 바꾸면: ReplicaSet 은 기존 파드를 그대로 두고, Deployment 는 새 ReplicaSet 으로 갈아탄다 (Mac 에서 실행)
cd "$(dirname "$0")/../.."
K="./lab kubectl"; NS=ch05
img(){ $K get pod -n $NS -l app=$1 -o jsonpath='{range .items[*]}    {.metadata.name}  {.spec.containers[0].image}  owner={.metadata.ownerReferences[0].name}{"\n"}{end}'; }
echo "# 11 ReplicaSet vs Deployment: 이미지 변경 ($(date '+%F %T %Z'))"
$K create deploy dp-demo -n $NS --image=nginx:1.27-alpine --replicas=2 >/dev/null
cat <<'Y' | $K apply -n $NS -f - >/dev/null
apiVersion: apps/v1
kind: ReplicaSet
metadata: {name: rs-only}
spec:
  replicas: 2
  selector: {matchLabels: {app: rs-only}}
  template:
    metadata: {labels: {app: rs-only}}
    spec: {containers: [{name: web, image: nginx:1.27-alpine}]}
Y
$K rollout status deploy/dp-demo -n $NS --timeout=120s >/dev/null; $K wait pod -n $NS -l app=rs-only --for=condition=Ready --timeout=120s >/dev/null
echo; echo "## ReplicaSet 템플릿 이미지를 nginx:1.28-alpine 으로 바꾼 뒤 15초"
$K set image rs/rs-only web=nginx:1.28-alpine -n $NS >/dev/null; sleep 15
echo "  RS 템플릿: $($K get rs rs-only -n $NS -o jsonpath='{.spec.template.spec.containers[0].image}')"; img rs-only
echo; echo "## Deployment 이미지를 nginx:1.28-alpine 으로 바꾼 뒤 rollout 완료"
$K set image deploy/dp-demo nginx=nginx:1.28-alpine -n $NS >/dev/null; $K rollout status deploy/dp-demo -n $NS --timeout=180s >/dev/null
$K get rs -n $NS -l app=dp-demo -o custom-columns='    RS:.metadata.name,DESIRED:.spec.replicas,IMAGE:.spec.template.spec.containers[0].image,REVISION:.metadata.annotations.deployment\.kubernetes\.io/revision'
img dp-demo
echo; echo "## 되돌리기: rollout undo"
$K rollout undo deploy/dp-demo -n $NS >/dev/null; $K rollout status deploy/dp-demo -n $NS --timeout=180s >/dev/null
$K get rs -n $NS -l app=dp-demo -o custom-columns='    RS:.metadata.name,DESIRED:.spec.replicas,IMAGE:.spec.template.spec.containers[0].image,REVISION:.metadata.annotations.deployment\.kubernetes\.io/revision'
$K delete deploy dp-demo -n $NS >/dev/null; $K delete rs rs-only -n $NS >/dev/null
