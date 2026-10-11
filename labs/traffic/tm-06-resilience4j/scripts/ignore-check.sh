#!/usr/bin/env bash
# 덧붙인 확인: 서킷이 벌크헤드 거절(BulkheadFullException)을 실패로 세지 않게 하면 어떻게 되나.
# order-cbbh(기본 설정)와 order-cbbh-ign(ignoreExceptions 에 BulkheadFullException)만 4분 동안 비교한다.
#   0~1분 정상 50ms, 1~3분 느려짐 1000ms, 3~4분 정상
# 실행: docker compose --profile ignore up -d --build && ./scripts/ignore-check.sh
set -euo pipefail
DS=${DS:-http://localhost:28082}
fault() { echo "$(date +%T) delayMs=$1 errorRate=$2"; curl -s -X POST "$DS/admin/fault?delayMs=$1&errorRate=$2"; echo; }

fault 50 0
DURATION=4m TARGETS=order-cbbh,order-cbbh-ign docker compose --profile load run --rm load > out/k6-ignore.txt 2>&1 &
K6=$!
sleep 60;  fault 1000 0
sleep 120; fault 50 0
wait $K6
