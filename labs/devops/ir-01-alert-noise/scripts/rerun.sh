#!/bin/sh
# 첫 실행에서 믿을 수 없게 된 시나리오를 다시 돌린다. summarize 가 "!!" 를 찍으면(호스트가 잠들어 폴링이 끊기는 등)
# 그 결과를 results/aborted/ 로 옮기고 같은 시나리오를 다시 돌린다. 시나리오마다 최대 6번
cd "$(dirname "$0")/.."
awake_ok() {  # macOS: 덮개가 닫힌 채 배터리로 돌면 caffeinate 로도 잠드는 것을 막지 못한다. 덮개가 열렸거나 전원이 꽂혔을 때만 돌린다
  command -v ioreg >/dev/null || return 0
  ioreg -r -k AppleClamshellState -d 4 | grep -q '"AppleClamshellState" = No' && return 0
  pmset -g batt | grep -q "AC Power" && return 0
  return 1
}
run() {  # 이름 설정 멈춤초 관찰초
  n=1
  while [ $n -le 6 ]; do
    # 조건이 3분 연속 이어질 때만 시작한다(잠깐 덮개를 열었다 닫으면 실행이 버려진다). 스택은 run_scenario.py 가 띄운다
    ok=0
    while [ $ok -lt 3 ]; do
      if awake_ok; then ok=$((ok+1)); else ok=0; echo "[$1] 덮개 닫힘 + 배터리, 기다린다"; fi
      [ $ok -lt 3 ] && sleep 60
    done
    python3 scripts/run_scenario.py "$1" "$2" "$3" "$4" || true
    python3 scripts/summarize.py "$1" > /dev/null
    if ! grep -q '^!!' "results/$1.txt"; then echo "[$1] 깨끗한 실행 (시도 $n)"; return; fi
    k=2; while [ -e "results/aborted/run$k-$1.txt" ]; do k=$((k+1)); done
    mv "results/$1.txt" "results/aborted/run$k-$1.txt"
    echo "[$1] 믿을 수 없는 실행, 다시 (시도 $n)"
    n=$((n+1))
  done
}
for s in ${SCENARIOS:-b-nogroup c-group d-inhibit e-route}; do
  run "$s" "$s.yml" 360 420
done
run g-repeat g-repeat.yml 480 150
