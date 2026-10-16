"""out/<이름>.csv 와 .marks 로 한 실행을 요약한다. 시각은 rollout_start 를 0 으로 한 초.
사용: python3 scripts/analyze.py <이름>...   (결과는 표준 출력. results/ 에 저장은 summarize.sh 가 한다)
"""
import csv, json, sys
from collections import Counter, defaultdict


def load(name):
    marks = []
    for line in open(f"out/{name}.marks"):
        t, *ev = line.split()
        marks.append((float(t), ev))
    t0 = next(t for t, ev in marks if ev[0] == "rollout_start")
    rows = list(csv.DictReader(open(f"out/{name}.csv")))
    return t0, marks, rows


def summarize(name):
    t0, marks, rows = load(name)
    tdone = next(t for t, ev in marks if ev[0] == "rollout_done")
    out = [f"== {name}"]
    # 이벤트 시각
    ev_lines = []
    for t, ev in marks:
        if ev[0] in ("load_start", "load_stop"):
            continue
        ev_lines.append(f"  {t - t0:7.1f}s  {' '.join(ev[:2])}")
    out += ev_lines
    out.append(f"  바꾸기 시작부터 끝까지: {tdone - t0:.1f}s")

    # 응답 분류
    def cls(r):
        s = int(r["status"])
        if s == 0:
            return "연결실패/타임아웃"
        if s == 200:
            return f"200 {r['policy']}"
        return f"{s} {r['policy']}"

    before = [r for r in rows if float(r["t"]) < t0]
    during = [r for r in rows if t0 <= float(r["t"]) <= tdone]
    after = [r for r in rows if float(r["t"]) > tdone]
    for label, rs in (("바꾸기 전", before), ("바꾸는 중", during), ("바꾼 뒤", after)):
        c = Counter(cls(r) for r in rs)
        tot = len(rs)
        parts = ", ".join(f"{k} {v}" for k, v in sorted(c.items()))
        out.append(f"  [{label}] 요청 {tot}: {parts}")

    # 서비스별: 마지막 v1 응답, 첫 v2 응답, 연결 실패 구간
    per = defaultdict(list)
    for r in rows:
        per[r["svc"]].append(r)
    first_v2_all, last_v1_all = [], []
    out.append("  서비스   첫 v2      마지막 v1   v1·v2 섞임   연결실패/503   가장 긴 실패 구간")
    for svc in sorted(per):
        rs = sorted(per[svc], key=lambda r: float(r["t"]))
        v2 = [float(r["t"]) - t0 for r in rs if r["policy"] == "v2"]
        v1 = [float(r["t"]) - t0 for r in rs if r["policy"] == "v1"]
        fv2 = min(v2) if v2 else None
        lv1 = max(v1) if v1 else None
        if fv2 is not None:
            first_v2_all.append(fv2)
        if lv1 is not None:
            last_v1_all.append(lv1)
        mixed = sum(1 for r in rs if fv2 is not None and lv1 is not None and fv2 <= float(r["t"]) - t0 <= lv1)
        bad = [float(r["t"]) - t0 for r in rs if r["status"] == "0" or r["policy"] in ("sidecar-down", "")]
        # 연속 실패 구간의 길이(성공 응답이 끼면 끊는다)
        longest, cur_start, prev_bad = 0.0, None, False
        for r in rs:
            t = float(r["t"]) - t0
            isbad = r["status"] == "0" or r["policy"] in ("sidecar-down", "")
            if isbad and not prev_bad:
                cur_start = t
            if isbad:
                longest = max(longest, t - cur_start)
            prev_bad = isbad
        f = lambda x: "   -   " if x is None else f"{x:7.2f}s"
        out.append(f"  {svc:6} {f(fv2)}   {f(lv1)}   {mixed:6}건      {len(bad):6}건       {longest:.2f}s")
    if first_v2_all and last_v1_all:
        out.append(f"  전체: 첫 v2 {min(first_v2_all):.2f}s, 마지막 v1 {max(last_v1_all):.2f}s, "
                   f"두 정책이 함께 응답한 창 {max(last_v1_all) - min(first_v2_all):.2f}s")
    # 지연
    def pct(xs, p):
        xs = sorted(xs)
        return xs[min(len(xs) - 1, int(len(xs) * p))] if xs else 0
    ok = [int(r["ms"]) for r in rows if r["status"] == "200"]
    out.append(f"  200 응답 지연(부하기 측정) p50 {pct(ok, .5)}ms p99 {pct(ok, .99)}ms")
    try:
        b = json.load(open(f"out/{name}.backend.json"))
        out.append(f"  backend 가 받은 /data {b['data']}건 (그중 503 {b['fail']}건), 부하기 요청 {len(rows)}건")
    except FileNotFoundError:
        pass
    try:
        bef = {l.split()[0]: l.split()[1:] for l in open(f"out/{name}.before")}
        aft = {l.split()[0]: l.split()[1:] for l in open(f"out/{name}.after")}
        changed = [n.strip('/') for n in bef if n in aft and bef[n] != aft[n]]
        new = [n.strip('/') for n in aft if n not in bef]
        out.append(f"  다시 시작한 컨테이너: {len(changed) + len(new)}개 {sorted(changed + new)}")
    except FileNotFoundError:
        pass
    return "\n".join(out)


for n in sys.argv[1:]:
    print(summarize(n))
    print()
