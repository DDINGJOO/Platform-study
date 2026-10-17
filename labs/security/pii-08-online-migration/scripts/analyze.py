#!/usr/bin/env python3
"""요청 원자료(out/<시나리오>-req.csv)에서 실패·값 틀림이 어느 단계, 어느 버전, 어떤 요청에서 났는지 센다."""
import collections, csv, sys

rows = list(csv.DictReader(open(sys.argv[1], encoding="utf-8")))
bad = collections.Counter()
for r in rows:
    if r["verdict"] != "ok":
        bad[(r["phase"], r["version"], r["op"], r["verdict"])] += 1
if bad:
    print("not-ok by phase/version/op:")
    for (ph, v, op, vd), n in sorted(bad.items()):
        print("  %-26s %-7s %-9s %-9s %6d" % (ph, v, op, vd, n))
else:
    print("not-ok by phase/version/op: none")

if "--latency" in sys.argv:
    lat = collections.defaultdict(list)
    for r in rows:
        if r["op"] in ("login", "update"):
            lat[r["phase"]].append(float(r["ms"]))
    print("write latency (login+update) ms:")
    print("  %-16s %6s %7s %7s %8s %6s" % ("phase", "n", "p50", "p99", "max", ">1s"))
    for ph, xs in lat.items():
        xs.sort()
        q = lambda f: xs[min(len(xs) - 1, int(len(xs) * f))]
        print("  %-16s %6d %7.1f %7.1f %8.1f %6d" % (ph, len(xs), q(0.5), q(0.99), xs[-1], sum(x > 1000 for x in xs)))
