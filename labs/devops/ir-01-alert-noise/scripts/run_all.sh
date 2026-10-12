#!/bin/sh
# 글에 쓴 시나리오를 차례로 돌린다(약 90분). db 를 6분 멈추고 7분 지켜본다.
set -e
cd "$(dirname "$0")/.."
for s in a-defaults b-nogroup c-group d-inhibit e-route; do
  python3 scripts/run_scenario.py "$s" "$s.yml" 360 420
done
python3 scripts/run_scenario.py g-repeat g-repeat.yml 480 150
python3 scripts/summarize.py
