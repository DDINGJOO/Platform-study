#!/usr/bin/env bash
# 롤아웃의 파드 템플릿 env 를 바꿔 새 버전을 배포한다.
# 사용: scripts/deploy.sh <VERSION> [EXTRA_MS] [ERROR_RATE]
set -euo pipefail
V=$1; EXTRA=${2:-0}; ERR=${3:-0}
kubectl --context kind-ds-02 -n ds02 patch rollout demo --type json -p "[
 {\"op\":\"replace\",\"path\":\"/spec/template/spec/containers/0/env\",\"value\":[
  {\"name\":\"VERSION\",\"value\":\"$V\"},
  {\"name\":\"EXTRA_MS\",\"value\":\"$EXTRA\"},
  {\"name\":\"ERROR_RATE\",\"value\":\"$ERR\"},
  {\"name\":\"WARMUP_MS\",\"value\":\"30\"},
  {\"name\":\"WARMUP_TAU_S\",\"value\":\"120\"}]}]"
date -u +%H:%M:%S
