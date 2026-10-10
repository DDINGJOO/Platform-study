#!/usr/bin/env bash
# k6 를 돌리면서 시각에 맞춰 실패율(500 비율)을 바꾼다. 실행 위치: 이 디렉터리.
set -euo pipefail
A=http://localhost:${APP_A_PORT:-23181}
B=http://localhost:${APP_B_PORT:-23182}
fail() { curl -s -X POST "$1/admin/fail-rate?value=$2" >/dev/null; echo "$(date +%T) $1 fail-rate=$2"; }

fail $A 0; fail $B 0
docker compose --profile load run --rm load > k6.log 2>&1 &
K6=$!
date -u +%s > start.txt   # 분석할 때 쓰는 시작 시각(유닉스 초)
echo "$(date +%T) k6 시작 (0:00)"
sleep 60;  fail $A 0.02; fail $B 0.02   # 1:00 평소 실패율 2%
sleep 210; fail $A 0.3;  fail $B 0.3    # 4:30 장애: 실패율 30%
sleep 120; fail $A 0.02; fail $B 0.5    # 6:30 app-b 만 50%
sleep 90;  fail $B 0.02                 # 8:00 k6 가 끝나고 트래픽 0
wait $K6
echo "$(date +%T) k6 끝. 90초 동안 트래픽 없이 둔다"
sleep 90
echo "$(date +%T) 끝 (9:30)"
