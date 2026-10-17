#!/usr/bin/env bash
# 전체 실행: 세 바퀴. 바퀴마다 10만 행, 1만 행, 5만 행 순서로 새로 시드하고 잰다.
# 5만 행에서는 demo(findBy 결과), freq(빈도), rotate(키 회전)까지 돈다. 출력은 out/ 에 남는다.
set -euo pipefail
cd "$(dirname "$0")/.."
J="java -Xmx3g --sun-misc-unsafe-memory-access=allow -jar app/build/libs/lookup.jar"
ROUNDS=${ROUNDS:-3}
mkdir -p out
docker compose up -d --wait
for r in $(seq 1 "$ROUNDS"); do
  for n in 100000 10000 50000; do
    $J seed "$n"   | tee "out/seed-$n-r$r.txt"
    $J bench 200   | tee "out/bench-$n-r$r.txt"
    if [ "$n" = 50000 ]; then
      $J demo --logging.level.org.hibernate.SQL=debug --logging.level.org.hibernate.orm.jdbc.bind=trace > "out/demo-trace-r$r.txt" 2>&1 || true
      $J demo        | tee "out/demo-r$r.txt"
      $J freq        | tee "out/freq-r$r.txt"
      $J rotate      | tee "out/rotate-r$r.txt"
    fi
  done
done
$J ivreuse | tee out/ivreuse.txt
