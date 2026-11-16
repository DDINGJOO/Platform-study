#!/usr/bin/env bash
# rollout status 가 끝난 순간 옛 ReplicaSet 파드는 무슨 상태인가: 종료 중(deletionTimestamp)인가, status.terminatingReplicas 에 잡히나 (Mac 에서 실행)
cd "$(dirname "$0")/../.."
K="./lab kubectl"; NS=ch05; D=term-demo
echo "# 19 rollout 완료 직후 옛 파드 ($(date '+%F %T %Z'))"
$K create deploy $D -n $NS --image=nginx:1.27-alpine --replicas=2 >/dev/null
$K patch deploy $D -n $NS --type json -p '[{"op":"add","path":"/spec/template/spec/terminationGracePeriodSeconds","value":20},{"op":"replace","path":"/spec/template/spec/containers/0/command","value":["sh","-c","trap \"sleep 15; exit 0\" TERM; nginx -g \"daemon off;\" & wait"]}]' >/dev/null
$K rollout status deploy/$D -n $NS --timeout=120s >/dev/null
echo "  (컨테이너가 SIGTERM 을 받으면 15초 뒤에 끝나게 해 종료 중인 시간을 늘렸다)"
$K set image deploy/$D nginx=nginx:1.28-alpine -n $NS >/dev/null
s=$(date +%s); $K rollout status deploy/$D -n $NS --timeout=180s >/dev/null; echo; echo "## rollout status 끝남 (+$(( $(date +%s) - s ))s)"
echo "  deploy status: replicas=$($K get deploy $D -n $NS -o jsonpath='{.status.replicas}') updated=$($K get deploy $D -n $NS -o jsonpath='{.status.updatedReplicas}') available=$($K get deploy $D -n $NS -o jsonpath='{.status.availableReplicas}') terminatingReplicas=$($K get deploy $D -n $NS -o jsonpath='{.status.terminatingReplicas}')"
$K get pod -n $NS -l app=$D -o custom-columns='  POD:.metadata.name,IMAGE:.spec.containers[0].image,PHASE:.status.phase,DELETION:.metadata.deletionTimestamp'
sleep 20; echo; echo "## 20초 뒤"
echo "  terminatingReplicas=$($K get deploy $D -n $NS -o jsonpath='{.status.terminatingReplicas}')"
$K get pod -n $NS -l app=$D -o custom-columns='  POD:.metadata.name,IMAGE:.spec.containers[0].image,PHASE:.status.phase,DELETION:.metadata.deletionTimestamp'
$K delete deploy $D -n $NS >/dev/null
