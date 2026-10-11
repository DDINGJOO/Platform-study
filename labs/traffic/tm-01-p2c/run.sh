#!/usr/bin/env bash
# 사용: ./run.sh <rr|p2c|fullscan> [multi]
# Envoy 설정을 바꿔 띄우고(앱은 그대로 둔다), k6 로 RATE(기본 400)건/초를 DURATION(기본 90s) 동안 보낸 뒤
# k6 요약과 Envoy 접근 로그를 out/<이름>/ 에 남긴다. multi 를 주면 Envoy 세 대에 요청을 나눠 보낸다.
set -euo pipefail
cd "$(dirname "$0")"
cfg=$1; mode=${2:-single}
name=$cfg-$mode
out=out/$name; mkdir -p "$out"
if [ "$mode" = multi ]; then
  profiles="--profile multi"; envoys=envoy:10000,envoy-2:10000,envoy-3:10000; svcs="envoy envoy-2 envoy-3"
else
  profiles=""; envoys=envoy:10000; svcs="envoy"
  docker compose --profile multi rm -sf envoy-2 envoy-3 >/dev/null 2>&1 || true
fi
# Envoy 를 새로 만들어 접근 로그와 통계를 비운다
ENVOY_CONFIG=$cfg docker compose $profiles up -d --no-deps --force-recreate $svcs
sleep 5
date +%s > "$out/start"
ENVOYS=$envoys docker compose --profile load run --rm load > "$out/k6.txt" 2>&1
date +%s > "$out/end"
sleep 12   # Envoy 는 접근 로그를 모아 두었다가 내보낸다. 바로 모으면 마지막 몇 초가 빠진다
docker compose $profiles logs --no-log-prefix $svcs > "$out/access.log"
curl -s "localhost:${ENVOY_ADMIN_PORT:-26901}/clusters" | grep -E '::(rq_total|rq_active|rq_error)::' > "$out/clusters.txt" || true
grep -E 'http_req_duration|http_reqs|http_req_failed' "$out/k6.txt"
python3 ../common-envoy/scripts/access-summary.py "$out/access.log" --skip 10
