#!/usr/bin/env bash
# 42편용 조회 스크립트(읽기만). 실습 저장소 루트(./lab 이 있는 곳)에서 실행한다.
# 컨트롤러 매니저가 쓰는 신원: 인포머용 kubeconfig 인증서, 컨트롤러별 ServiceAccount 와 ClusterRole, 권한 차이,
# 그리고 Service 의 ClusterIP 를 기록하는 ServiceCIDR·IPAddress 객체를 본다. 아무것도 만들거나 고치지 않는다.
K="./lab kubectl"; ts(){ date '+%T'; }
echo "# 컨트롤러 매니저가 쓰는 신원과 Service IP 기록 ($(date '+%F %T %Z'), Mac 에서 ./lab 으로 조회만)"

echo; echo "## 1. 인포머와 리더 선출에 쓰는 신원: controller-manager.conf 의 클라이언트 인증서"
./lab ssh master -- sudo bash -s <<'R'
grep client-certificate-data /etc/kubernetes/controller-manager.conf | awk '{print $2}' | base64 -d | openssl x509 -noout -subject -issuer | sed 's/^/  /'
R

echo; echo "## 2. kube-system 의 ServiceAccount"
ALL=$($K -n kube-system get sa -o name | sed 's#serviceaccount/##')
echo "  전체 $(echo "$ALL" | wc -l | tr -d ' ')개, 이름이 -controller 로 끝나는 것 $(echo "$ALL" | grep -c -- '-controller$')개"
echo "  -controller 로 끝나지 않는 것:"
echo "$ALL" | grep -v -- '-controller$' | paste -sd' ' - | fold -w 150 -s | sed 's/^/    /'

echo; echo "## 3. system:controller: 로 시작하는 ClusterRole"
CR=$($K get clusterrole -o name | sed 's#clusterrole.rbac.authorization.k8s.io/##' | grep '^system:controller:')
echo "  $(echo "$CR" | wc -l | tr -d ' ')개"
echo "$CR" | sed 's/system:controller://' | paste -sd' ' - | fold -w 150 -s | sed 's/^/    /'

echo; echo "## 4. deployment-controller 와 replicaset-controller 의 규칙 (파드·ReplicaSet 관련만)"
for c in deployment-controller replicaset-controller; do
  echo "  [system:controller:$c]"
  $K get clusterrole system:controller:$c -o json | python3 -c '
import json,sys
for r in json.load(sys.stdin)["rules"]:
    res=[x for x in r.get("resources",[]) if x.startswith("pod") or x.startswith("replicaset") or x.startswith("deployment")]
    if res: print("    %-45s %s" % (",".join(res), ",".join(r["verbs"])))'
done

echo; echo "## 5. kubectl auth can-i 로 본 권한 차이 (--as 로 ServiceAccount 흉내, 읽기 전용 검사)"
for c in deployment-controller replicaset-controller; do
  for q in "create pods" "update replicasets.apps" "update deployments.apps"; do
    echo "  $c  $q: $($K auth can-i $q -n default --as=system:serviceaccount:kube-system:$c 2>&1)"
  done
done

echo; echo "## 6. Service 의 ClusterIP 는 어디에 기록되나 (ServiceCIDR, IPAddress)"
$K get servicecidrs 2>&1 | sed 's/^/  /'
echo "  IPAddress 객체 수: $($K get ipaddresses --no-headers 2>/dev/null | wc -l | tr -d ' '), Service 수: $($K get svc -A --no-headers 2>/dev/null | wc -l | tr -d ' '), 그중 clusterIP None(headless): $($K get svc -A -o jsonpath='{range .items[*]}{.spec.clusterIP}{"\n"}{end}' | grep -c '^None$')"
$K get ipaddress 10.96.0.1 -o jsonpath='  10.96.0.1 → parentRef {.spec.parentRef.resource}/{.spec.parentRef.namespace}/{.spec.parentRef.name}{"\n"}' 2>&1
$K get ipaddress 10.96.0.1 -o jsonpath='  managedBy 라벨: {.metadata.labels.ipaddress\.kubernetes\.io/managed-by}{"\n"}' 2>&1

echo; echo "## 7. default 네임스페이스 EndpointSlice 를 관리하는 쪽 (endpointslice.kubernetes.io/managed-by 라벨)"
$K -n default get endpointslices -o jsonpath='{range .items[*]}  {.metadata.name}  service={.metadata.labels.kubernetes\.io/service-name}  managed-by={.metadata.labels.endpointslice\.kubernetes\.io/managed-by}{"\n"}{end}' 2>&1
