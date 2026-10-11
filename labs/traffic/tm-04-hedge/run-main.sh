#!/bin/sh
# 실습-4 본 실행: 같은 백엔드(2%가 300ms 더 느림)에 정책 셋을 차례로 2분씩, 초당 200건.
set -e
cd "$(dirname "$0")"
docker compose --profile load run --rm -e TARGET=/plain -e RATE=200 -e DURATION=30s -e NAME=warmup load
for p in plain hedge retry; do
  date -u +"%H:%M:%S start $p"
  docker compose --profile load run --rm -e TARGET=/$p -e RATE=200 -e DURATION=120s load
  sleep 20
done
date -u +"%H:%M:%S end"
