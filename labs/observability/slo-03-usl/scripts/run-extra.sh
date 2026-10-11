#!/usr/bin/env bash
# run-rest.sh 다음에 돌린 것: 일의 양을 고정한 CPU 시나리오, 정점 근처를 1씩 촘촘히 잰 일관성 시나리오.
set -euo pipefail
cd "$(dirname "$0")/.."
APP=${APP_URL:-http://localhost:22080}

# CPU: 벽시계 2ms 대신 계산 180만 번(동시성 1에서 약 2ms). 코어를 뺏기면 그만큼 늦게 끝난다
APP_CPUS=2 docker compose up -d --build app; sleep 8
curl -s -XPOST "$APP/config?parallelUs=0&serialUs=0&coherencyUs=0&cpuUs=0&cpuLoops=1800000&spinSerial=true&expRandom=false"; echo
bash scripts/sweep.sh cpu-fixed 3

# 일관성 시나리오의 정점 근처
docker compose up -d app; sleep 8
curl -s -XPOST "$APP/config?parallelUs=20000&serialUs=500&coherencyUs=50&cpuUs=0&cpuLoops=0&spinSerial=true&expRandom=false"; echo
STEPS="16 17 18 19 20 21 22 23 24" bash scripts/sweep.sh coherency-fine 2
