#!/usr/bin/env bash
# 띄우기 → 스키마 → CLI → JDBC 두 모드 → 잠금. 출력은 out/ 에 남는다. 내리는 건 직접: docker compose down -v
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p out
docker compose up -d --wait
docker compose exec -T mysql mysql -uroot -plab lab < sql/schema.sql 2>&1 | grep -v 'Using a password' || true
docker compose exec -T mysql mysql -uroot -plab -N -e "SELECT VERSION(), @@transaction_isolation" 2>&1 | grep -v 'Using a password' | tee out/version.txt
./scripts/cli.sh   | tee out/cli.txt
./scripts/jdbc.sh  | tee out/jdbc.txt
./scripts/locks.sh | tee out/locks.txt
