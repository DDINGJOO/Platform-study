#!/usr/bin/env bash
# 두 번째 클러스터에서 e1, e2-kill-all-pdb, e4, e5 를 차례로 다시 돌린다.
# 노트북 덮개가 닫힌 채 배터리로 돌면 시스템이 잠들어 실행이 끊기므로, 그 상태면 풀릴 때까지 기다렸다 시작한다.
# 실행마다 5초 판정 사이 공백(> 8초)을 검사해 공백이 있으면 results/aborted/ 로 옮기고 다시 돌린다(최대 3번).
set -uo pipefail
cd "$(dirname "$0")/.."
LOG=results/raw/rerun.log
mkdir -p results/raw results/aborted
log(){ echo "[$(date +%H:%M:%S)] $*" | tee -a "$LOG"; }
awake_ok(){
  ioreg -r -k AppleClamshellState -d 4 | grep -q '"AppleClamshellState" = No' && return 0
  pmset -g batt | grep -q "AC Power" && return 0
  return 1
}
wait_awake(){ until awake_ok; do sleep 30; done; }
# 같은 Docker Desktop 을 쓰는 실습-1(ir-01-alert-noise)의 재실행이 끝날 때까지 기다린다(측정끼리 부하를 주지 않게)
i1_busy(){
  pgrep -f 'ir-01-alert-noise.*rerun.sh' >/dev/null && return 0
  [ "$(docker ps -q --filter name=ir-01-alert-noise | wc -l | tr -d ' ')" != "0" ] && return 0
  return 1
}
wait_i1(){ while i1_busy; do sleep 30; done; }
k(){ kubectl --context kind-ir-03 -n ir03 "$@"; }
restarts(){ kubectl --context kind-ir-03 get pods -A --no-headers 2>/dev/null | awk '$1=="kube-system"||$1=="chaos-mesh"{s+=$5} END{print s+0}'; }
gap_free(){ python3 - "$1" <<'PY'
import sys
ts=[int(l.split('\t')[0]) for l in open(sys.argv[1]).read().splitlines()[1:]]
sys.exit(0 if all(b-a<=8 for a,b in zip(ts,ts[1:])) else 1)
PY
}
pf(){ pkill -f 'port-forward svc/prometheus 29090' 2>/dev/null; sleep 1
      (kubectl --context kind-ir-03 -n ir03 port-forward svc/prometheus 29090:9090 >/dev/null 2>&1 &); sleep 3; }
run(){  # run <이름> <카오스> <관찰초> [--no-abort]
  local name=$1 chaos=$2 obs=$3 extra=${4:-}
  for try in 1 2 3; do
    wait_awake; pf
    local r0; r0=$(restarts)
    log "start $name (try $try) restarts=$r0"
    caffeinate -s -i python3 -u scripts/experiment.py "$name" "$chaos" --baseline 30 --observe "$obs" --recover 30 $extra >> "$LOG" 2>&1
    local rc=$? r1; r1=$(restarts)
    log "end $name rc=$rc restarts=$r1"
    if [ $rc -eq 2 ]; then mv "results/$name.tsv" "results/aborted/$name-baseline-refused-try$try.tsv"; sleep 20; continue; fi
    if gap_free "results/$name.tsv" && [ "$r0" = "$r1" ]; then return 0; fi
    log "discard $name: gap or control-plane restart"
    mv "results/$name.tsv" "results/aborted/$name-try$try.tsv"
    python3 - "$name" <<'PY'
import sys
n=sys.argv[1]; s=open('results/summary.txt').read()
i=s.rfind('== '+n+'  ')
if i>=0:
    j=s.find('== ',i+3); s=s[:i]+(s[j:] if j>=0 else '')
open('results/summary.txt','w').write(s)
PY
    sleep 20
  done
  log "GAVE UP $name"; return 1
}

log "waiting: lid/power and ir-01 rerun"
until awake_ok && ! i1_busy; do sleep 30; done
log "awake and ir-01 idle. creating cluster"
caffeinate -s -i ./scripts/up.sh >> "$LOG" 2>&1 || { log "up failed"; exit 1; }
sleep 60   # 앱이 뜨고 지표가 쌓이게

run e1-pod-kill-naive chaos/01-pod-kill-stock-one.yaml 120 --no-abort
./scripts/fix.sh readiness >> "$LOG" 2>&1; sleep 40
run e1-pod-kill-readiness chaos/01-pod-kill-stock-one.yaml 120 --no-abort

k apply -f k8s/20-pdb-stock.yaml >> "$LOG" 2>&1; k get pdb stock >> "$LOG" 2>&1
run e2-kill-all-pdb chaos/07-pod-kill-stock-all-pdb.yaml 60
k get pdb stock >> "$LOG" 2>&1
k get events --sort-by=.lastTimestamp 2>/dev/null | grep -E 'pod-kill-stock-all-pdb|Killing' | tail -12 > results/raw/e2-kill-all-pdb-kills.txt
k delete -f k8s/20-pdb-stock.yaml >> "$LOG" 2>&1; sleep 30

run e4-loss-one chaos/05-loss-stock-one.yaml 60 --no-abort
./scripts/fix.sh retry-only >> "$LOG" 2>&1; sleep 40
run e4-loss-one-retry-only chaos/05-loss-stock-one.yaml 60 --no-abort
./scripts/fix.sh retry >> "$LOG" 2>&1; sleep 40
run e4-loss-one-retry300ms chaos/05-loss-stock-one.yaml 60 --no-abort

run e5-stress-front-one chaos/06-stress-front-one.yaml 60 --no-abort
T=$(( $(date +%s) - 33 ))   # 카오스를 걷은 시각 근처(회복 구간 30초 + 여유)
{ for qq in 'histogram_quantile(0.99, sum by (pod,le)(rate(app_request_seconds_bucket{tier="front"}[45s])))' \
            'histogram_quantile(0.5, sum by (pod,le)(rate(app_request_seconds_bucket{tier="front"}[45s])))'; do
    echo "# $qq"
    curl -s localhost:29090/api/v1/query --data-urlencode "query=$qq" --data-urlencode "time=$T" |
      python3 -c "import json,sys;[print(r['metric']['pod'],round(float(r['value'][1])*1000,1),'ms') for r in json.load(sys.stdin)['data']['result']]"
  done
  echo "# 부하 대상: $(grep -o 'ir03/front[^ ]*' results/raw/e5-stress-front-one-chaos.yaml.txt | head -1)"
} > results/e5-stress-front-perpod.txt

run e1-pod-kill-fixed chaos/01-pod-kill-stock-one.yaml 120 --no-abort

kubectl --context kind-ir-03 get pods -A --no-headers | awk '$1=="kube-system"||$1=="chaos-mesh"{print $1,$2,$5}' > results/raw/final-restarts.txt
log "all done"
./scripts/down.sh >> "$LOG" 2>&1
log "cluster deleted"
