#!/usr/bin/env bash
# mysql CLI 로 두 세션을 동시에 돌려 1205 / 1213 의 롤백 범위를 본다.
# 사용: scripts/cli.sh <s1|s2|s3|s4|s5|s6>   (compose 스택이 떠 있어야 한다)
#  s1  1205, 기본값            : 그 문장만 롤백, 트랜잭션은 열린 채, COMMIT 하면 앞 문장이 남는다
#  s2  innodb_rollback_on_timeout 을 실행 중에 켜 보기 (읽기 전용 변수)
#  s3  1205, rollback_on_timeout=ON 서버 : 트랜잭션 전체 롤백
#  s4  1213                    : 트랜잭션 전체 롤백, 다음 문장은 autocommit 으로 실행된다
#  s5  교착 감지 OFF, 기본값    : 교착이 1205 로 보이고, 둘 다 timeout
#  s6  교착 감지 OFF, rollback_on_timeout=ON : 한쪽 timeout 이 전체를 풀어 상대가 진행
#  s7  교착 감지 OFF, 기본값, 1205 를 받은 쪽이 바로 끝내지 않고 4초 더 머문다 : 잠금이 안 풀려 상대도 1205
set -uo pipefail
cd "$(dirname "$0")/.."

q() {  # q <service> : 표준입력의 SQL 을 한 세션으로 실행. 오류가 나도 다음 문장을 계속(--force)
  docker compose exec -T "$1" mysql -ulab -plab -D lab --force --unbuffered -t -vv 2>&1 | grep -v 'Using a password'
}
root() { docker compose exec -T "$1" mysql -uroot -plabroot -D lab -t 2>&1 | grep -v 'Using a password'; }

reset() {
  root "$1" <<'SQL'
DELETE FROM note; UPDATE item SET v = 0;
SQL
}

TRX="SELECT COUNT(*) AS open_trx, IFNULL(MAX(trx_rows_modified),0) AS rows_modified FROM information_schema.innodb_trx WHERE trx_mysql_thread_id = CONNECTION_ID();"
DLK="SELECT name, count FROM information_schema.innodb_metrics WHERE name = 'lock_deadlocks';"

# 한 행을 N 초 쥐고 있는 세션
holder() {  # holder <service> <seconds>
  q "$1" <<SQL
BEGIN;
UPDATE item SET v = v + 100 WHERE id = 1;
SELECT SLEEP($2) AS holding;
ROLLBACK;
SQL
}

# 1205 를 맞는 세션: 앞 문장(INSERT) → 막히는 UPDATE → 트랜잭션 상태 → COMMIT → 남은 행
victim_1205() {
  q "$1" <<SQL
SET SESSION innodb_lock_wait_timeout = 2;
BEGIN;
INSERT INTO note(who) VALUES ('B-before');
UPDATE item SET v = v + 1 WHERE id = 1;
$TRX
COMMIT;
SELECT who FROM note ORDER BY id;
SQL
}

case "${1:-}" in
s1|s3)
  svc=mysql; [ "$1" = s3 ] && svc=mysql-rbt
  reset $svc >/dev/null
  echo "### $1 server=$svc  rollback_on_timeout=$(root $svc <<<'SELECT @@innodb_rollback_on_timeout' | sed -n 4p | tr -d '| ')"
  holder $svc 5 > out/$1-A.txt &
  sleep 1
  echo "--- session B ---"
  victim_1205 $svc
  wait
  ;;
s2)
  echo "### s2 try to turn on innodb_rollback_on_timeout at runtime"
  root mysql <<'SQL'
SELECT @@innodb_rollback_on_timeout;
SET GLOBAL innodb_rollback_on_timeout = ON;
SQL
  ;;
s4)
  reset mysql >/dev/null
  echo "### s4 deadlock detect=$(root mysql <<<'SELECT @@innodb_deadlock_detect' | sed -n 4p | tr -d '| ')"
  root mysql <<<"$DLK"
  # A: 기록 3건(무거운 쪽) → item 1 → 2초 뒤 item 2
  q mysql > out/s4-A.txt <<SQL &
BEGIN;
INSERT INTO note(who) VALUES ('A-before'),('A-before'),('A-before');
UPDATE item SET v = v + 1 WHERE id = 1;
SELECT SLEEP(2) AS a_wait;
UPDATE item SET v = v + 1 WHERE id = 2;
COMMIT;
SQL
  sleep 1
  echo "--- session B ---"
  q mysql <<SQL
BEGIN;
INSERT INTO note(who) VALUES ('B-before');
UPDATE item SET v = v + 1 WHERE id = 2;
SELECT SLEEP(2) AS b_wait;
UPDATE item SET v = v + 1 WHERE id = 1;
$TRX
INSERT INTO note(who) VALUES ('B-after');
ROLLBACK;
SELECT who FROM note ORDER BY id;
SQL
  wait
  echo "--- session A ---"; cat out/s4-A.txt
  root mysql <<<"$DLK"
  ;;
s5|s6|s7)
  svc=mysql; [ "$1" = s6 ] && svc=mysql-rbt
  ATAIL="COMMIT;"; [ "$1" = s7 ] && ATAIL="SELECT SLEEP(4) AS a_still_open; ROLLBACK;"
  reset $svc >/dev/null
  root $svc <<<"SET GLOBAL innodb_deadlock_detect = OFF; SET GLOBAL innodb_lock_wait_timeout = 3;"
  echo "### $1 server=$svc deadlock_detect=$(root $svc <<<'SELECT @@innodb_deadlock_detect' | sed -n 4p | tr -d '| ') rollback_on_timeout=$(root $svc <<<'SELECT @@innodb_rollback_on_timeout' | sed -n 4p | tr -d '| ') lock_wait_timeout=3"
  root $svc <<<"$DLK"
  start=$(date +%s)
  q $svc > out/$1-A.txt <<SQL &
BEGIN;
INSERT INTO note(who) VALUES ('A-before'),('A-before'),('A-before');
UPDATE item SET v = v + 1 WHERE id = 1;
SELECT SLEEP(2) AS a_wait;
UPDATE item SET v = v + 1 WHERE id = 2;
$TRX
$ATAIL
SQL
  sleep 1
  q $svc > out/$1-B.txt <<SQL
BEGIN;
INSERT INTO note(who) VALUES ('B-before');
UPDATE item SET v = v + 1 WHERE id = 2;
SELECT SLEEP(2) AS b_wait;
UPDATE item SET v = v + 1 WHERE id = 1;
$TRX
COMMIT;
SQL
  wait
  echo "both sessions finished after $(( $(date +%s) - start ))s"
  echo "--- session A ---"; cat out/$1-A.txt
  echo "--- session B ---"; cat out/$1-B.txt
  echo "--- after ---"
  root $svc <<<"SELECT who, COUNT(*) AS n FROM note GROUP BY who ORDER BY who; SELECT * FROM item;"
  root $svc <<<"$DLK"
  root $svc <<<"SET GLOBAL innodb_deadlock_detect = ON; SET GLOBAL innodb_lock_wait_timeout = 50;"
  ;;
*) echo "usage: $0 s1|s2|s3|s4|s5|s6|s7"; exit 2 ;;
esac
