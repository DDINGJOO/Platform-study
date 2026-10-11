#!/usr/bin/env bash
# 시나리오 3. 대조군과 나쁜 카나리를 띄운 채(k8s/experiment-lowtraffic.yaml) 부하만 바꿔 가며
# 10분 구간마다 같은 판정을 부른다. 먼저 10분은 프로세스 예열에 쓴다.
# judge 는 port-forward 로 연다: kubectl -n ds02 port-forward svc/judge 25080:80
set -uo pipefail
cd "$(dirname "$0")/.."
mkdir -p results/raw
OUT=results/raw/s3-lowtraffic.jsonl
K="kubectl --context kind-ds-02 -n ds02"
B=$($K get rs -l role=lt-baseline -o jsonpath='{.items[0].metadata.labels.rollouts-pod-template-hash}')
C=$($K get rs -l role=lt-canary -o jsonpath='{.items[0].metadata.labels.rollouts-pod-template-hash}')
judge() {  # $1 = 부하 라벨
  for step in 10 30 60; do
    curl -s "http://localhost:25080/judge?control=$B&experiment=$C&window=600&step=$step&label=rate$1-step$step" \
      | python3 -c "import sys,json;d=json.load(sys.stdin);d['rate']='$1';print(json.dumps(d))" >> $OUT
  done
}
sleep 600                    # 예열(초당 50건)
sleep 600; judge 50
./scripts/load.sh 10; sleep 600; judge 10
./scripts/load.sh 2;  sleep 600; judge 2
./scripts/load.sh 50
echo done >> $OUT.done
