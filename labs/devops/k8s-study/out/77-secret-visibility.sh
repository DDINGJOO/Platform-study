#!/usr/bin/env bash
# 비밀번호를 env value·secretKeyRef·envFrom·볼륨으로 넣을 때 describe·get·컨테이너 안·권한별로 무엇이 보이나 (Mac 에서 실행)
# 실습 저장소 루트에서 실행한다. 네임스페이스 blog-77 만 만들고 지운다. 비밀번호는 실습용 값이다.
K="./lab kubectl"; NS=blog-77
echo "# 77 비밀번호는 어디에 보이나 ($(date '+%F %T %Z'), kubectl $($K version -o json 2>/dev/null | python3 -c 'import json,sys;print(json.load(sys.stdin)["serverVersion"]["gitVersion"])'))"
$K create ns $NS >/dev/null
$K create secret generic db-cred -n $NS --from-literal=password='k8spass#' >/dev/null
cat <<'Y' | $K apply -n $NS -f - >/dev/null
apiVersion: v1
kind: Pod
metadata: {name: env-value}
spec:
  containers:
  - name: c
    image: busybox:1.37
    command: [sleep, "3600"]
    env: [{name: DB_PASSWORD, value: "k8spass#"}]
---
apiVersion: v1
kind: Pod
metadata: {name: env-ref}
spec:
  containers:
  - name: c
    image: busybox:1.37
    command: [sleep, "3600"]
    env:
    - name: DB_PASSWORD
      valueFrom: {secretKeyRef: {name: db-cred, key: password}}
---
apiVersion: v1
kind: Pod
metadata: {name: env-from}
spec:
  containers:
  - name: c
    image: busybox:1.37
    command: [sleep, "3600"]
    envFrom: [{prefix: DB_, secretRef: {name: db-cred}}]
---
apiVersion: v1
kind: Pod
metadata: {name: vol}
spec:
  containers:
  - name: c
    image: busybox:1.37
    command: [sleep, "3600"]
    volumeMounts: [{name: cred, mountPath: /etc/db, readOnly: true}]
  volumes:
  - name: cred
    secret: {secretName: db-cred}
Y
$K wait pod/env-value pod/env-ref pod/env-from pod/vol -n $NS --for=condition=Ready --timeout=120s >/dev/null

echo; echo "## 1. kubectl describe pod 의 컨테이너 칸 (Environment 부터 Mounts 까지)"
for p in env-value env-ref env-from vol; do
  echo "  [$p]"
  $K describe pod $p -n $NS | sed -n '/^    Environment/,/^Conditions:/p' | grep -v -E '^Conditions:|kube-api-access' | sed 's/^/  /'
done
echo "  [vol] Volumes 칸"
$K describe pod vol -n $NS | sed -n '/^Volumes:/,/^QoS/p' | grep -A3 '^  cred:' | sed 's/^/  /'

echo; echo "## 2. kubectl get pod -o jsonpath (spec 에 저장된 것)"
echo "  env-value  env:     $($K get pod env-value -n $NS -o jsonpath='{.spec.containers[0].env}')"
echo "  env-ref    env:     $($K get pod env-ref -n $NS -o jsonpath='{.spec.containers[0].env}')"
echo "  env-from   envFrom: $($K get pod env-from -n $NS -o jsonpath='{.spec.containers[0].envFrom}')"
echo "  vol        volumes: $($K get pod vol -n $NS -o jsonpath='{.spec.volumes[?(@.name=="cred")]}')"
echo "  env-value 의 last-applied-configuration 주석에 비밀번호 문자열이 나온 횟수: $($K get pod env-value -n $NS -o jsonpath='{.metadata.annotations.kubectl\.kubernetes\.io/last-applied-configuration}' | grep -o 'k8spass#' | wc -l | tr -d ' ')"

echo; echo "## 3. 컨테이너 안에서 (kubectl exec)"
echo "  env-value: $($K exec env-value -n $NS -- env | grep DB_)"
echo "  env-ref:   $($K exec env-ref -n $NS -- env | grep DB_)"
echo "  env-from:  $($K exec env-from -n $NS -- env | grep DB_)"
echo "  vol: env 에 DB_ 줄 수=$($K exec vol -n $NS -- env | grep -c DB_)  cat /etc/db/password=$($K exec vol -n $NS -- cat /etc/db/password)"
$K exec vol -n $NS -- ls -la /etc/db | sed 's/^/    /'
$K exec vol -n $NS -- sh -c 'mount | grep /etc/db' | sed 's/^/    /'

echo; echo "## 4. Secret 객체 자체"
$K describe secret db-cred -n $NS | sed -n '/^Data/,$p' | sed 's/^/  /'
echo "  get -o jsonpath data.password = $($K get secret db-cred -n $NS -o jsonpath='{.data.password}') → base64 -d → $($K get secret db-cred -n $NS -o jsonpath='{.data.password}' | base64 -d)"
cat <<'Y' | $K apply -n $NS -f - >/dev/null
apiVersion: v1
kind: Secret
metadata: {name: db-cred-applied}
stringData: {password: "k8spass#"}
Y
echo "  stringData 로 kubectl apply 한 Secret: data.password=$($K get secret db-cred-applied -n $NS -o jsonpath='{.data.password}'), last-applied-configuration 주석:"
echo "    $($K get secret db-cred-applied -n $NS -o jsonpath='{.metadata.annotations.kubectl\.kubernetes\.io/last-applied-configuration}')"

echo; echo "## 5. pods 만 읽는 ServiceAccount (Role: pods·events get/list, secrets 없음)"
$K create sa pod-reader -n $NS >/dev/null
$K create role pod-reader -n $NS --verb=get,list --resource=pods,events >/dev/null
$K create rolebinding pod-reader -n $NS --role=pod-reader --serviceaccount=$NS:pod-reader >/dev/null
AS="--as=system:serviceaccount:$NS:pod-reader"
for r in "get pods" "get secrets" "create pods/exec"; do echo "  can-i $r: $($K auth can-i $r -n $NS $AS)"; done
echo "  get pod env-value env (pod-reader): $($K get pod env-value -n $NS $AS -o jsonpath='{.spec.containers[0].env}' 2>&1)"
echo "  describe pod env-ref (pod-reader): $($K describe pod env-ref -n $NS $AS 2>&1 | grep 'DB_PASSWORD' | sed 's/^ *//')"
echo "  get secret db-cred (pod-reader): $($K get secret db-cred -n $NS $AS 2>&1)"

echo; echo "## 6. 파드를 만들 수 있는 ServiceAccount (Role: pods create·get·list, pods/log get, secrets 없음)"
$K create sa pod-maker -n $NS >/dev/null
$K create role pod-maker -n $NS --verb=create,get,list --resource=pods >/dev/null
$K create role pod-log -n $NS --verb=get --resource=pods/log >/dev/null
$K create rolebinding pod-maker -n $NS --role=pod-maker --serviceaccount=$NS:pod-maker >/dev/null
$K create rolebinding pod-log -n $NS --role=pod-log --serviceaccount=$NS:pod-maker >/dev/null
AS="--as=system:serviceaccount:$NS:pod-maker"
echo "  can-i get secrets (pod-maker): $($K auth can-i get secrets -n $NS $AS)"
cat <<'Y' | $K create -n $NS $AS -f - 2>&1 | sed 's/^/  /'
apiVersion: v1
kind: Pod
metadata: {name: peek}
spec:
  restartPolicy: Never
  containers:
  - name: c
    image: busybox:1.37
    command: [sh, -c, 'echo "DB_PASSWORD=$DB_PASSWORD"']
    env:
    - name: DB_PASSWORD
      valueFrom: {secretKeyRef: {name: db-cred, key: password}}
Y
for i in $(seq 1 30); do [ "$($K get pod peek -n $NS -o jsonpath='{.status.phase}')" = Succeeded ] && break; sleep 1; done
echo "  peek phase=$($K get pod peek -n $NS -o jsonpath='{.status.phase}'), logs (pod-maker): $($K logs peek -n $NS $AS 2>&1)"

$K delete ns $NS --wait=false >/dev/null
echo; echo "(네임스페이스 $NS 삭제 요청)"
