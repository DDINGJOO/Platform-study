#!/usr/bin/env bash
# 막는 법을 하나씩만 켜고 다섯 경로를 돌린 뒤, 경로별로 남은 줄 수를 센다.
set -euo pipefail
cd "$(dirname "$0")/.."
run() { local n="$1"; shift; ./scripts/run.sh "$n" "$@" >/dev/null; }
run d0-none
run d1-exclude dto=exclude
run d2-include dto=masked
run d3-allow   dto=allow
run d4-msg     mask=MSG_NAIVE
run d5-full    mask=FULL_NAIVE
run d6-wide    mask=FULL_WIDE
run d7-turbo   turbo=true
run d8-wireoff wire=INFO
run d9-code    code=safe
run d10-all    dto=allow code=safe mask=FULL_WIDE wire=INFO turbo=true
python3 scripts/leaks.py out/d0-none.log out/d1-exclude.log out/d2-include.log out/d3-allow.log \
  out/d4-msg.log out/d5-full.log out/d6-wide.log out/d7-turbo.log out/d8-wireoff.log out/d9-code.log out/d10-all.log \
  | tee out/matrix.txt
