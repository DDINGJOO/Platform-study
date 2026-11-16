#!/usr/bin/env bash
# 오브젝트 관계도의 화살표를 클러스터에서 하나씩 확인 (Mac 에서 실행)
cd "$(dirname "$0")/../.."
K="./lab kubectl"; NS=ch05
echo "# 05 오브젝트 관계도 화살표 확인 ($(date '+%F %T %Z'))"

echo; echo "## 1. Pod → Volume: Volume 은 따로 있는 오브젝트인가"
echo "  api-resources 중 이름에 volume 이 들어간 종류(KIND):"
$K api-resources --no-headers | grep -i volume | awk '{print "    "$NF}'
echo "  파드 스펙 안의 필드: $($K explain pod.spec.volumes | grep '^FIELD:')"

echo; echo "## 2. Secret → ConfigMap (Extends?): 두 종류의 최상위 필드"
for k in configmap secret; do
  echo "  $k ($($K explain $k | sed -n 's/^VERSION: *//p')): $($K explain $k | sed -n '/^FIELDS:/,$p' | grep -E '^  [a-zA-Z]' | awk '{print $1}' | paste -sd' ' -)"
done

echo; echo "## 3. Deployment → ReplicaSet → Pod: ownerReferences"
cat <<'Y' | $K apply -n $NS -f - >/dev/null
apiVersion: apps/v1
kind: Deployment
metadata: {name: obj-demo}
spec:
  replicas: 2
  selector: {matchLabels: {app: obj-demo}}
  template:
    metadata: {labels: {app: obj-demo}}
    spec:
      containers:
      - name: web
        image: nginx:1.27-alpine
        resources: {requests: {cpu: 50m}}
Y
$K expose deploy obj-demo -n $NS --port=80 >/dev/null
$K rollout status deploy/obj-demo -n $NS --timeout=120s >/dev/null
$K get rs -n $NS -l app=obj-demo -o jsonpath='{range .items[*]}  ReplicaSet {.metadata.name}  owner={.metadata.ownerReferences[0].kind}/{.metadata.ownerReferences[0].name}  selector={.spec.selector.matchLabels}{"\n"}{end}'
$K get pod -n $NS -l app=obj-demo -o jsonpath='{range .items[*]}  Pod {.metadata.name}  owner={.metadata.ownerReferences[0].kind}/{.metadata.ownerReferences[0].name}  ip={.status.podIP}  labels={.metadata.labels}{"\n"}{end}'

echo; echo "## 4. Service → Pod: 사이에 있는 EndpointSlice"
echo "  Service selector: $($K get svc obj-demo -n $NS -o jsonpath='{.spec.selector}')  clusterIP: $($K get svc obj-demo -n $NS -o jsonpath='{.spec.clusterIP}')"
$K get endpointslice -n $NS -l kubernetes.io/service-name=obj-demo -o jsonpath='{range .items[*]}  EndpointSlice {.metadata.name}  owner={.metadata.ownerReferences[0].kind}/{.metadata.ownerReferences[0].name}  managed-by={.metadata.labels.endpointslice\.kubernetes\.io/managed-by}{"\n"}{range .endpoints[*]}    address={.addresses[0]}  pod={.targetRef.name}  ready={.conditions.ready}{"\n"}{end}{end}'

echo; echo "## 5. HPA → Deployment: 무엇을 바꾸고, 무엇이 필요한가"
$K autoscale deploy obj-demo -n $NS --cpu-percent=50 --min=1 --max=3 2>&1 | sed 's/^/  autoscale: /'
echo "  scaleTargetRef: $($K get hpa obj-demo -n $NS -o jsonpath='{.spec.scaleTargetRef}')"
echo "  Deployment 의 scale 하위 리소스: $($K get --raw /apis/apps/v1/namespaces/$NS/deployments/obj-demo/scale | head -c 300)"
echo "  metrics API 등록 여부(apiservice): $($K get apiservice v1beta1.metrics.k8s.io --no-headers 2>&1 | head -1)"
sleep 45
echo "  45초 뒤 HPA conditions:"
$K get hpa obj-demo -n $NS -o jsonpath='{range .status.conditions[*]}    {.type}={.status} {.reason}: {.message}{"\n"}{end}'

echo; echo "## 6. Role → Pod (Controls operations?): 파드의 ServiceAccount 권한"
SA=$($K get pod -n $NS -l app=obj-demo -o jsonpath='{.items[0].spec.serviceAccountName}')
echo "  파드의 serviceAccountName: $SA"
echo "  Role 없이  can-i list pods (as SA): $($K auth can-i list pods -n $NS --as=system:serviceaccount:$NS:$SA)"
$K create role pod-reader -n $NS --verb=get,list --resource=pods >/dev/null
$K create rolebinding pod-reader -n $NS --role=pod-reader --serviceaccount=$NS:$SA >/dev/null
echo "  Role+RoleBinding 뒤 can-i list pods (as SA): $($K auth can-i list pods -n $NS --as=system:serviceaccount:$NS:$SA)"
echo "  같은 SA 로 can-i delete pods: $($K auth can-i delete pods -n $NS --as=system:serviceaccount:$NS:$SA)"

echo; echo "## 7. StorageClass → PV (Creates?): 누가 PV 를 만드나"
$K get sc -o custom-columns='  NAME:.metadata.name,PROVISIONER:.provisioner,BINDING:.volumeBindingMode' 2>&1
$K get pv -o custom-columns='  PV:.metadata.name,STORAGECLASS:.spec.storageClassName,CLAIM:.spec.claimRef.name' 2>&1

echo; echo "## 8. Ingress → Service: 규칙만 만들면 트래픽이 가나"
echo "  IngressClass: $($K get ingressclass --no-headers 2>&1 | head -3)"
$K create ingress obj-demo -n $NS --rule="demo.local/*=obj-demo:80" >/dev/null
sleep 10
$K get ingress obj-demo -n $NS -o custom-columns='  NAME:.metadata.name,CLASS:.spec.ingressClassName,HOSTS:.spec.rules[0].host,ADDRESS:.status.loadBalancer.ingress[0].ip'

$K delete ingress,hpa,svc,deploy obj-demo -n $NS >/dev/null
$K delete role,rolebinding pod-reader -n $NS >/dev/null
