#!/bin/sh
# 같은 장애를 N번 주입해 탐지 시간(주입 → page 알림 수신)이 얼마나 흔들리는지 본다.
# 매 회: 무작위 0~20초 대기 → 주입 → page 알림 수신 즉시 독 제거 → 두 경고의 resolved 알림까지 기다림(다음 회가 새 알림 그룹에서 시작하도록)
#   scripts/ttd-trials.sh <N> [prefix] [시작 회차]
set -e
cd "$(dirname "$0")/.."
N=${1:-5}; P=${2:-trial}; FIRST=${3:-1}
for i in $(seq "$FIRST" "$N"); do
  python3 scripts/gd.py event start "$P-$i"
  sleep $(python3 -c 'import random; print(round(random.uniform(0,20),1))')
  python3 scripts/gd.py inject 900 300
  python3 scripts/gd.py wait OrderErrorRatioHigh firing 600
  python3 scripts/gd.py heal
  # resolved 알림이 8분 안에 안 오면(호스트·Docker VM 이 멈췄던 경우 실제로 있었다) Alertmanager 를 새로 띄워 알림 그룹을 비운다
  python3 scripts/gd.py settle 480 || { docker compose up -d --force-recreate alertmanager; sleep 30; }
  sleep 20
done
python3 scripts/gd.py event start end-of-trials
