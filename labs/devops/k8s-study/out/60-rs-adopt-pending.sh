#!/usr/bin/env bash
# ReplicaSet 이 세는 것: 먼저 있던 단독 파드를 입양하나, 스케줄되지 않은 Pending 파드도 세나, 라벨을 바꾸면 Service 대상에서도 빠지나, Deployment 는 restartPolicy Never 를 받나 (Mac 에서 실행)
# 실습 저장소 루트에서 실행한다. 네임스페이스 blog-60 만 만들고 지운다.
K="./lab kubectl"; NS=blog-60
pods(){ $K get pod -n $NS -l "$1" -o custom-columns='    NAME:.metadata.name,PHASE:.status.phase,NODE:.spec.nodeName,APP:.metadata.labels.app,OWNER:.metadata.ownerReferences[0].kind,OWNERNAME:.metadata.ownerReferences[0].name'; }
rs(){ cat <<Y | $K apply -n $NS -f - >/dev/null
apiVersion: apps/v1
kind: ReplicaSet
metadata: {name: $1}
spec:
  replicas: 2
  selector: {matchLabels: {app: $1}}
  template:
    metadata: {labels: {app: $1}}
    spec:
      $2
      containers: [{name: web, image: nginx:1.27-alpine}]
Y
}
echo "# 60 ReplicaSet 이 세는 것 ($(date '+%F %T %Z'))"
$K create ns $NS >/dev/null

echo; echo "## 1. 라벨 app=adopt 인 단독 파드 early 를 먼저 만들고, 같은 셀렉터의 replicas=2 ReplicaSet 을 만들면"
$K run early -n $NS --image=nginx:1.27-alpine --labels=app=adopt >/dev/null
$K wait pod/early -n $NS --for=condition=Ready --timeout=120s >/dev/null
echo "  ReplicaSet 을 만들기 전 early 의 owner: $($K get pod early -n $NS -o jsonpath='{.metadata.ownerReferences[0].kind}')(없음)"
rs adopt ""
sleep 6
pods app=adopt
echo "  RS 이벤트:"; $K get events -n $NS --field-selector involvedObject.name=adopt -o custom-columns='    REASON:.reason,MSG:.message' --no-headers

echo; echo "## 2. 어느 노드에도 없는 라벨을 nodeSelector 로 준 replicas=2 ReplicaSet (15초 뒤)"
rs pend "nodeSelector: {blog60/none: \"true\"}"
sleep 15
pods app=pend
echo "  RS status: replicas=$($K get rs pend -n $NS -o jsonpath='{.status.replicas}') readyReplicas=$($K get rs pend -n $NS -o jsonpath='{.status.readyReplicas}') availableReplicas=$($K get rs pend -n $NS -o jsonpath='{.status.availableReplicas}')(빈칸=0)"
echo "  RS 이벤트:"; $K get events -n $NS --field-selector involvedObject.name=pend -o custom-columns='    REASON:.reason,MSG:.message' --no-headers
P=$($K get pod -n $NS -l app=pend -o jsonpath='{.items[0].metadata.name}')
echo "  파드 이벤트($P):"; $K get events -n $NS --field-selector involvedObject.name=$P -o custom-columns='    REASON:.reason,MSG:.message' --no-headers | cut -c1-160

echo; echo "## 3. adopt 를 Service 로 노출한 뒤 파드 하나의 라벨을 app=debug 로 바꾸면"
$K expose rs adopt -n $NS --port=80 >/dev/null; sleep 3
eps(){ $K get endpointslice -n $NS -l kubernetes.io/service-name=adopt -o jsonpath='{range .items[*].endpoints[*]}{.targetRef.name} {end}'; }
echo "  바꾸기 전 Service 대상: $(eps)"
$K label pod early -n $NS app=debug --overwrite >/dev/null; sleep 5
echo "  early 의 라벨을 바꾼 뒤 Service 대상: $(eps)"
pods 'app in (adopt,debug)'

echo; echo "## 4. Deployment 템플릿에 restartPolicy: Never 를 쓰면 (dry-run=server)"
cat <<'Y' | $K apply -n $NS --dry-run=server -f - 2>&1 | sed 's/^/  /'
apiVersion: apps/v1
kind: Deployment
metadata: {name: once}
spec:
  selector: {matchLabels: {app: once}}
  template:
    metadata: {labels: {app: once}}
    spec:
      restartPolicy: Never
      containers: [{name: c, image: busybox:1.37, command: ["sh", "-c", "echo done"]}]
Y
$K delete ns $NS --wait=false >/dev/null
