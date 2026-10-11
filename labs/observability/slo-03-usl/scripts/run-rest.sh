#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
APP=${APP_URL:-http://localhost:22080}
docker compose up -d --build app; sleep 8
curl -s -XPOST "$APP/config?parallelUs=20000&serialUs=1000&coherencyUs=0&cpuUs=0&spinSerial=true&expRandom=true"; echo
bash scripts/sweep.sh contention-exp 3
curl -s -XPOST "$APP/config?parallelUs=20000&serialUs=500&coherencyUs=50&cpuUs=0&spinSerial=true&expRandom=true"; echo
bash scripts/sweep.sh coherency-exp 3
APP_CPUS=2 docker compose up -d app; sleep 8
curl -s -XPOST "$APP/config?parallelUs=0&serialUs=0&coherencyUs=0&cpuUs=2000&spinSerial=true&expRandom=false"; echo
curl -s "$APP/stats"; echo
bash scripts/sweep.sh cpu 3
