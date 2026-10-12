#!/usr/bin/env bash
# co-03-resolution 실습 단계. 실습 디렉터리에서 돌린다.
#   ./scripts/lab.sh repo       합성 저장소 만들기
#   ./scripts/lab.sh resolve    두 도구로 해소하고 실행하기 (results/resolve-*.txt)
#   ./scripts/lab.sh analyze    미사용/미선언 분석 (results/analyze-*.txt)
#   ./scripts/lab.sh bump       b 를 2.0 으로 올려 컴파일 (results/bump-*.txt)
#   ./scripts/lab.sh boot       Spring Boot 측정 (results/boot-*.txt)
#   ./scripts/lab.sh down       컨테이너, 볼륨 정리
set -euo pipefail
cd "$(dirname "$0")/.."
DC="docker compose --profile tools"
MODS="m1 m2 m3 m4 m5 an an-decl"
mkdir -p results

case "${1:-}" in
repo)
  $DC run --rm mvn bash scripts/make-repo.sh | tee results/repo.txt
  ;;

resolve)
  # Maven: 모듈마다 dependency:tree(-Dverbose 로 버려진 버전까지) 와 실행
  $DC run --rm mvn bash -c '
    set -e
    mvn -q -f maven/pom.xml compile >/dev/null
    for m in '"$MODS"'; do
      echo "=== maven $m"
      mvn -q -f maven/pom.xml -pl $m dependency:tree -Dverbose -DoutputFile=/tmp/tree.txt >/dev/null && cat /tmp/tree.txt
      mvn -q -f maven/pom.xml -pl $m dependency:build-classpath -Dmdep.outputFile=/tmp/cp.txt >/dev/null
      java -cp maven/$m/target/classes:$(cat /tmp/cp.txt) lab.co3.Main || echo "RESULT $m EXIT $?"
    done' 2>&1 | tee results/resolve-maven.txt
  # Gradle: runtimeClasspath 해소 결과와 실행
  $DC run --rm gradle bash -c '
    for m in '"$MODS"'; do
      echo "=== gradle $m"
      gradle -q :$m:dependencies --configuration runtimeClasspath | sed -n "/runtimeClasspath/,/^$/p"
      gradle -q :$m:run || echo "RESULT $m EXIT $?"
    done
    echo "=== gradle dependencyInsight m1 c"
    gradle -q :m1:dependencyInsight --dependency lab.co3:c --configuration runtimeClasspath' 2>&1 | tee results/resolve-gradle.txt
  grep -h '^RESULT' results/resolve-maven.txt | sed 's/^RESULT/maven /' > results/resolve-summary.txt
  grep -h '^RESULT' results/resolve-gradle.txt | sed 's/^RESULT/gradle/' >> results/resolve-summary.txt
  cat results/resolve-summary.txt
  ;;

analyze)
  $DC run --rm mvn bash -c '
    mvn -q -f maven/pom.xml compile >/dev/null
    for m in '"$MODS"'; do
      echo "=== maven dependency:analyze $m"
      mvn -f maven/pom.xml -pl $m dependency:analyze 2>&1 | grep -E "WARNING\]|No dependency problems" || true
    done' 2>&1 | tee results/analyze-maven.txt
  $DC run --rm gradle bash -c '
    gradle buildHealth -Pdependency.analysis.print.build.health=true > /tmp/bh.log 2>&1; echo "buildHealth exit $?"
    cat /tmp/bh.log | grep -v "^$" | tail -60
    echo "=== report"
    cat build/reports/dependency-analysis/build-health-report.txt 2>/dev/null || true' 2>&1 | tee results/analyze-gradle.txt
  ;;

bump)
  # 1차 의존성 b 를 2.0 으로 올렸을 때 모듈별 컴파일 결과
  $DC run --rm mvn bash -c '
    for m in '"$MODS"'; do
      if mvn -q -f maven/pom.xml -pl $m -Db.version=2.0 clean compile > /tmp/c.log 2>&1; then
        echo "BUMP maven $m compile OK"
      else
        echo "BUMP maven $m compile FAIL $(grep "ERROR.*\.java" /tmp/c.log | sort -u | wc -l) distinct errors"; grep "ERROR.*\.java" /tmp/c.log | sort -u
      fi
    done' 2>&1 | tee results/bump-maven.txt
  $DC run --rm gradle bash -c '
    for m in '"$MODS"'; do
      if gradle -q -PbVersion=2.0 :$m:compileJava > /tmp/c.log 2>&1; then
        echo "BUMP gradle $m compile OK"
      else
        echo "BUMP gradle $m compile FAIL $(grep "^/.*error:" /tmp/c.log | sort -u | wc -l) distinct errors"; grep "^/.*error:" /tmp/c.log | sort -u
      fi
    done' 2>&1 | tee results/bump-gradle.txt
  ;;

boot)
  python3 scripts/boot.py | tee results/boot.txt
  ;;

down)
  docker compose --profile tools --profile boot down -v --remove-orphans
  ;;
*)
  sed -n '2,10p' "$0"; exit 1;;
esac
