#!/usr/bin/env bash
# co-04-openrewrite 실습 단계. 실습 디렉터리에서 돌린다.
#   ./scripts/lab.sh build      컴파일, 의존성과 JaCoCo 복사
#   ./scripts/lab.sh grep       grep 으로 찾기 (results/grep.txt)
#   ./scripts/lab.sh rewrite N  FindMethods dryRun 을 기본값/matchOverrides 로 N 번씩 (results/rewrite-*)
#   ./scripts/lab.sh notypes    로깅 라이브러리를 클래스패스에서 빼고 dryRunNoFork (results/rewrite-notypes*)
#   ./scripts/lab.sh runtime    JaCoCo 붙인 앱에 k6 60초, 덤프와 XML 리포트 (results/jacoco.xml)
#   ./scripts/lab.sh score      세 방법의 결과를 정답표와 맞춘다
#   ./scripts/lab.sh down
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p results
DC="docker compose"
PATTERN='org.slf4j.Logger info(..)'
REGEX='\b(log|logger|LOG)\.info\('

rewrite_once() {  # $1 이름, $2 matchOverrides, $3 goal, $4 추가 옵션
  local name=$1 mo=$2 goal=$3 extra=${4:-}
  $DC --profile tools run --rm mvn bash -c "
    rm -rf target/rewrite target/site/rewrite
    s=\$(date +%s%N)
    mvn -B $extra rewrite:$goal \
      -Drewrite.activeRecipes=org.openrewrite.java.search.FindMethods \
      -Drewrite.options='methodPattern=$PATTERN,matchOverrides=$mo' \
      -Drewrite.exportDatatables=true > /tmp/rw.log 2>&1; rc=\$?
    e=\$(date +%s%N)
    echo \"ELAPSED_MS \$(( (e - s) / 1000000 )) rc=\$rc\"
    grep -E 'WARNING|ERROR|Total time' /tmp/rw.log | head -40
    mkdir -p /work/results/$name
    cp target/rewrite/rewrite.patch /work/results/$name/ 2>/dev/null || echo 'no patch'
    find target/rewrite -name '*.csv' -exec cp {} /work/results/$name/ \; 2>/dev/null || true
  "
}

case "${1:-}" in
build)
  $DC --profile tools run --rm mvn mvn -B -q clean package
  ;;
grep)
  $DC --profile tools run --rm mvn bash -c "grep -rnE '$REGEX' src/main/java | sed 's#^src/main/java/##'" | tee results/grep.txt
  echo "grep 매치 $(wc -l < results/grep.txt) 줄"
  ;;
rewrite)
  n=${2:-3}
  for i in $(seq 1 "$n"); do
    rewrite_once rewrite-default false dryRun | tee -a results/rewrite-default.log
    rewrite_once rewrite-overrides true dryRun | tee -a results/rewrite-overrides.log
  done
  grep ELAPSED_MS results/rewrite-default.log results/rewrite-overrides.log
  ;;
notypes)
  rewrite_once rewrite-notypes true dryRunNoFork -Dnotypes | tee results/rewrite-notypes.log
  ;;
runtime)
  $DC --profile run up -d app
  $DC --profile run run --rm k6 2>&1 | tail -25 | tee results/k6.txt
  $DC --profile tools run --rm jacoco dump --address app --port 6300 --destfile target/jacoco.exec
  $DC --profile tools run --rm jacoco report target/jacoco.exec --classfiles target/classes \
      --sourcefiles src/main/java --xml target/jacoco.xml --html target/jacoco-html
  cp app/target/jacoco.xml results/jacoco.xml
  $DC --profile run stop app
  ;;
score)
  python3 scripts/score.py
  ;;
down)
  $DC --profile tools --profile run down -v --remove-orphans
  ;;
*)
  sed -n '2,10p' "$0"; exit 1;;
esac
