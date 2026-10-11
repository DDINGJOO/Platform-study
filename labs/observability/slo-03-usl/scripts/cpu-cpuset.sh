#!/usr/bin/env bash
# 같은 CPU 시나리오를 할당량 없이 코어 두 개에 고정(cpuset "0,1")해서 다시 잰다.
set -euo pipefail
cd "$(dirname "$0")/.."
APP=${APP_URL:-http://localhost:22080}
docker compose -f compose.yaml -f compose.cpuset.yaml up -d app; sleep 8
curl -s -XPOST "$APP/config?parallelUs=0&serialUs=0&coherencyUs=0&cpuUs=0&cpuLoops=1800000&spinSerial=true&expRandom=false"; echo
curl -s "$APP/stats"; echo
STEPS="1 2 4 6 8 12 16 24 32 48 64" bash scripts/sweep.sh cpu-cpuset 2
docker compose up -d app
