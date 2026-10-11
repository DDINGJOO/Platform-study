#!/usr/bin/env bash
# 롤아웃 상태를 2초마다 한 줄씩 남긴다. 시각은 배포 시작부터 지난 초.
# 사용: scripts/watch.sh <출력파일> <최대초>
OUT=$1; MAX=${2:-900}; T0=$(date +%s)
while :; do
  T=$(( $(date +%s) - T0 )); [ $T -gt $MAX ] && break
  L=$(kubectl --context kind-ds-02 -n ds02 get rollout demo -o jsonpath='{.status.phase}|{.status.currentStepIndex}|{.status.abort}|{.status.message}' 2>/dev/null)
  P=$(kubectl --context kind-ds-02 -n ds02 get rs -l app=demo -o jsonpath='{range .items[*]}{.metadata.labels.rollouts-pod-template-hash}={.status.readyReplicas}/{.spec.replicas} {end}' 2>/dev/null)
  A=$(kubectl --context kind-ds-02 -n ds02 get analysisrun -o jsonpath='{range .items[*]}{.metadata.name}:{.status.phase} {end}' 2>/dev/null)
  echo "+${T}s $L | $P | $A" >> "$OUT"
  sleep 2
done
