#!/usr/bin/env bash
# MySQL 8.4 를 띄우고 세 바퀴 돈 뒤 요약을 만든다. 끝나면 docker compose down -v 로 내린다.
set -u
cd "$(dirname "$0")/.."
docker compose up -d --wait
for r in 1 2 3; do scripts/run.sh "$r"; done
python3 scripts/summarize.py > results/summary.txt
cat results/summary.txt
