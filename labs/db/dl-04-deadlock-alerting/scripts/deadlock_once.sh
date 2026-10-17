#!/usr/bin/env bash
# 두 세션이 행 1, 2 를 서로 반대 순서로 잠가 교착을 한 번 만든다.
# 출력: 두 세션 각각의 결과 줄. 한쪽은 정상 종료, 다른 쪽은 ERROR 1213 (교착 감지가 꺼져 있으면 1205).
# 앱 예외 수는 이 출력의 ERROR 줄을 센 값이다.
set -u
WAIT="${LOCK_WAIT:-50}"
A="SET SESSION innodb_lock_wait_timeout=$WAIT; START TRANSACTION; UPDATE t SET v=v+1 WHERE id=1; DO SLEEP(0.6); UPDATE t SET v=v+1 WHERE id=2; COMMIT;"
B="SET SESSION innodb_lock_wait_timeout=$WAIT; START TRANSACTION; UPDATE t SET v=v+1 WHERE id=2; DO SLEEP(0.6); UPDATE t SET v=v+1 WHERE id=1; COMMIT;"
run() { docker exec -i dl04-mysql mysql -uroot -plabroot lab -e "$2" 2>&1 | grep -v 'Using a password' | sed "s/^/$1 /"; echo "$1 exit"; }
run A "$A" &
sleep 0.2
run B "$B" &
wait
