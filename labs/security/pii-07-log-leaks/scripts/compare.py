#!/usr/bin/env python3
"""두 실행의 로그를 경로별로 위아래에 붙여 보여 준다. 새는 쪽은 값이 남은 줄만, 막은 쪽은 스택 줄을 뺀 전부.
사용법: compare.py out/d0-none.log out/d10-all.log"""
import re, sys
sys.path.insert(0, __import__("os").path.dirname(__file__))
from leaks import hits

def sections(path):
    out, cur = {}, None
    for line in open(path, encoding="utf-8"):
        line = line.rstrip("\n")
        if m := re.match(r"### (P\d) (.*)", line):
            cur = m.group(1); out[cur] = {"title": m.group(2), "lines": []}; continue
        if line.startswith("### END"): cur = None; continue
        if cur and not line.startswith("\tat ") and not line.startswith("\t..."):
            out[cur]["lines"].append(line)
    return out

def short(l, w=106):
    l = re.sub(r"((?:\[0x[0-9a-f]+\])+)", lambda m: f"[0x..×{m.group(1).count('[')}바이트]", l)
    l = l.replace("org.h2.jdbc.JdbcSQLIntegrityConstraintViolationException", "JdbcSQLIntegrity…Exception")
    l = re.sub(r'Unique index or primary key violation: "PUBLIC\.(\w+)_INDEX_\d+ ON .*?VALUES', r'Unique … "\1" … VALUES', l)
    return l if len(l) <= w else l[: w - 1] + "…"

a, b = sections(sys.argv[1]), sections(sys.argv[2])
for p in sorted(a):
    la = [l for l in a[p]["lines"] if hits(l)]
    lb = b[p]["lines"]
    nb = sum(len(hits(l)) for l in lb)
    print(f"── {p[1]} {a[p]['title']}")
    print(f"  ✗ 새는 쪽  값 {sum(len(hits(l)) for l in la)}개")
    for l in la[:3]: print("    " + short(l))
    if len(la) > 3: print(f"    … 외 {len(la) - 3}줄")
    print(f"  ✓ 막은 쪽  값 {nb}개")
    for l in lb[:12 if p == 'P5' else 4]:
        print(("  ! " if hits(l) else "    ") + short(l))
