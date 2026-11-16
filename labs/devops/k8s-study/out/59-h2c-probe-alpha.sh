#!/usr/bin/env bash
# 1.37 의 httpGet.protocol(H2C 프로브)은 알파·기본 꺼짐: 스키마엔 있지만 값을 넣으면 어떻게 되나 (Mac 에서 실행)
cd "$(dirname "$0")/../.."
K="./lab kubectl"
echo "# 17 httpGet.protocol 알파 필드 ($(date '+%F %T %Z'))"
echo "  kube-apiserver --feature-gates: $($K -n kube-system get pod kube-apiserver-k8s-master -o jsonpath='{.spec.containers[0].command}' | tr ',' '\n' | grep -c feature-gates)개 지정"
echo; echo "## protocol: HTTP2 를 넣고 server dry-run, 저장될 객체의 readinessProbe.httpGet"
cat <<'Y' | $K apply --dry-run=server -o jsonpath='  {.spec.containers[0].readinessProbe.httpGet}{"\n"}' -f - 2>&1
apiVersion: v1
kind: Pod
metadata: {name: h2c, namespace: ch05}
spec:
  containers:
  - name: c
    image: nginx:1.27-alpine
    readinessProbe:
      httpGet: {path: /, port: 80, protocol: HTTP2}
Y
