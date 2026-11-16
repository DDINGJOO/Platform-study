#!/usr/bin/env bash
# kubectl 의 --validate 모드와 --dry-run=client·server 가 필드 이름 오타와 값 오류를 각각 어디서 잡나 (Mac 에서 실행)
# 실습 저장소 루트에서 실행한다. 네임스페이스 blog-59 만 만들고 지운다. 객체는 dry-run 이라 저장되지 않는다.
K="./lab kubectl"; NS=blog-59
echo "# 59 검증 모드와 dry-run ($(date '+%F %T %Z'))"
$K create ns $NS >/dev/null
TYPO="apiVersion: v1
kind: Pod
metadata: {name: typo, namespace: $NS}
spec:
  containers:
  - name: c
    image: nginx:1.27-alpine
    imagePullPolicyy: Always"
BADVAL="apiVersion: v1
kind: Pod
metadata: {name: badval, namespace: $NS}
spec:
  restartPolicy: Sometimes
  containers:
  - name: c
    image: nginx:1.27-alpine"

echo; echo "## 0. kubectl apply --help 의 --validate 설명"
$K apply --help | grep -A1 -- "--validate='strict'" | tail -1 | fold -s -w 110 | sed 's/^[[:space:]]*/  /'

for case in "필드 이름 오타(imagePullPolicyy)|TYPO" "값 오류(restartPolicy: Sometimes)|BADVAL"; do
  label=${case%%|*}; var=${case##*|}; Y=${!var}
  echo; echo "## $label"
  for opts in "--dry-run=client" "--dry-run=client --validate=false" "--dry-run=server" "--dry-run=server --validate=false"; do
    printf '  %-36s → ' "apply $opts"
    echo "$Y" | $K apply $opts -f - 2>&1 | tr '\n' ' ' | cut -c1-230; echo
  done
done

echo; echo "## 오타가 버려진 뒤 저장될 객체에 그 필드가 남나 (--dry-run=server --validate=false -o yaml 의 containers)"
echo "$TYPO" | $K apply --dry-run=server --validate=false -o jsonpath='  {.spec.containers[0]}{"\n"}' -f -

$K delete ns $NS --wait=false >/dev/null
