#!/bin/sh
# 사용: ./run.sh <모드> <이름> [k6 환경변수...]
#   ./run.sh retry seq-retry VUS=1 ITERATIONS=200      한 번에 하나씩
#   ./run.sh retry vu10-retry VUS=10 ITERATIONS=600    동시에 10개씩
# 모드가 바뀌면 Envoy 를 그 설정으로 다시 띄우고 svc-a, svc-b 를 재시작한 뒤 워밍업한다.
# 측정 직전에 Envoy 카운터를 0 으로 돌리고(/reset_counters), 부하가 끝나면 층별 요청 수를 센다.
set -e
cd "$(dirname "$0")"
ADMIN=localhost:${ENVOY_ADMIN_PORT:-27101}
mode=$1; name=$2; shift 2
if [ "$(cat out/.mode 2>/dev/null)" != "$mode" ]; then
  ENVOY_MODE=$mode docker compose up -d --force-recreate envoy >/dev/null 2>&1
  until curl -sf $ADMIN/ready >/dev/null; do sleep 1; done
  # 앱의 JDK HttpClient 는 옛 Envoy 컨테이너로 맺은 연결을 들고 있다. 그대로 두면 읽기 타임아웃(10초)까지 멈춘다.
  docker compose restart svc-a svc-b >/dev/null 2>&1
  until curl -s localhost:${ENVOY_PORT:-27100}/work | grep -q "svc-a <-"; do sleep 1; done
  docker compose --profile load run --rm -e NAME=warmup-$mode -e VUS=4 -e ITERATIONS=200 load >/dev/null 2>&1
  echo "$mode" > out/.mode
fi
curl -sf -X POST $ADMIN/reset_counters >/dev/null
envs=""; for kv in "$@"; do envs="$envs -e $kv"; done
date -u +"%H:%M:%S start $name ($mode)"
docker compose --profile load run --rm -e NAME=$name $envs load 2>/dev/null | grep "reqs="
sleep 2
python3 count.py ${ENVOY_ADMIN_PORT:-27101}
date -u +"%H:%M:%S end $name"
