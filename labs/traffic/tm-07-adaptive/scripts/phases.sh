#!/usr/bin/env bash
# 13분 동안 부하를 주면서 하위 지연을 두 번 바꾼다. tm-07-adaptive 디렉터리에서 실행한다.
#   0~3분   하위 50ms   (상한 초당 800건, 부하 200건: 여유)
#   3~10분  하위 500ms  (상한 초당 80건, 부하 200건: 2.5배 과부하)
#   10~13분 하위 50ms   (회복)
set -euo pipefail
PORTS=${PORTS:-"28282 28285 28284"}   # per-request 프로필을 띄웠다면 28283 도 넣는다
delay() { echo "$(date +%T) delay=$1ms"; for p in $PORTS; do curl -s -m 3 --retry 5 --retry-all-errors -X POST "localhost:$p/admin/delay?ms=$1" > /dev/null || echo "  $p 응답 없음"; done; }

delay 50
DURATION=13m docker compose --profile load run --rm load > out/k6.txt 2>&1 &
K6=$!
sleep 180; delay 500
sleep 420; delay 50
wait $K6
tail -60 out/k6.txt
