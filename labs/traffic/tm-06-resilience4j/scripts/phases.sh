#!/usr/bin/env bash
# 11분 동안 부하를 주면서 하위 서비스의 상태를 다섯 번 바꾼다. tm-06-resilience4j 디렉터리에서 실행한다.
#   0~2분  정상      50ms, 실패 0
#   2~5분  느려짐    1000ms, 실패 0
#   5~6분  정상
#   6~9분  빨리 실패  50ms, 실패 100%
#   9~11분 정상
set -euo pipefail
DS=${DS:-http://localhost:28082}
fault() { echo "$(date +%T) delayMs=$1 errorRate=$2"; curl -s -X POST "$DS/admin/fault?delayMs=$1&errorRate=$2"; echo; }

fault 50 0
docker compose --profile load run --rm load > out/k6.txt 2>&1 &
K6=$!
sleep 120; fault 1000 0
sleep 180; fault 50 0
sleep 60;  fault 50 1.0
sleep 180; fault 50 0
wait $K6
tail -40 out/k6.txt
