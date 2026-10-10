#!/usr/bin/env bash
# 시나리오 2: 앱이 사라진다. 두 Deployment 를 replicas=0 으로 줄이고, HOLD 초(기본 400) 뒤에 1 로 되돌린다.
set -euo pipefail
K="kubectl --context kind-obs-lab-metrics-02 -n obs"
echo "scale0 $(date +%s) $(date +%T)"
$K scale deploy pull-app push-app --replicas=0 >/dev/null
sleep "${HOLD:-400}"
$K scale deploy pull-app push-app --replicas=1 >/dev/null
echo "scale1 $(date +%s) $(date +%T)"
