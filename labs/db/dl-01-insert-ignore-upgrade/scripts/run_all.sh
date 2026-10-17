#!/usr/bin/env bash
# 전체 실행: 시나리오 11개 x 격리 수준 2개(RR, RC) x 테이블 2개 x ROUNDS 바퀴. 출력은 out/, 요약은 results/summary.txt
set -euo pipefail
cd "$(dirname "$0")/.."
ROUNDS=${ROUNDS:-3}
mkdir -p out results
docker compose up -d --wait
M="docker compose exec -T -e MYSQL_PWD=labroot mysql mysql -uroot lab"
$M -N -e "SELECT VERSION(), @@transaction_isolation, @@innodb_deadlock_detect, @@innodb_lock_wait_timeout;" | tee out/env.txt
docker version --format 'Docker client {{.Client.Version}}, server {{.Server.Version}}' | tee -a out/env.txt
# SCN="이름 이름" 으로 일부만 돌릴 수 있다. 결과 줄은 out/results.txt 에 덧붙는다
SCN=${SCN:-$(python3 scripts/sessions.py list | awk '{print $1}')}
for r in $(seq 1 "$ROUNDS"); do
  for iso in RR RC; do
    for t in first_visit first_visit_pk; do
      for s in $SCN; do
        f="out/$s-$iso-$t-r$r.txt"
        python3 scripts/sessions.py "$s" "$iso" "$t" > "$f"
        grep '^RESULT' "$f" | sed "s/\$/ round=$r/"
        if [ "$s" = exists-2s ] && [ "$r" = 1 ]; then
          $M -e "SHOW ENGINE INNODB STATUS\G" > "out/innodb-status-$s-$iso-$t.txt"
        fi
      done
    done
  done
done | tee -a out/results.txt
$M -e "SHOW GLOBAL STATUS LIKE 'Innodb_deadlocks'; SELECT NAME, COUNT, STATUS FROM information_schema.INNODB_METRICS WHERE NAME='lock_deadlocks';" | tee out/counters.txt
{
  echo "# MySQL $(cut -f1 out/env.txt), 기본 격리 수준 $(cut -f2 out/env.txt), 바퀴 $ROUNDS"
  sed 's/^RESULT //' out/results.txt | sort -k1,1 -k3,3 -k2,2 -s
} > results/summary.txt
echo "끝. 내리려면: docker compose down -v"
