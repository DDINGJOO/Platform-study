#!/usr/bin/env bash
# 부하 한 번: 앱 컨테이너의 cgroup CPU 사용량을 앞뒤로 재고, k6 를 DURATION(기본 3m) 돌린 뒤
# 시작·끝 시각(유닉스 초)과 그 사이 CPU 초를 찍는다. 프로파일의 CPU 합계와 맞춰 보는 데 쓴다.
set -euo pipefail
cd "$(dirname "$0")"
cpu() { docker compose exec -T app cat /sys/fs/cgroup/cpu.stat | awk '/^usage_usec/{print $2}'; }
c0=$(cpu); t0=$(date +%s)
docker compose --profile load run --rm -e DURATION="${DURATION:-3m}" load 2>&1 | grep -E "http_req_duration|http_reqs"
t1=$(date +%s); c1=$(cpu)
awk -v a="$c0" -v b="$c1" -v t0="$t0" -v t1="$t1" 'BEGIN{printf "window %d %d  app_cpu_seconds=%.1f  (%.2f cores)\n", t0, t1, (b-a)/1e6, (b-a)/1e6/(t1-t0)}'
docker compose logs --since "$((t1-t0+5))s" app 2>/dev/null | grep -c "Error uploading snapshot" | sed 's/^/rejected_uploads=/' || true
