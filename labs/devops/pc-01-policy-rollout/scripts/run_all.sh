#!/bin/bash
# 네 방식을 번갈아 세 번씩 돌린다. 이름: <방식>-<회차>
set -e
cd "$(dirname "$0")/.."
for n in 1 2 3; do
  for arm in lib sidecar dyn upgrade; do
    ./scripts/run.sh $arm $arm-$n > out/$arm-$n.log 2>&1
    echo "finished $arm-$n"
  done
done
