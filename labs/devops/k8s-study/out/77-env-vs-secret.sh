#!/usr/bin/env bash
# 비밀번호를 env value 로 넣을 때와 Secret(secretKeyRef)으로 넣을 때 kubectl describe·get -o yaml·컨테이너 안에서 무엇이 보이나 (Mac 에서 실행)
cd "$(dirname "$0")/../.."
K="./lab kubectl"; NS=ch05
echo "# 24 env value vs secretKeyRef ($(date '+%F %T %Z'))"
$K create secret generic mysql-root -n $NS --from-literal=password='k8spass#' >/dev/null
cat <<'Y' | $K apply -n $NS -f - >/dev/null
apiVersion: v1
kind: Pod
metadata: {name: env-plain}
spec:
  containers:
  - {name: c, image: busybox:1.37, command: [sleep, "3600"], env: [{name: MYSQL_ROOT_PASSWORD, value: "k8spass#"}]}
---
apiVersion: v1
kind: Pod
metadata: {name: env-secret}
spec:
  containers:
  - name: c
    image: busybox:1.37
    command: [sleep, "3600"]
    env:
    - name: MYSQL_ROOT_PASSWORD
      valueFrom: {secretKeyRef: {name: mysql-root, key: password}}
Y
$K wait pod/env-plain pod/env-secret -n $NS --for=condition=Ready --timeout=60s >/dev/null
for p in env-plain env-secret; do
  echo; echo "## $p"
  echo "  kubectl describe (Environment):"; $K describe pod $p -n $NS | sed -n '/Environment:/,/Mounts:/p' | grep -v Mounts | sed 's/^/    /'
  echo "  kubectl get -o jsonpath env: $($K get pod $p -n $NS -o jsonpath='{.spec.containers[0].env}')"
  echo "  컨테이너 안 env: $($K exec $p -n $NS -- env | grep MYSQL_ROOT_PASSWORD)"
done
echo; echo "## Secret 자체는 base64 로 인코딩만 돼 있다 (암호화가 아님)"
echo "  data.password = $($K get secret mysql-root -n $NS -o jsonpath='{.data.password}') → $($K get secret mysql-root -n $NS -o jsonpath='{.data.password}' | base64 -d)"
echo; echo "## 기본 ServiceAccount 로 Secret 을 읽을 수 있나 / 파드는 읽을 수 있나"
echo "  can-i get secrets (default SA): $($K auth can-i get secrets -n $NS --as=system:serviceaccount:$NS:default)"
echo "  can-i get pods    (default SA): $($K auth can-i get pods -n $NS --as=system:serviceaccount:$NS:default)"
$K delete pod env-plain env-secret -n $NS --grace-period=1 --wait=false >/dev/null; $K delete secret mysql-root -n $NS >/dev/null
