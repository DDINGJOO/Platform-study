#!/bin/bash
# 한 번 실행: ./scripts/run.sh <unbounded|capped> <장애 지속 초> [결과 이름]
# 실행 위치: labs/devops/auto-02-auto-remediation
# 환경 변수
#   AM_CONF=alertmanager.default.yml   Alertmanager 간격을 기본값으로 (기본은 줄인 alertmanager.yml)
#   HUMAN_DELAY=120                    escalate 가 찍히고 이만큼 뒤에 사람이 원인(state/leak)을 지운다. 없으면 아무도 안 온다
set -u
cd "$(dirname "$0")/.."
MODE=$1; DUR=${2:-900}; TAG=${3:-$MODE}; R=out/$TAG
rm -rf "$R" state/leak; mkdir -p "$R" state
rm -f out/events.jsonl out/load.csv
MODE=$MODE docker compose up -d --force-recreate
sleep 75                                     # 기준 구간. app 가동 시간이 GRACE+RAMP(60초)를 넘긴다
F0=$(docker compose exec -T app python -c "import time,pathlib; pathlib.Path('/state/leak').touch(); print(time.time())")
{ echo "fault_start=$F0"; echo "mode=$MODE duration=$DUR am_conf=${AM_CONF:-alertmanager.yml} human_delay=${HUMAN_DELAY:-none}"; } > "$R/meta.txt"
echo "[run] $TAG 장애 시작, ${DUR}초 동안 둔다"

HPID=""
if [ -n "${HUMAN_DELAY:-}" ]; then
  # 사람 흉내: escalate 를 보고 HUMAN_DELAY 초 뒤 절차서 3단계(rm state/leak)를 한다
  ( until grep -q '"type": "escalate"' out/events.jsonl 2>/dev/null; do sleep 1; done
    sleep "$HUMAN_DELAY"
    rm -f state/leak
    echo "human_fix=$(python3 -c 'import time; print(time.time())')" >> "$R/meta.txt"
    echo "[run] 사람이 원인을 지웠다" ) &
  HPID=$!
fi

sleep "$DUR"
F1=$(docker compose exec -T remediator python -c "import time; print(time.time())")   # app 은 재시작 중일 수 있다
[ -n "$HPID" ] && kill "$HPID" 2>/dev/null
echo "fault_end=$F1" >> "$R/meta.txt"
curl -s "http://localhost:${PROM_PORT:-36190}/api/v1/query_range" --data-urlencode 'query=ALERTS{alertname="AppErrorRatioHigh"}' \
  --data-urlencode "start=$(python3 -c "print($F0-90)")" --data-urlencode "end=$F1" --data-urlencode step=1 > "$R/alerts.json"
curl -s "http://localhost:${PROM_PORT:-36190}/api/v1/query_range" --data-urlencode 'query=app:error_ratio:30s' \
  --data-urlencode "start=$(python3 -c "print($F0-90)")" --data-urlencode "end=$F1" --data-urlencode step=5 > "$R/ratio.json"
docker compose stop load remediator >/dev/null
cp out/events.jsonl out/load.csv "$R/"
docker compose logs --no-color app > "$R/app.log" 2>&1
rm -f state/leak
echo "[run] 끝. python3 scripts/analyze.py $R"
