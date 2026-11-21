#!/usr/bin/env bash
# Secret 을 만드는 방법(create, 클라이언트 apply, 서버 사이드 apply)마다 비밀번호 문자열이 객체의 어디에 남나 (Mac 에서 실행)
# 실습 저장소 루트에서 실행한다. 네임스페이스 blog-77 만 만들고 지운다. 비밀번호는 실습용 값이다.
K="./lab kubectl"; NS=blog-77
echo "# 77 Secret 을 만드는 방법과 last-applied 주석 ($(date '+%F %T %Z'))"
$K create ns $NS >/dev/null
$K create secret generic s-create -n $NS --from-literal=password='k8spass#' >/dev/null
printf 'apiVersion: v1\nkind: Secret\nmetadata: {name: s-apply}\nstringData: {password: "k8spass#"}\n' | $K apply -n $NS -f - >/dev/null
printf 'apiVersion: v1\nkind: Secret\nmetadata: {name: s-ssa}\nstringData: {password: "k8spass#"}\n' | $K apply --server-side -n $NS -f - >/dev/null
echo
printf '  %-9s %-28s %-32s %s\n' SECRET "last-applied 주석에 평문 횟수" "get -o yaml 전체에 평문 횟수" "managedFields 작성자(동작)"
for s in s-create s-apply s-ssa; do
  la=$($K get secret $s -n $NS -o jsonpath='{.metadata.annotations.kubectl\.kubernetes\.io/last-applied-configuration}' | grep -o 'k8spass#' | wc -l | tr -d ' ')
  all=$($K get secret $s -n $NS -o yaml | grep -o 'k8spass#' | wc -l | tr -d ' ')
  mf=$($K get secret $s -n $NS -o jsonpath='{range .metadata.managedFields[*]}{.manager}({.operation}) {end}')
  printf '  %-9s %-28s %-32s %s\n' $s "$la" "$all" "$mf"
done
echo
echo "  s-ssa 의 managedFields 가 기록한 칸: $($K get secret s-ssa -n $NS -o jsonpath='{.metadata.managedFields[0].fieldsV1}')"
echo "  kubectl describe secret s-apply 의 Annotations 줄: $($K describe secret s-apply -n $NS | grep '^Annotations')"
$K delete ns $NS --wait=false >/dev/null
echo; echo "(네임스페이스 $NS 삭제 요청)"
