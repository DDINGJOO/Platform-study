#!/usr/bin/env bash
# 한 바퀴: A(INSERT IGNORE 다음 FOR UPDATE) → B(두 행 반대 순서) → C(갭 잠금 표기)
# 사용: scripts/run.sh <바퀴 번호>   (MySQL 이 떠 있어야 한다. run_all.sh 가 띄운다)
set -u
cd "$(dirname "$0")/.."
R=${1:-1}
O=out/r$R; mkdir -p "$O"
M()  { docker compose exec -T -e MYSQL_PWD=labroot mysql mysql -uroot lab "$@"; }
MS() { M --force -t -vv; }                    # 세션용: 에러가 나도 다음 문장을 계속, 문장을 함께 찍는다

WAITS="
SELECT w.REQUESTING_THREAD_ID AS req_thr, rl.LOCK_MODE AS req_mode, rl.INDEX_NAME AS idx, rl.LOCK_DATA AS req_data,
       w.BLOCKING_THREAD_ID AS blk_thr, bl.LOCK_MODE AS blk_mode, bl.LOCK_DATA AS blk_data,
       rs.SQL_TEXT AS req_sql_now, bs.SQL_TEXT AS blk_sql_now
FROM performance_schema.data_lock_waits w
JOIN performance_schema.data_locks rl ON rl.ENGINE_LOCK_ID = w.REQUESTING_ENGINE_LOCK_ID
JOIN performance_schema.data_locks bl ON bl.ENGINE_LOCK_ID = w.BLOCKING_ENGINE_LOCK_ID
LEFT JOIN performance_schema.events_statements_current rs ON rs.THREAD_ID = w.REQUESTING_THREAD_ID
LEFT JOIN performance_schema.events_statements_current bs ON bs.THREAD_ID = w.BLOCKING_THREAD_ID
ORDER BY req_thr;"
LOCKS="
SELECT l.THREAD_ID AS thr, l.ENGINE_TRANSACTION_ID AS trx, x.trx_mysql_thread_id AS owner_conn,
       l.OBJECT_NAME AS tbl, l.INDEX_NAME AS idx, l.LOCK_TYPE AS type, l.LOCK_MODE AS mode, l.LOCK_STATUS AS status, l.LOCK_DATA AS data
FROM performance_schema.data_locks l
LEFT JOIN information_schema.INNODB_TRX x ON x.trx_id = l.ENGINE_TRANSACTION_ID
WHERE l.OBJECT_SCHEMA = 'lab' ORDER BY trx, type DESC, idx, data;"
# 잠금의 주인은 THREAD_ID 가 아니라 트랜잭션으로 찾는다 (INNODB_TRX.trx_mysql_thread_id = 접속 번호)
WAITS2="
SELECT rx.trx_mysql_thread_id AS req_conn, rl.LOCK_MODE AS req_mode, rl.LOCK_DATA AS data,
       bx.trx_mysql_thread_id AS blk_conn, bl.LOCK_MODE AS blk_mode,
       LEFT(rx.trx_query, 50) AS req_sql_now, LEFT(IFNULL(bx.trx_query, '(idle)'), 30) AS blk_sql_now
FROM performance_schema.data_lock_waits w
JOIN performance_schema.data_locks rl ON rl.ENGINE_LOCK_ID = w.REQUESTING_ENGINE_LOCK_ID
JOIN performance_schema.data_locks bl ON bl.ENGINE_LOCK_ID = w.BLOCKING_ENGINE_LOCK_ID
JOIN information_schema.INNODB_TRX rx ON rx.trx_id = w.REQUESTING_ENGINE_TRANSACTION_ID
JOIN information_schema.INNODB_TRX bx ON bx.trx_id = w.BLOCKING_ENGINE_TRANSACTION_ID
ORDER BY req_conn;"
# 막고 있는 스레드가 이 트랜잭션에서 실행한 문장들 (잠금을 잡은 문장은 여기서 찾는다)
HIST="
SELECT t.PROCESSLIST_ID AS conn, h.EVENT_ID AS ev, LEFT(h.SQL_TEXT, 60) AS sql_text
FROM performance_schema.events_statements_history h
JOIN performance_schema.threads t USING (THREAD_ID)
WHERE t.PROCESSLIST_ID IN (SELECT x.trx_mysql_thread_id FROM performance_schema.data_lock_waits w
                           JOIN information_schema.INNODB_TRX x ON x.trx_id = w.BLOCKING_ENGINE_TRANSACTION_ID)
  AND h.SQL_TEXT NOT LIKE 'select @@version%' AND h.SQL_TEXT NOT LIKE 'select \$\$%'
ORDER BY conn, ev;"
counters() {
  M -t -e "SELECT NAME, COUNT FROM information_schema.INNODB_METRICS WHERE NAME='lock_deadlocks';
           SHOW GLOBAL STATUS LIKE 'Innodb_deadlocks';"
}
latest() { M -N -r -e "SHOW ENGINE INNODB STATUS" | sed -n '/^LATEST DETECTED DEADLOCK/,/^TRANSACTIONS$/p'; }

M < sql/schema.sql
{
  M -e "SET GLOBAL log_error_verbosity = 2;"   # 바퀴마다 기본값으로 되돌린다
  echo "## 이 바퀴 시작 시점 값 (같은 컨테이너의 앞선 실행이 바꾼 값이 남아 있을 수 있다. 서버 기본값이 아니다)"; M -t -e "SELECT @@innodb_print_all_deadlocks, @@log_error_verbosity, @@innodb_deadlock_detect, @@transaction_isolation, @@version;"
  M -e "SET GLOBAL innodb_print_all_deadlocks = ON;"
  echo "## 켠 뒤"; M -t -e "SELECT @@innodb_print_all_deadlocks;"
  echo "## 카운터(시작)"; counters
} > "$O/00-settings.txt" 2>&1
LOGSTART=$(date -u +%Y-%m-%dT%H:%M:%SZ)

# ---------- A: 첫 방문 동시 요청 3개 ----------
SA="SELECT CONNECTION_ID() AS conn, PS_CURRENT_THREAD_ID() AS thr;
BEGIN;
INSERT IGNORE INTO visit (user_key) VALUES ('u-1');
SELECT NOW(6) AS after_insert_ignore;"
printf '%s\nSELECT SLEEP(4);\nSELECT * FROM visit WHERE user_key='"'u-1'"' FOR UPDATE;\nUPDATE visit SET cnt = cnt + 1 WHERE user_key='"'u-1'"';\nCOMMIT;\n' "$SA" | MS > "$O/A-s1.txt" 2>&1 &
P1=$!
sleep 1.5
for s in 2 3; do
  printf '%s\nSELECT * FROM visit WHERE user_key='"'u-1'"' FOR UPDATE;\nUPDATE visit SET cnt = cnt + 1 WHERE user_key='"'u-1'"';\nCOMMIT;\nSELECT NOW(6) AS done;\n' "$SA" | MS > "$O/A-s$s.txt" 2>&1 &
  eval P$s=$!
done
sleep 1.5
{ echo "## A 대기 중 data_locks"; M -t -e "$LOCKS"
  echo "## A 대기 중 data_lock_waits 조인 (THREAD_ID 기준, 함정)"; M -t -e "$WAITS"
  echo "## A 대기 중 data_lock_waits 조인 (트랜잭션 기준)"; M -t -e "$WAITS2"
  echo "## A 막는 스레드의 문장 이력"; M -t -e "$HIST"; } > "$O/A-waiting.txt" 2>&1
wait $P1 $P2 $P3
latest > "$O/A-status.txt"
M -t -e "SELECT * FROM visit;" > "$O/A-final.txt"

# ---------- B: 두 행을 서로 반대 순서로 ----------
# A 는 log_error_verbosity=2(기본값)로, B 는 3 으로 에러 로그에 남는 모양을 비교한다
M -e "SET GLOBAL log_error_verbosity = 3;"
printf '%s\n' "SELECT CONNECTION_ID() AS conn, PS_CURRENT_THREAD_ID() AS thr;" "BEGIN;" \
  "UPDATE acct SET bal = bal - 10 WHERE id = 1;" "SELECT SLEEP(1);" \
  "UPDATE acct SET bal = bal + 10 WHERE id = 2;" "COMMIT;" "SELECT NOW(6) AS done;" | MS > "$O/B-s1.txt" 2>&1 &
Q1=$!
sleep 0.3
printf '%s\n' "SELECT CONNECTION_ID() AS conn, PS_CURRENT_THREAD_ID() AS thr;" "BEGIN;" \
  "UPDATE acct SET bal = bal - 10 WHERE id = 2;" "SELECT SLEEP(3);" \
  "UPDATE acct SET bal = bal + 10 WHERE id = 1;" "COMMIT;" "SELECT NOW(6) AS done;" | MS > "$O/B-s2.txt" 2>&1 &
Q2=$!
sleep 2.2
{ echo "## B 대기 중 data_locks"; M -t -e "$LOCKS"
  echo "## B 대기 중 data_lock_waits 조인 (THREAD_ID 기준, 함정)"; M -t -e "$WAITS"
  echo "## B 대기 중 data_lock_waits 조인 (트랜잭션 기준)"; M -t -e "$WAITS2"
  echo "## B 막는 스레드의 문장 이력"; M -t -e "$HIST"; } > "$O/B-waiting.txt" 2>&1
wait $Q1 $Q2
latest > "$O/B-status.txt"
M -t -e "SELECT * FROM acct;" > "$O/B-final.txt"
{ echo "## 카운터(끝)"; counters; } >> "$O/00-settings.txt" 2>&1

# ---------- C: 갭 잠금 표기 (교착 없음, 표기 대조용) ----------
M -e "SET GLOBAL innodb_status_output_locks = ON;"
printf '%s\n' "BEGIN;" "SELECT * FROM acct WHERE id = 5 FOR UPDATE;" \
  "SELECT * FROM acct WHERE id BETWEEN 1 AND 2 FOR UPDATE;" "SELECT * FROM visit WHERE user_key = 'u-1' FOR SHARE;" \
  "SELECT SLEEP(3);" "ROLLBACK;" | MS > "$O/C-s1.txt" 2>&1 &
C1=$!
sleep 0.8
printf '%s\n' "BEGIN;" "INSERT INTO acct VALUES (6, 0);" "ROLLBACK;" | MS > "$O/C-s2.txt" 2>&1 &
C2=$!
sleep 1
{ echo "## C data_locks"; M -t -e "$LOCKS"
  echo "## C STATUS TRANSACTIONS (innodb_status_output_locks=ON)"
  M -N -r -e "SHOW ENGINE INNODB STATUS" | sed -n '/^TRANSACTIONS$/,/^FILE I\/O$/p'; } > "$O/C-locks.txt" 2>&1
wait $C1 $C2
M -e "SET GLOBAL innodb_status_output_locks = OFF;"

sleep 1
docker compose logs --no-log-prefix --since "$LOGSTART" mysql > "$O/errorlog.txt" 2>&1
M -e "SET GLOBAL log_error_verbosity = 2;"
echo "r$R done: $(grep -c 'Deadlock found' "$O"/A-s*.txt "$O"/B-s*.txt | tr '\n' ' ')"
