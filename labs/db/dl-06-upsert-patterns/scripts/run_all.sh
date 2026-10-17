#!/usr/bin/env bash
# 전체 실행. MySQL(127.0.0.1:39060)을 띄우고 RUNS 바퀴(기본 3) 돈다. 출력은 out/ 에 남는다.
#  바퀴마다: 7개 패턴 x RR/RC 를 4건 동시 x 90 라운드(360건), 재시도 2종, Spring ① 2종
#  한 번만: 잠금 발자국(footprint), 교착 직전 data_locks, @Retryable 순서
set -euo pipefail
cd "$(dirname "$0")/.."
J="java -jar app/build/libs/upsert.jar"
RUNS=${RUNS:-3}
ROUNDS=${ROUNDS:-90}
mkdir -p out
docker compose up -d --wait
for r in $(seq 1 "$RUNS"); do
  for iso in RR RC; do
    for p in p1 p2 p2a p3 p4 p4b p5; do
      $J bench "$p" "$iso" "$ROUNDS" | tee "out/bench-$p-$iso-r$r.txt"
    done
  done
  for p in p1 p5; do
    $J retry "$p" RR "$ROUNDS" | tee "out/retry-$p-RR-r$r.txt"
  done
  $J spring plain "$ROUNDS" | tee "out/spring-plain-r$r.txt"
  $J spring retry "$ROUNDS" | tee "out/spring-retry-r$r.txt"
done
for p in p1 p2 p3 p4 p5; do
  $J footprint "$p" RR | tee "out/footprint-$p-RR.txt"
done
$J footprint p5 RC | tee out/footprint-p5-RC.txt
$J footprint p1 RC | tee out/footprint-p1-RC.txt
$J deadlock p1 RR | tee out/deadlock-p1-RR.txt
$J deadlock p5 RR | tee out/deadlock-p5-RR.txt
$J deadlock p5 RC | tee out/deadlock-p5-RC.txt
$J order | tee out/order.txt
docker compose exec -T mysql mysql -uroot -plabroot -N -e "SELECT VERSION(); SELECT @@transaction_isolation, @@innodb_lock_wait_timeout, @@innodb_deadlock_detect" 2>/dev/null | tee out/server.txt
