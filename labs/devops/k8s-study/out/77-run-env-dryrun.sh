#!/usr/bin/env bash
# 명령형 kubectl run --env 로 뼈대를 뽑아도 비밀번호가 spec 의 env value 로 들어가나 (Mac 에서 실행, --dry-run=client 라 클러스터에 아무것도 만들지 않는다)
# 실습 저장소 루트에서 실행한다. 비밀번호는 실습용 값이다.
K="./lab kubectl"
echo "# 77 kubectl run --env 의 뼈대 ($(date '+%F %T %Z'))"
echo; echo "## kubectl run db --image=mysql:8.4 --port=3306 --env=MYSQL_ROOT_PASSWORD='k8spass#' --dry-run=client -o yaml"
$K run db --image=mysql:8.4 --port=3306 --env=MYSQL_ROOT_PASSWORD='k8spass#' --dry-run=client -o yaml | sed 's/^/  /'
