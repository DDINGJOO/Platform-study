#!/usr/bin/env bash
# 실습 한 번을 처음부터 끝까지 돌린다. 스택은 미리 떠 있어야 한다(docker compose up -d --build).
# 시간표(초, 시작 기준): T_CHANGE 에 쿼리 변경 배포, T_DECOY 에 무관한 배너 변경 배포(auto 면 예측 기준),
# 5xx 가 시작되면 AFTER_TIMEOUT 뒤에 "직전 변경"을 되돌리고, OBSERVE 동안 본 뒤 쿼리 변경을 되돌린다.
set -euo pipefail
cd "$(dirname "$0")/.."
T_CHANGE=${T_CHANGE:-180}; T_DECOY=${T_DECOY:-900}; AFTER_TIMEOUT=${AFTER_TIMEOUT:-120}; OBSERVE=${OBSERVE:-300}
MAX=${MAX:-3600}
export OUT=out/${RUN:-run1}; mkdir -p "$OUT"; : > "$OUT/events.raw"
P=http://localhost:${PROM_PORT:-34090}

start=$(date +%s); echo "$start start" >> "$OUT/events.raw"
last=$start
tick() {  # 5초마다 깨어난다. 30초 넘게 비면(노트북 잠자기 등) 기록해 두고 그 실행을 버린다
  sleep 5; now=$(date +%s)
  if (( now - last > 30 )); then echo "$now gap $last" >> "$OUT/events.raw"; fi
  last=$now
}
until_t() { while (( $(date +%s) - start < $1 )); do tick; done; }
q() { curl -s "$P/api/v1/query" --data-urlencode "query=$1" | python3 -c 'import json,sys; r=json.load(sys.stdin)["data"]["result"]; print(r[0]["value"][1] if r else 0)'; }
explain() {
  for v in exact ci; do
    if [ $v = exact ]; then w="customer_ref = 'C00042'"; else w="lower(customer_ref) = lower('C00042')"; fi
    docker compose exec -T db psql -U shop -d shop -c \
      "explain (analyze, buffers) select id, amount, created_at from orders where $w order by created_at desc limit 20" \
      > "$OUT/explain-$1-$v.txt"
  done
}

# DB 컨테이너 CPU 를 5초마다 기록 (docker stats 의 100% = 코어 하나)
dbid=$(docker compose ps -q db)
( while true; do echo "$(date +%s) $(docker stats --no-stream --format '{{.CPUPerc}}' "$dbid")"; sleep 5; done ) >> "$OUT/cpu.raw" &
cpu_pid=$!
trap 'kill $cpu_pid 2>/dev/null || true' EXIT

K6_OUT=${RUN:-run1}-k6.csv.gz docker compose --profile load run -d --rm load > "$OUT/k6.container"
explain start

until_t "$T_CHANGE"
scripts/deploy.sh 2.14.0 ci autumn-sale "order-api 2.14.0: 고객 코드 대소문자 무시 조회"
until_t $((T_CHANGE + 60)); explain change+60s
until_t $((T_CHANGE + 180)); python3 scripts/predict.py "$start" > "$OUT/prediction.txt"

# T_DECOY=auto: 미끼 배포를 "예측한 SLO 위반 시각의 DECOY_LEAD 초 전"에 둔다.
# 고정값(기본 900초)은 기계 속도에 따라 증상보다 늦게 떨어질 수 있다. 미끼는 증상 "직전"이어야 한다.
if [ "$T_DECOY" = auto ]; then
  slo_at=$(sed -n 's/^p99 300ms 를 넘는 행 수.*시작 기준 \([0-9-]*\)초.*/\1/p' "$OUT/prediction.txt")
  T_DECOY=$(( slo_at - ${DECOY_LEAD:-300} ))
  (( T_DECOY < T_CHANGE + 240 )) && T_DECOY=$((T_CHANGE + 240))
  echo "$(date +%s) decoy-planned $T_DECOY" >> "$OUT/events.raw"
fi

until_t "$T_DECOY"
scripts/deploy.sh 2.14.1 ci winter-sale "order-api 2.14.1: 배너 문구 변경"

# 5xx 가 초당 0.1건을 넘으면 타임아웃이 시작된 것으로 본다
while [ "$(q 'sum(rate(http_server_requests_seconds_count{uri="/orders/recent",status=~"5.."}[30s])) > 0.1')" = 0 ]; do
  tick; (( $(date +%s) - start > MAX )) && { echo "$(date +%s) abort" >> "$OUT/events.raw"; break; }
done
echo "$(date +%s) 5xx-detected" >> "$OUT/events.raw"
t=$(( $(date +%s) - start ))
until_t $((t + AFTER_TIMEOUT))
scripts/deploy.sh 2.14.0 ci autumn-sale "되돌리기: 2.14.1 배너 변경"
t=$(( $(date +%s) - start ))
until_t $((t + OBSERVE))
scripts/deploy.sh 2.13.0 exact autumn-sale "되돌리기: 2.14.0 쿼리 변경"
t=$(( $(date +%s) - start ))
until_t $((t + OBSERVE))
explain end

docker kill -s INT "$(cat "$OUT/k6.container")" >/dev/null 2>&1 || true
echo "$(date +%s) end" >> "$OUT/events.raw"
echo "run done: $OUT"
