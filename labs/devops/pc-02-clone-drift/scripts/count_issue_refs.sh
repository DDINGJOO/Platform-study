#!/usr/bin/env bash
# 창 안 머지 아닌 커밋 중 메시지에 gh-<숫자> 가 있는 커밋 수(대소문자 무시)
#   WORK=... ./scripts/count_issue_refs.sh v6.1.0 v6.2.0
set -euo pipefail
R="${WORK:?}/src/repo"
git -C "$R" log --no-merges --format=%B%x00 "$1..$2" | python3 -c '
import sys, re
m = [x for x in sys.stdin.read().split("\0") if x.strip()]
n = sum(1 for x in m if re.search(r"gh-[0-9]", x, re.I))
print(f"commits={len(m)} with_gh_ref={n} ({n/len(m):.1%})")'
