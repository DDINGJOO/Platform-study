#!/usr/bin/env bash
# 36편: --allow-privileged=true 가 필요한 파드. kube-system DaemonSet 컨테이너의 securityContext.privileged 를 본다. 조회만 한다.
# 실습 저장소 루트(./lab 이 있는 곳)에서 bash <이 스크립트> 로 실행
set -u
echo "# privileged 컨테이너를 쓰는 DaemonSet ($(date '+%F %T %Z'))"
./lab kubectl -n kube-system get ds -o jsonpath='{range .items[*]}  {.metadata.name}: {range .spec.template.spec.containers[*]}{.name} privileged={.securityContext.privileged} {end}{"\n"}{end}'
