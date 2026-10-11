#!/usr/bin/env bash
# 글에 실린 세 시나리오를 차례로 돌린다(각 3회 × 11단계, 합쳐 50분 남짓).
set -euo pipefail
cd "$(dirname "$0")/.."
APP=${APP_URL:-http://localhost:22080}

# A. 경합만: 병렬 20ms(잠) + 락 안에서 1ms
curl -s -XPOST "$APP/config?parallelUs=20000&serialUs=1000&coherencyUs=0&cpuUs=0&spinSerial=true"; echo
bash scripts/sweep.sh contention 3

# B. 경합 + 일관성: 병렬 20ms + 락 안에서 0.5ms + 같이 들어와 있는 요청 하나당 0.05ms
curl -s -XPOST "$APP/config?parallelUs=20000&serialUs=500&coherencyUs=50&cpuUs=0&spinSerial=true"; echo
bash scripts/sweep.sh coherency 3
