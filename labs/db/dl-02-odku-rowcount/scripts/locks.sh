#!/usr/bin/env bash
# 트랜잭션 안에서 문장을 하나 실행하고, 같은 세션에서 performance_schema.data_locks 를 본다.
set -euo pipefail
cd "$(dirname "$0")/.."
q() { docker compose exec -T mysql mysql -uroot -plab lab -t 2>&1 | grep -v 'Using a password'; }
case_() {  # $1 격리수준 $2 설명 $3 문장
  echo "== [$1] $2"
  echo "   $3"
  q <<SQL
SET SESSION TRANSACTION ISOLATION LEVEL $1;
START TRANSACTION;
$3;
SELECT ROW_COUNT() AS row_count;
SELECT INDEX_NAME, LOCK_TYPE, LOCK_MODE, LOCK_STATUS, LOCK_DATA
  FROM performance_schema.data_locks
 WHERE OBJECT_NAME='lk' AND THREAD_ID=PS_CURRENT_THREAD_ID()
 ORDER BY LOCK_TYPE DESC, INDEX_NAME, LOCK_DATA;
ROLLBACK;
SQL
}
# lk: (10,'a'),(20,'c'),(30,'e'), PRIMARY(id) + uk_code(code)
for iso in 'REPEATABLE READ' 'READ COMMITTED'; do
  case_ "$iso" "ODKU 새 행"                  "INSERT INTO lk VALUES (25,'d',1) ON DUPLICATE KEY UPDATE v=v+1"
  case_ "$iso" "ODKU PK 중복(id=20)"          "INSERT INTO lk VALUES (20,'x',1) ON DUPLICATE KEY UPDATE v=v+1"
  case_ "$iso" "ODKU 보조 유니크 중복('c')"   "INSERT INTO lk VALUES (99,'c',1) ON DUPLICATE KEY UPDATE v=v+1"
  case_ "$iso" "ODKU 보조 유니크 중복, v=v"   "INSERT INTO lk VALUES (99,'c',1) ON DUPLICATE KEY UPDATE v=v"
  case_ "$iso" "INSERT IGNORE 보조 유니크 중복" "INSERT IGNORE INTO lk VALUES (99,'c',1)"
done
