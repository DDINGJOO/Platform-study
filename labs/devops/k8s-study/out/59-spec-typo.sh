#!/usr/bin/env bash
# spec 에 오타가 있으면 어떻게 되나: kubectl 기본 검증(strict) vs --validate=false (Mac 에서 실행)
cd "$(dirname "$0")/../.."
K="./lab kubectl"
echo "# 08 spec 오타 검증 ($(date '+%F %T %Z'))"
Y='apiVersion: v1
kind: Pod
metadata: {name: typo, namespace: ch05}
spec:
  containers:
  - name: c
    image: nginx:1.27-alpine
    imagePullPolicyy: Always'
echo; echo "## 기본(--validate=true → 서버 strict 검증), 필드 이름 오타 imagePullPolicyy"
echo "$Y" | $K apply --dry-run=server -f - 2>&1 | sed 's/^/  /'
echo; echo "## --validate=false"
echo "$Y" | $K apply --dry-run=server --validate=false -f - 2>&1 | sed 's/^/  /'
echo; echo "## 값이 틀린 경우(restartPolicy: Sometimes)는 필드 검증이 아니라 API 검증에서 걸린다"
echo "$Y" | sed 's/imagePullPolicyy: Always/imagePullPolicy: Always/' | sed 's/^spec:/spec:\n  restartPolicy: Sometimes/' | $K apply --dry-run=server -f - 2>&1 | sed 's/^/  /'
