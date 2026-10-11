#!/usr/bin/env bash
# 부하 생성기를 초당 <RATE> 건으로 다시 띄운다. 사용: scripts/load.sh <RATE>
set -euo pipefail
cd "$(dirname "$0")/.."
K="kubectl --context kind-ds-02 -n ds02"
$K delete job load --ignore-not-found --wait=true
sed "s/value: \"50\"}/value: \"$1\"}/" k8s/load.yaml | $K apply -f -
date -u +%H:%M:%S
