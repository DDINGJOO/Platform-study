#!/usr/bin/env bash
# nginx:1.27-alpine 이미지의 /bin/sh 가 무엇인지(busybox 인지) 본다 (Mac 에서 실행)
# 실습 저장소 루트에서 실행한다. 네임스페이스 blog-65 만 쓰고 끝나면 지운다.
K="./lab kubectl"; NS=blog-65
$K create ns $NS >/dev/null
$K -n $NS run shcheck --image=nginx:1.27-alpine --restart=Never --command -- sh -c 'ls -l /bin/sh; readlink -f /bin/sh' >/dev/null
$K -n $NS wait --for=jsonpath='{.status.phase}'=Succeeded pod/shcheck --timeout=60s >/dev/null
echo "# nginx:1.27-alpine 의 /bin/sh ($(date '+%F %T %Z'))"
$K -n $NS logs shcheck | sed 's/^/  /'
$K delete ns $NS --wait=true >/dev/null 2>&1
echo "# 네임스페이스 $NS 삭제"
