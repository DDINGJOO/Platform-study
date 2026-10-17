#!/usr/bin/env bash
# 교착을 셀 수 있는 자리를 한 번에 본다: INNODB_METRICS 잠금 카운터, 상태 변수, 관련 설정.
D="$(cd "$(dirname "$0")" && pwd)"
echo "== SELECT VERSION(), 관련 설정"
"$D/sql.sh" "SELECT VERSION() AS version, @@innodb_deadlock_detect AS deadlock_detect, @@innodb_print_all_deadlocks AS print_all_deadlocks, @@innodb_lock_wait_timeout AS lock_wait_timeout, @@log_error AS log_error;"
echo "== INNODB_METRICS 의 lock 서브시스템 중 deadlock/timeout"
"$D/sql.sh" "SELECT NAME, TYPE, STATUS, COUNT, COUNT_RESET FROM information_schema.INNODB_METRICS WHERE NAME LIKE 'lock_deadlock%' OR NAME = 'lock_timeouts' OR NAME='lock_row_lock_waits' ORDER BY NAME;"
echo "== SHOW GLOBAL STATUS LIKE '%dead%'"
"$D/sql.sh" "SHOW GLOBAL STATUS LIKE '%dead%';"
echo "== SHOW GLOBAL STATUS LIKE 'Innodb_row_lock%'"
"$D/sql.sh" "SHOW GLOBAL STATUS LIKE 'Innodb_row_lock%';"
echo "== performance_schema.global_status 에서 이름에 dead 가 들어간 변수 수"
"$D/sql.sh" "SELECT COUNT(*) AS n_dead FROM performance_schema.global_status WHERE VARIABLE_NAME LIKE '%dead%';"
