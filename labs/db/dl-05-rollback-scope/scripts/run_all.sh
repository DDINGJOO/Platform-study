#!/usr/bin/env bash
# 스택을 띄우고 CLI 시나리오와 앱 시나리오를 세 바퀴 돌려 out/ 에 저장한다.
set -uo pipefail
cd "$(dirname "$0")/.."
mkdir -p out
docker compose up -d --wait
for r in 1 2 3; do
  for s in s1 s2 s3 s4 s5 s6 s7; do scripts/cli.sh $s > out/cli-$s-r$r.txt 2>&1; done
  scripts/app.sh 39050 versions > out/app-versions-r$r.txt 2>&1
  for k in jdbc repo commit em; do
    for c in 1213 1205; do scripts/app.sh 39050 throw $k $c > out/app-throw-$k-$c-r$r.txt 2>&1; done
  done
  ERRCODES=1 scripts/app.sh 39050 versions > out/app-errcodes-versions-r$r.txt 2>&1
  for c in 1213 1205; do ERRCODES=1 scripts/app.sh 39050 throw jdbc $c > out/app-errcodes-throw-jdbc-$c-r$r.txt 2>&1; done
  for k in jdbc repo; do
    for c in 1213 1205; do scripts/app.sh 39050 catch $k $c > out/app-catch-$k-$c-r$r.txt 2>&1; done
  done
done
