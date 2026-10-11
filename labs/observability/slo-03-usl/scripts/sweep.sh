#!/usr/bin/env bash
# 동시성 N 을 단계별로 올리며 처리량을 잰다. 한 단계 = k6 한 번(워밍업 5초 + 측정 20초).
# 사용: bash scripts/sweep.sh <시나리오 이름> [반복 횟수]
#   앱 설정은 미리 POST /config 로 바꿔 둔다(README 참고).
# 결과: results/<시나리오>.csv 에 한 줄씩 덧붙인다.
set -euo pipefail
cd "$(dirname "$0")/.."

NAME=${1:?scenario name}
REPS=${2:-3}
STEPS=${STEPS:-"1 2 4 6 8 12 16 24 32 48 64"}
APP=${APP_URL:-http://localhost:22080}
OUT=results/$NAME.csv

[ -f "$OUT" ] || echo "scenario,rep,n,count,x_rps,avg_ms,p50_ms,p99_ms,fail_rate,lock_wait_ms,lock_hold_ms,peers_avg,loadavg1,started" > "$OUT"

stat() { curl -s "$APP/stats" | python3 -c 'import json,sys;d=json.load(sys.stdin);print(d["count"],d["lockWaitNs"],d["lockHoldNs"],d["peersSum"])'; }

for rep in $(seq 1 "$REPS"); do
  for n in $STEPS; do
    started=$(date +%H:%M:%S)
    read -r c0 w0 h0 p0 <<<"$(stat)"
    line=$(docker compose --profile load run --rm -e VUS="$n" k6 run -q --no-color /scripts/step.js 2>/dev/null | grep '^{"vus"')
    read -r c1 w1 h1 p1 <<<"$(stat)"
    # 도커 VM 전체의 1분 로드 애버리지. 다른 컨테이너가 CPU 를 얼마나 쓰고 있었는지 가늠한다
    load1=$(docker compose exec -T app cat /proc/loadavg | cut -d' ' -f1)
    python3 - "$NAME" "$rep" "$line" "$c0" "$w0" "$h0" "$p0" "$c1" "$w1" "$h1" "$p1" "$load1" "$started" >> "$OUT" <<'PY'
import json, sys
name, rep, line = sys.argv[1], sys.argv[2], sys.argv[3]
c0, w0, h0, p0, c1, w1, h1, p1 = map(int, sys.argv[4:12])
load1, started = sys.argv[12], sys.argv[13]
d = json.loads(line)
dc = max(c1 - c0, 1)   # 서버 쪽 값은 워밍업 5초까지 포함한 평균이다
x = d["count"] / d["measureSeconds"]
print(f'{name},{rep},{d["vus"]},{d["count"]},{x:.1f},{d["avgMs"]:.3f},{d["p50Ms"]:.3f},{d["p99Ms"]:.3f},'
      f'{d["failRate"]:.4f},{(w1-w0)/dc/1e6:.3f},{(h1-h0)/dc/1e6:.3f},{(p1-p0)/dc:.2f},{load1},{started}')
PY
    tail -1 "$OUT"
  done
done
