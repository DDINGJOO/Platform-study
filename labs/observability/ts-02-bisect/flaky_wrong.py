#!/usr/bin/env python3
"""out/flaky.tsv 에서 오답이 범인(613)에서 얼마나 떨어져 있었는지 센다. -> out/flaky-wrong.txt"""
import csv, os
HERE = os.path.dirname(os.path.abspath(__file__))
rows = list(csv.DictReader(open(os.path.join(HERE, "out/flaky.tsv")), delimiter="\t"))
lines = []
for key in sorted(set((r["mode"], r["p"], r["vote"]) for r in rows)):
    w = [int(r["found"]) for r in rows if (r["mode"], r["p"], r["vote"]) == key and r["found"] != "613"]
    if not w:
        lines.append(f"{key} 오답 없음")
        continue
    d = sorted(abs(x - 613) for x in w)
    lines.append(f"{key} 오답 {len(w)}건, 범인과 거리 중앙값 {d[len(d)//2]}, 10 이내 {sum(x <= 10 for x in d)}건, "
                 f"50 이내 {sum(x <= 50 for x in d)}건, 최대 {d[-1]}")
open(os.path.join(HERE, "out/flaky-wrong.txt"), "w").write("\n".join(lines) + "\n")
print("\n".join(lines))
