#!/usr/bin/env bash
# 실습 전체. Docker 가 필요한 단계가 섞여 있다. 출력은 out/ 에 남는다.
#   ./scripts/run_all.sh            전부
#   ./scripts/run_all.sh h2|skip|noskip|mysql
set -u
cd "$(dirname "$0")/.."
mkdir -p out
G="./gradlew --console=plain -q"
run() {  # run <이름> <명령...> : 출력과 종료 코드를 out/<이름>.txt 에
  local name=$1; shift
  echo "== $name: $*"
  { echo "\$ $*"; "$@" 2>&1; echo "exit=$?"; } > "out/$name.txt"
  grep -E "PASSED|SKIPPED|FAILED|BUILD|impl=|checkNoSkipped|exit=" "out/$name.txt" | head -20
}
step=${1:-all}

if [[ $step == all || $step == h2 ]]; then
  # 1. H2 MySQL 모드: 고치기 전 코드인데도 초록
  run h2-buggy  ./gradlew --console=plain test --tests lab.H2MysqlModeTest -Pimpl=buggy
  run h2-probe  ./gradlew --console=plain test --tests lab.H2LockProbeTest
fi

if [[ $step == all || $step == skip ]]; then
  # 2. Docker 를 못 찾게 한다: DOCKER_HOST 를 아무도 듣지 않는 포트로
  run a-skip-dockerhost  env DOCKER_HOST=tcp://127.0.0.1:39071 ./gradlew --console=plain test --tests lab.SkippingMysqlTest
  run a-strict-dockerhost env DOCKER_HOST=tcp://127.0.0.1:39071 ./gradlew --console=plain test --tests lab.StrictMysqlTest
  # 3. Docker 는 살아 있는데 Testcontainers 버전이 맞지 않는다
  for v in 1.19.8 1.21.3 1.21.4 2.0.5; do
    run "v-skip-$v"   ./gradlew --console=plain test --tests lab.SkippingMysqlTest -PtcVersion=$v -Pimpl=buggy
  done
  # 3-1. 올릴 수 없을 때: API 버전을 직접 정하면 옛 버전도 붙는가
  run v-skip-1.19.8-api144 ./gradlew --console=plain test --tests lab.SkippingMysqlTest -PtcVersion=1.19.8 -PapiVersion=1.44 -Pimpl=buggy
  run v-strict-1.19.8 ./gradlew --console=plain test --tests lab.StrictMysqlTest -PtcVersion=1.19.8 -Pimpl=buggy
fi

if [[ $step == all || $step == noskip ]]; then
  # 4. skip 0 검사: 같은 skip 이 빌드를 막는다
  run b-noskip-1.19.8 ./gradlew --console=plain test --tests lab.SkippingMysqlTest -PtcVersion=1.19.8 -PnoSkip
  # 5. 조건을 꺼서 skip 대신 실패로: JUnit 의 junit.jupiter.conditions.deactivate
  run b-deactivate-1.19.8 ./gradlew --console=plain test --tests lab.SkippingMysqlTest -PtcVersion=1.19.8 \
      -Pdeactivate='org.testcontainers.*'
fi

if [[ $step == all || $step == mysql ]]; then
  # 6. 실제 MySQL 8.4: 고치기 전 빨간불, 고친 뒤 초록불 (세 바퀴씩)
  for i in 1 2 3; do
    run "c-buggy-r$i" ./gradlew --console=plain test --tests lab.SkippingMysqlTest -Pimpl=buggy -PnoSkip
    run "c-fixed-r$i" ./gradlew --console=plain test --tests lab.SkippingMysqlTest -Pimpl=fixed -PnoSkip
  done
fi
