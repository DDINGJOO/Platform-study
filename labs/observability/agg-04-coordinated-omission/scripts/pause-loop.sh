#!/usr/bin/env bash
# 세 앱 컨테이너를 PERIOD 초마다 PAUSE 초씩 docker pause 로 얼린다(프로세스 전체 정지).
# 실제로 얼린 시각과 녹인 시각(유닉스 초)을 out/pauses.log 에 남긴다. COUNT 번 반복하고 끝난다.
# 실습 디렉터리에서 실행한다: ./scripts/pause-loop.sh
set -euo pipefail
PERIOD=${PERIOD:-30}; PAUSE=${PAUSE:-2}; COUNT=${COUNT:-10}; FIRST=${FIRST:-15}
APPS="app-closed app-open app-starved"
: > out/pauses.log
sleep "$FIRST"
for i in $(seq 1 "$COUNT"); do
  t0=$(python3 -c 'import time;print(f"{time.time():.3f}")')
  docker compose pause $APPS >/dev/null 2>&1
  t1=$(python3 -c 'import time;print(f"{time.time():.3f}")')
  sleep "$PAUSE"
  t2=$(python3 -c 'import time;print(f"{time.time():.3f}")')
  docker compose unpause $APPS >/dev/null 2>&1
  t3=$(python3 -c 'import time;print(f"{time.time():.3f}")')
  echo "$i pause_start=$t0 paused=$t1 unpause_start=$t2 unpaused=$t3" | tee -a out/pauses.log
  sleep $((PERIOD - PAUSE))
done
