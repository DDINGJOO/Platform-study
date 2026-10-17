#!/usr/bin/env bash
# 전체 실습: 카운터 확인 → 교착 1건씩 세 자리 대조 → 13분 시계열 → 재시작 뒤 카운터.
# 출력은 out/ 에 저장한다. 끝나면 docker compose down -v 로 내린다(이 스크립트는 내리지 않는다).
set -u
cd "$(dirname "$0")/.."
S=scripts; O=out; mkdir -p $O
q() { $S/sql.sh "$1"; }
cnt() { docker exec dl04-mysql mysql -uroot -plabroot -N -e "SELECT CONCAT(NAME,'=',COUNT) FROM information_schema.INNODB_METRICS WHERE NAME IN ('lock_deadlocks','lock_timeouts') ORDER BY NAME" 2>/dev/null | tr '\n' ' '; }
logn() { docker logs dl04-mysql 2>&1 | grep -c "Transactions deadlock detected"; }

docker compose up -d --wait
q "CREATE TABLE IF NOT EXISTS t (id INT PRIMARY KEY, v INT NOT NULL); INSERT IGNORE INTO t VALUES (1,0),(2,0);"

$S/probe.sh > $O/probe-0.txt; cat $O/probe-0.txt

{
echo "== step1 기본값(print_all_deadlocks=OFF)에서 교착 1건"
echo "before: $(cnt) errlog=$(logn)"
$S/deadlock_once.sh
echo "after : $(cnt) errlog=$(logn)"

echo; echo "== step2 SET GLOBAL innodb_print_all_deadlocks=ON (log_error_verbosity=$(docker exec dl04-mysql mysql -uroot -plabroot -N -e 'SELECT @@log_error_verbosity' 2>/dev/null)) 에서 교착 1건"
q "SET GLOBAL innodb_print_all_deadlocks=ON;" >/dev/null
$S/deadlock_once.sh
echo "after : $(cnt) errlog=$(logn)"

echo; echo "== step3 SET GLOBAL log_error_verbosity=3 에서 교착 1건"
q "SET GLOBAL log_error_verbosity=3;" >/dev/null
$S/deadlock_once.sh
echo "after : $(cnt) errlog=$(logn)"

echo; echo "== step4 SET GLOBAL innodb_monitor_reset='lock_deadlocks'"
q "SELECT NAME, COUNT, COUNT_RESET FROM information_schema.INNODB_METRICS WHERE NAME='lock_deadlocks';"
q "SET GLOBAL innodb_monitor_reset='lock_deadlocks'; SELECT NAME, COUNT, COUNT_RESET FROM information_schema.INNODB_METRICS WHERE NAME='lock_deadlocks';"

echo; echo "== step5 innodb_deadlock_detect=OFF, innodb_lock_wait_timeout=3 에서 같은 교착"
q "SET GLOBAL innodb_deadlock_detect=OFF;" >/dev/null
echo "before: $(cnt) errlog=$(logn)"
time LOCK_WAIT=3 $S/deadlock_once.sh
echo "after : $(cnt) errlog=$(logn)"
q "SET GLOBAL innodb_deadlock_detect=ON;" >/dev/null
} 2>&1 | tee $O/steps${RUN:+-$RUN}.txt
[ -n "${STEPS_ONLY:-}" ] && exit 0

echo; echo "== step6 13분 시계열 (1초 = 1분)"
B_LOG=$(logn); B_CNT=$(cnt)
python3 $S/timeline.py | tee $O/timeline-run.txt
{ echo "before: $B_CNT errlog=$B_LOG"; echo "after : $(cnt) errlog=$(logn)"; } | tee -a $O/timeline-run.txt
grep -c "errors=1" $O/deadlocks.log | sed 's/^/deadlock_once runs with exactly 1 ERROR: /' | tee -a $O/timeline-run.txt
grep -v "errors=1" $O/deadlocks.log | tee -a $O/timeline-run.txt

echo; echo "== step7 컨테이너 재시작 뒤"
echo "before restart: $(cnt)" | tee $O/restart.txt
docker compose restart mysql >/dev/null 2>&1; docker compose up -d --wait >/dev/null 2>&1
echo "after restart : $(cnt)" | tee -a $O/restart.txt
$S/sql.sh "SELECT @@innodb_print_all_deadlocks AS print_all_deadlocks, @@log_error_verbosity AS verbosity;" | tee -a $O/restart.txt
docker logs dl04-mysql > $O/mysqld.log 2>&1
