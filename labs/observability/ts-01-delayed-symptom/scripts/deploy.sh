#!/usr/bin/env bash
# 배포 한 번 = 앱 컨테이너를 새 설정으로 다시 띄우고, 뜨면 Grafana 에 annotation 을 남긴다.
# 사용: scripts/deploy.sh <버전> <exact|ci> <배너> "<설명>"
set -euo pipefail
cd "$(dirname "$0")/.."
export APP_VERSION=$1 QUERY_VARIANT=$2 BANNER=$3
OUT=${OUT:-out}
docker compose up -d --no-deps app >/dev/null 2>&1
for _ in $(seq 1 90); do
  curl -sf "http://localhost:${APP_PORT:-34080}/actuator/health" >/dev/null && break
  sleep 1
done
ts=$(date +%s)
curl -s -X POST "http://localhost:${GRAFANA_PORT:-34030}/api/annotations" \
  -H 'Content-Type: application/json' \
  -d "{\"time\": ${ts}000, \"tags\": [\"deploy\"], \"text\": \"$4\"}" >/dev/null
echo "$ts deploy $1 $2 $3 $4" >> "$OUT/events.raw"
echo "deployed $1 ($2, $3)"
