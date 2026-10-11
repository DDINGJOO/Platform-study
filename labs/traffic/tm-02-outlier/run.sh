#!/usr/bin/env bash
# 사용: ./run.sh <rr|p2c|fullscan|p2c-od-default|p2c-od-20> [고칠 시점(초)]
# Envoy 를 새 설정으로 띄우고, app-5 를 "즉시 503" 상태로 바꾼 뒤 k6 로 RATE(기본 200)건/초를 DURATION(기본 90s) 보낸다.
# 두 번째 인자를 주면 부하 시작 후 그 초에 app-5 를 고친다(fail=false). 결과는 out/<설정>/ 에 남는다.
set -euo pipefail
cd "$(dirname "$0")"
cfg=$1; heal=${2:-}
out=out/$cfg; mkdir -p "$out"
APP5=localhost:${APP_PORT_BASE:-2610}5
curl -s -X POST "$APP5/chaos?fail=false" >/dev/null
ENVOY_CONFIG=$cfg docker compose up -d --no-deps --force-recreate envoy
sleep 5
curl -s -X POST "$APP5/chaos?fail=true"; echo        # app-5 고장: 요청이 오면 바로 503
date +%s > "$out/start"
if [ -n "$heal" ]; then
  ( sleep "$heal"; curl -s -X POST "$APP5/chaos?fail=false" > /dev/null; date +%s > "$out/healed" ) &
fi
docker compose --profile load run --rm load > "$out/k6.txt" 2>&1
date +%s > "$out/end"
wait
sleep 12   # Envoy 는 접근 로그를 모아 두었다가 내보낸다. 바로 모으면 마지막 몇 초가 빠진다
docker compose logs --no-log-prefix envoy > "$out/access.log"
curl -s "localhost:${ENVOY_ADMIN_PORT:-26901}/stats" | grep -E 'cluster\.backend\.(outlier_detection|upstream_rq_[0-9]xx|upstream_rq_total)' > "$out/stats.txt" || true
curl -s -X POST "$APP5/chaos?fail=false" >/dev/null
grep -E 'http_req_duration|http_reqs|http_req_failed' "$out/k6.txt"
python3 ../common-envoy/scripts/access-summary.py "$out/access.log" --skip 10
cat "$out/stats.txt"
