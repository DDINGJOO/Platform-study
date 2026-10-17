#!/usr/bin/env bash
# 사용: scripts/run.sh <시나리오>
#   count-demo     검증 COUNT 두 가지를 이상한 값 하나씩으로 비교
#   ddl            0단계: 컬럼 넓히기. INPLACE 가 되는 길이와 안 되는 길이, COPY 동안 쓰기 지연
#   happy          바른 순서: v0 -> v1 -> v2 -> 채우기(중간에 죽였다 이어서) -> 검증 -> v3
#   skip-read      읽기 먼저를 건너뛴다: v0 -> v2
#   strict-early   평문 모양만 채우고 "평문 모양 COUNT = 0" 을 믿고 v3
#   config-miss    v2 중 한 대가 쓰기 스위치를 못 읽었다(1편): 채우기 뒤 0 이 다시 늘어난다
#   rollback-wrong 되돌림: 쓰기를 켠 채 복원 -> v0
#   rollback-right 되돌림: 쓰기를 먼저 끈다(v2-off) -> 복원 -> 검증 -> v0
# 시나리오마다 DB 를 새로 채운다. 결과 요약은 표준 출력, 요청 원자료는 out/<시나리오>-req.csv
source "$(dirname "$0")/lib.sh"
S=${1:?scenario}
MIX=${MIX:-8}

trap 'load_stop 2>/dev/null; stop_all' EXIT

counts() { echo "  [counts] $(sql -N -e "$(cat sql/counts.sql)" | awk '{printf "plain_shape=%s not_cipher=%s not_cipher_ne_empty=%s nulls=%s total=%s", $1,$2,$3,$4,$5}')"; }

prelude() {   # DB 초기화, 컬럼을 넓혀 두고, v0 두 대로 부하를 건다
  echo "== $S"
  echo "  [db] rows=$(reset_db)"
  sql -e "ALTER TABLE agent MODIFY rrn VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_bin NULL"
  batch dump "$ST/expected.jsonl"
  pool_set
  start_inst 38081 v0; start_inst 38082 v0
  pool_set $(entry 38081 v0) $(entry 38082 v0)
  phase "0-v0"
  load_start "$S"
  sleep 5
}

finish() {
  load_stop
  echo "  [load]"
  sed 's/^/    /' "$OUT/$S-load.log"
  python3 scripts/analyze.py "$OUT/$S-req.csv" | sed 's/^/    /'
}

fill_with_kill() {   # 채우기를 띄우고 4초 뒤 죽였다가 다시 띄운다. 진행 위치에서 이어지는지 본다
  local sel=$1
  # 함수(batch)를 백그라운드로 돌리면 $! 가 서브셸이라 kill 이 java 에 닿지 않는다. java 를 직접 띄운다
  java -Xmx256m -cp "$CP" Lab batch fill --select "$sel" --page 1000 --sleep-ms 20 > "$OUT/$S-fill1.log" 2>&1 &
  local bp=$!
  sleep 4
  kill -9 "$bp" 2>/dev/null || true
  wait "$bp" 2>/dev/null || true
  echo "  [fill#1 killed -9] last_log=\"$(tail -1 "$OUT/$S-fill1.log")\" saved_cursor=$(sql -N -e "SELECT cursor_id FROM batch_state WHERE job='fill'")"
  batch fill --select "$sel" --page 1000 --sleep-ms 20 > "$OUT/$S-fill2.log" 2>&1
  grep -E 'start|done|건너뛴' "$OUT/$S-fill2.log" | sed 's/^/  [fill#2] /'
}

case "$S" in
count-demo)
  echo "== $S"
  sql -t < sql/count_demo.sql
  ;;

ddl)
  echo "== $S"
  echo "  [db] rows=$(reset_db)"
  batch dump "$ST/expected.jsonl"
  start_inst 38081 v0; start_inst 38082 v0
  pool_set $(entry 38081 v0) $(entry 38082 v0)
  phase "0-before"; load_start "$S"; sleep 5
  phase "1-inplace-63"
  t=$(python3 -c 'import time;print(time.time())')
  sql -e "ALTER TABLE agent MODIFY rrn VARCHAR(63) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_bin NULL, ALGORITHM=INPLACE, LOCK=NONE" \
    && echo "  [ddl] VARCHAR(63) INPLACE ok, $(python3 -c "import time;print('%.2fs' % (time.time()-$t))")"
  sleep 3
  phase "2-inplace-255"
  docker compose exec -T mysql mysql -ulab -plabpass lab -e "ALTER TABLE agent MODIFY rrn VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_bin NULL, ALGORITHM=INPLACE, LOCK=NONE" 2>&1 | grep -v Warning | sed 's/^/  [ddl] /' || true
  sleep 3
  phase "3-copy-255"
  t=$(python3 -c 'import time;print(time.time())')
  sql -e "ALTER TABLE agent MODIFY rrn VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_bin NULL, ALGORITHM=COPY" \
    && echo "  [ddl] VARCHAR(255) COPY ok, $(python3 -c "import time;print('%.2fs' % (time.time()-$t))")"
  phase "4-after"; sleep 5
  finish
  python3 scripts/analyze.py "$OUT/$S-req.csv" --latency
  ;;

happy)
  prelude
  phase "1-roll-v0-to-v1"; rolling v1 "$MIX"
  phase "2-v1"; sleep 5
  phase "3-roll-v1-to-v2"; rolling v2 "$MIX"
  phase "4-v2"; sleep 3; counts
  phase "5-fill"; fill_with_kill all
  phase "6-verify"; counts; batch verify | sed 's/^/  /'
  phase "7-roll-v2-to-v3"; rolling v3 "$MIX"
  phase "8-v3"; sleep 8; counts
  finish
  ;;

skip-read)
  prelude
  phase "1-roll-v0-to-v2"; rolling v2 "$MIX"
  phase "2-v2"; sleep 5
  finish
  ;;

strict-early)
  prelude
  phase "1-roll-v0-to-v1"; rolling v1 "$MIX"
  phase "3-roll-v1-to-v2"; rolling v2 "$MIX"
  phase "5-fill-shape"; fill_with_kill shape
  phase "6-verify"; counts; batch verify | sed 's/^/  /'
  phase "7-roll-v2-to-v3"; rolling v3 "$MIX"
  phase "8-v3"; sleep 8
  finish
  ;;

config-miss)
  prelude
  phase "1-roll-v0-to-v1"; rolling v1 "$MIX"
  # 2차 배포: 두 대 중 한 대는 스위치가 읽히지 않은 v2-off 로 뜬다(설정 파일이 그 프로필에서 안 읽힌 상황)
  phase "3-roll-v1-to-v2(one-miss)"
  start_inst 38085 v2; pool_set $(pool_get) $(entry 38085 v2); sleep "$MIX"; pool_set $(pool_get | grep -v '^38081:'); sleep 1; stop_inst 38081
  start_inst 38086 v2-off; pool_set $(pool_get) $(entry 38086 v2-off); sleep "$MIX"; pool_set $(pool_get | grep -v '^38082:'); sleep 1; stop_inst 38082
  phase "5-fill"; fill_with_kill all
  phase "6-verify"; counts
  for i in 1 2 3; do sleep 10; echo "  [+${i}0s]"; counts; done
  finish
  ;;

rollback-wrong|rollback-right)
  prelude
  phase "1-roll-v0-to-v1"; rolling v1 "$MIX"
  phase "3-roll-v1-to-v2"; rolling v2 "$MIX"
  phase "5-fill"; batch fill --select all --page 1000 > "$OUT/$S-fill.log" 2>&1; grep done "$OUT/$S-fill.log" | sed 's/^/  /'
  phase "6-v2"; counts; sleep 3
  if [ "$S" = rollback-right ]; then
    phase "R1-roll-v2-to-v2off"; rolling v2-off "$MIX"
  fi
  phase "R2-restore"
  batch restore --page 1000 > "$OUT/$S-restore.log" 2>&1; grep done "$OUT/$S-restore.log" | sed 's/^/  /'
  sleep 3
  phase "R3-verify"
  echo "  [after restore] cipher_rows=$(sql -N -e "SELECT COUNT(*) FROM agent WHERE rrn LIKE 'LABENC1:%'")"
  phase "R4-roll-to-v0"; rolling v0 "$MIX"
  phase "R5-v0"; sleep 8
  echo "  [end] cipher_rows=$(sql -N -e "SELECT COUNT(*) FROM agent WHERE rrn LIKE 'LABENC1:%'")"
  finish
  ;;

fake-prefix)   # SQL COUNT 가 못 세는 값: 접두어만 맞고 풀리지 않는 값
  echo "== $S"
  echo "  [db] rows=$(reset_db)"
  sql -e "ALTER TABLE agent MODIFY rrn VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_bin NULL"
  batch fill --select all --page 1000 | grep done | sed 's/^/  /'
  sql -e "UPDATE agent SET rrn = 'LABENC1:hello' WHERE id = 150001"
  counts
  batch verify | sed 's/^/  /'
  ;;

*) echo "unknown scenario $S"; exit 1 ;;
esac
