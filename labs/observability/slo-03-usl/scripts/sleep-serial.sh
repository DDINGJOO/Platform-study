#!/usr/bin/env bash
# 2절: 직렬 구간을 잠(parkNanos)으로 채웠을 때 경합 시나리오가 어디서 멈추는지 본다(N = 1, 32 한 번씩).
set -euo pipefail
cd "$(dirname "$0")/.."
APP=${APP_URL:-http://localhost:22080}
docker compose up -d app; sleep 8
curl -s -XPOST "$APP/config?parallelUs=20000&serialUs=1000&coherencyUs=0&cpuUs=0&cpuLoops=0&spinSerial=false&expRandom=false"; echo
rm -f results/sleep-serial.csv
STEPS="1 32" bash scripts/sweep.sh sleep-serial 1
