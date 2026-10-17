#!/usr/bin/env bash
# 컨테이너 안의 mysql 클라이언트로 SQL 한 덩어리를 돌린다. 사용: sql.sh "<SQL>"
docker exec -i dl04-mysql mysql -uroot -plabroot --table lab -e "$1" 2>&1 | grep -v 'Using a password' || true
