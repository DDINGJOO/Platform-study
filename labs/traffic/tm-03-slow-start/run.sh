#!/usr/bin/env bash
# 사용: ./run.sh <rr|rr-ss|lr|lr-ss>
# app-4 를 내린 상태에서 Envoy 를 새 설정으로 띄우고 k6 로 RATE(기본 150)건/초를 DURATION(기본 150s) 보낸다.
# 부하 시작 JOIN_AT(기본 30)초 뒤에 app-4 를 새로 띄운다. 결과는 out/<설정>/ 에 남는다.
set -euo pipefail
cd "$(dirname "$0")"
cfg=$1; join=${JOIN_AT:-30}
out=out/$cfg; mkdir -p "$out"
docker compose rm -sf app-4 >/dev/null 2>&1 || true
ENVOY_CONFIG=$cfg docker compose up -d --no-deps --force-recreate envoy
sleep 8
date +%s > "$out/start"
( sleep "$join"; date +%s.%N > "$out/join"; docker compose up -d --no-deps app-4 >/dev/null 2>&1 ) &
docker compose --profile load run --rm load > "$out/k6.txt" 2>&1
date +%s > "$out/end"
wait
sleep 12   # Envoy 는 접근 로그를 모아 두었다가 내보낸다
docker compose logs --no-log-prefix envoy > "$out/access.log"
docker compose logs --no-log-prefix app-4 | grep -E 'Started|JVM' > "$out/app4-start.txt" || true
curl -s "localhost:${ENVOY_ADMIN_PORT:-26901}/stats" | grep -E 'cluster\.backend\.(health_check|upstream_rq_[0-9]xx|upstream_rq_total|upstream_cx_connect_fail|lb_)' > "$out/stats.txt" || true
grep -E 'http_req_duration|http_reqs|http_req_failed' "$out/k6.txt"
python3 join-report.py "$out"
