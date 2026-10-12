#!/usr/bin/env bash
# 실험에서 깨진 가설을 고치는 단계. 인자: readiness | retry-only | retry | naive(처음 상태로 되돌린다)
set -euo pipefail
cd "$(dirname "$0")/.."
K="kubectl --context kind-ir-03 -n ir03"
case "$1" in
  readiness)
    for d in stock front; do $K patch deploy $d --type strategic --patch-file k8s/10-readiness.yaml; done ;;
  retry-only)
    # 고친 것 2(첫 시도): 실패하면 한 번 더 부른다. 타임아웃은 1초 그대로
    $K set env deploy/front RETRIES=1 ;;
  retry)
    # 고친 것 2: stock 호출 한 번을 300ms 에서 끊고, 실패하면 한 번 더 부른다(새 연결이라 다른 파드로 갈 수 있다)
    $K set env deploy/front STOCK_TIMEOUT_S=0.3 RETRIES=1 ;;
  naive)
    $K apply -f k8s/00-base.yaml ;;
  *) echo "readiness | retry-only | retry | naive"; exit 1 ;;
esac
for d in stock front; do $K rollout status deploy/$d --timeout=180s; done
