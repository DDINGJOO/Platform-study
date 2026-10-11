#!/usr/bin/env bash
# 시나리오 하나를 돌린다. k6 로 요청을 계속 보내면서 배포·롤백 명령을 넣고, 명령 시각을 events 파일에 남긴다.
#   사용법: scripts/run.sh <recreate|rolling|rolling-prestop|rolling-undo|bluegreen|bg-undo-late|highlander>
# 실행 위치: labs/devops/ds-01-bluegreen
set -euo pipefail
cd "$(dirname "$0")/.."
NAME=$1
OUT=$NAME${TAG:+-$TAG}   # TAG 를 주면 결과 파일 이름에 붙인다 (같은 시나리오를 조건만 바꿔 다시 돌릴 때)
NOREUSE=${NOREUSE:-0}    # 1 이면 k6 가 요청마다 새 TCP 연결을 연다
K="kubectl --context kind-ds-01 -n lab"
AR="kubectl argo rollouts --context kind-ds-01 -n lab"
mkdir -p out
EV=out/$OUT.events; : > "$EV"
now() { python3 -c 'import time;print(int(time.time()*1000))'; }
mark() { echo "$(now) $*" >> "$EV"; echo "[$(date +%T)] $*"; }

reset() {   # 이전 시나리오를 지우고 manifest 하나를 v1 으로 띄운다
  $K delete deploy,rollout web --ignore-not-found --wait=true >/dev/null 2>&1 || true
  # Rollout 을 지워도 ReplicaSet 은 가비지 컬렉터가 나중에 지운다. 남은 것을 새 Rollout 이 같은 해시로 입양하지 않게 직접 지운다
  $K delete rs,pod -l app=web --wait=true >/dev/null 2>&1 || true
  kubectl --context kind-ds-01 apply -f k8s/00-namespace.yaml -f k8s/svc-web.yaml -f k8s/svc-preview.yaml >/dev/null
  kubectl --context kind-ds-01 apply -f "k8s/$1" >/dev/null
  wait_all v1
}
wait_all() {  # 서비스 입구로 20번 연속 같은 버전이 나올 때까지
  local n=0; while [ $n -lt 20 ]; do
    if curl -s -m 1 http://127.0.0.1:24080/ | grep -q "^$1 "; then n=$((n+1)); else n=0; sleep 0.5; fi
  done
}
wait_phase() { until [ "$($K get rollout web -o jsonpath='{.status.phase}')" = "$1" ]; do sleep 0.2; done; }
setver() {   # Rollout 의 VERSION 환경변수를 바꾼다 (파드 템플릿이 바뀌므로 새 ReplicaSet)
  $K patch rollout web --type json -p "[{\"op\":\"replace\",\"path\":\"/spec/template/spec/containers/0/env/0/value\",\"value\":\"$1\"}]" >/dev/null
}
watch_term() {   # 파드가 Terminating 이 되는 순간(deletionTimestamp 가 처음 보인 시각)을 events 에 남긴다
  local seen=" "
  while kill -0 "$K6PID" 2>/dev/null; do
    for p in $($K get pods -l app=web -o jsonpath='{range .items[?(@.metadata.deletionTimestamp)]}{.metadata.name}{" "}{end}' 2>/dev/null); do
      case "$seen" in *" $p "*) ;; *) seen="$seen$p "; echo "$(now) term:$p" >> "$EV" ;; esac
    done
    sleep 0.2
  done
}
load() {     # 백그라운드로 k6 를 돌린다
  docker run --rm --network kind -e K6_CSV_TIME_FORMAT=unix_milli -e RATE=50 -e DURATION="$1" -e NOREUSE="$NOREUSE" \
    -v "$PWD/k6:/scripts:ro" -v "$PWD/out:/out" grafana/k6:2.3.0 \
    run -q -o "csv=/out/$OUT.csv" /scripts/load.js > "out/$OUT.k6.txt" 2>&1 &
  K6PID=$!
  sleep 3; mark load-start
  watch_term & 
}

case $NAME in
recreate|rolling|rolling-prestop)
  reset "deploy-$NAME.yaml"
  load 60s; sleep 10
  mark deploy-v2; $K set env deploy/web VERSION=v2 >/dev/null
  $K rollout status deploy/web --timeout=180s >/dev/null; mark rollout-done
  wait_all v2; mark all-v2
  wait $K6PID ;;
rolling-undo)   # UNDO_MANIFEST 로 Deployment 를 바꿀 수 있다 (기본: preStop 5초)
  reset "${UNDO_MANIFEST:-deploy-rolling-prestop.yaml}"
  $K set env deploy/web VERSION=v2 >/dev/null; $K rollout status deploy/web >/dev/null; wait_all v2
  load 60s; sleep 10
  mark undo; $K rollout undo deploy/web >/dev/null
  $K rollout status deploy/web --timeout=180s >/dev/null; mark rollout-done
  wait_all v1; mark all-v1
  wait $K6PID ;;
bluegreen)
  reset rollout-bluegreen.yaml
  load 100s; sleep 10
  mark deploy-v2; setver v2
  wait_phase Paused; mark preview-ready
  sleep 5
  mark promote; $AR promote web >/dev/null
  wait_all v2; mark all-v2
  sleep 20
  mark undo; $AR undo web >/dev/null
  wait_all v1; mark all-v1
  wait $K6PID ;;
bg-undo-late)
  reset rollout-bluegreen.yaml
  setver v2; wait_phase Paused; $AR promote web >/dev/null; wait_all v2
  echo "scaleDownDelaySeconds(60초)가 지나 옛 ReplicaSet 이 0 이 될 때까지 기다린다"; sleep 70
  load 80s; sleep 10
  mark undo; $AR undo web >/dev/null
  wait_phase Paused; mark paused-again
  mark promote; $AR promote web >/dev/null
  wait_all v1; mark all-v1
  wait $K6PID ;;
bg-keepalive)   # 승격만 하고 되돌리지 않는다. 연결을 재사용하는 클라이언트가 언제 v2 로 넘어가는지 본다
  reset rollout-bluegreen.yaml
  load 110s; sleep 10
  mark deploy-v2; setver v2
  wait_phase Paused; mark preview-ready
  mark promote; $AR promote web >/dev/null
  wait_all v2; mark all-v2
  wait $K6PID ;;
highlander-delay0)   # scaleDownDelaySeconds: 0 이면 옛 ReplicaSet 이 바로 줄어드는가
  reset rollout-highlander-delay0.yaml
  load 90s; sleep 10
  mark deploy-v2; setver v2
  wait_all v2; mark all-v2
  wait $K6PID ;;
highlander)
  reset rollout-highlander.yaml
  load 60s; sleep 10
  mark deploy-v2; setver v2
  wait_all v2; mark all-v2
  wait $K6PID ;;
*) echo "unknown scenario"; exit 1 ;;
esac
$K get rs -o wide > "out/$OUT.rs.txt"
python3 scripts/analyze.py "$OUT" | tee "results/$OUT.txt"
