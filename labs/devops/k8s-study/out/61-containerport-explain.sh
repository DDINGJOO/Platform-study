#!/usr/bin/env bash
# containerPort 는 무엇을 막고 무엇을 막지 않나: API 서버가 내려 주는 필드 설명 (Mac 에서 실행)
# 실습 저장소 루트에서 실행한다(./lab kubectl). 조회만 한다.
K="./lab kubectl"
echo "# 61 containerPort 필드 설명 ($(date '+%F %T %Z'), 서버 $($K version -o json 2>/dev/null | grep -m1 gitVersion | tail -1 | tr -d ' ",' | cut -d: -f2))"
echo; echo "## kubectl explain pod.spec.containers.ports"
$K explain pod.spec.containers.ports | sed 's/^/  /'
