"""실습-2 결과 정리. 표준 라이브러리만.

  python3 analyze.py out/run.csv --prom http://localhost:32090 [--from <unix초> --to <unix초>]

1) 경고: Prometheus 의 ALERTS 시계열을 평가 간격(2초)으로 받아, 서비스·경고마다 꺼짐 -> 켜짐 횟수와 켜져 있던 시간을 센다
2) SLI 흔들림: CSV 로 2분 창(실제 1시간에 해당)마다 SLI 를 계산해 범위를 본다
3) 지연: lat-ln, lat-bi 의 앞 절반으로 평균+3σ 를 정하고 뒤 절반에서 넘는 비율을 센다
4) 시간 기준과 요청 기준: 1분 평균 지연 시계열의 p90 과 요청 지연의 p90
"""
import argparse
import csv
import json
import math
import statistics as st
import urllib.parse
import urllib.request
from collections import defaultdict

ap = argparse.ArgumentParser()
ap.add_argument("csv")
ap.add_argument("--prom", default="http://localhost:32090")
ap.add_argument("--from", dest="t0", type=float)
ap.add_argument("--to", dest="t1", type=float)
ap.add_argument("--skip", type=float, default=720, help="경고 집계에서 앞부분 몇 초를 뺄지(가장 긴 창 12분이 찰 때까지)")
a = ap.parse_args()

rows = sorted((float(r["ts"]), r["svc"], int(r["code"]), float(r["latency_ms"])) for r in csv.DictReader(open(a.csv)))
t0 = a.t0 or rows[0][0]
t1 = a.t1 or rows[-1][0]
print(f"CSV {a.csv}: {len(rows)}건, {t1 - t0:.0f}초")


def pct(xs, p):
    s = sorted(xs)
    k = (len(s) - 1) * p
    f = math.floor(k)
    return s[f] + (s[min(f + 1, len(s) - 1)] - s[f]) * (k - f)


# 1) 경고
try:
    a0 = t0 + a.skip
    url = a.prom + "/api/v1/query_range?" + urllib.parse.urlencode(
        {"query": "ALERTS{alertstate=\"firing\"}", "start": a0, "end": t1, "step": "2s"})
    res = json.load(urllib.request.urlopen(url))["data"]["result"]
    steps = int((t1 - a0) // 2) + 1
    print(f"\n[경고] 집계 구간 {t1 - a0:.0f}초 (= 실제 창 기준 {(t1 - a0) * 30 / 3600:.1f}시간), 앞 {a.skip:.0f}초는 창이 덜 차서 뺌")
    table = {}
    for s in res:
        m = s["metric"]
        on = set(round((float(t) - a0) / 2) for t, _ in s["values"])
        rises = sum(1 for k in on if k - 1 not in on)
        table[(m["route"], m["alertname"])] = (rises, len(on) * 2)
    for svc in ("e1", "e10", "e100", "h1", "h10", "h100"):
        line = []
        for al in ("FastBurn", "SlowBurn"):
            r, sec = table.get((f"/api/{svc}", al), (0, 0))
            line.append(f"{al} 켜짐 {r:3d}회 / 켜진 시간 {sec:5d}초({100 * sec / (t1 - a0):5.1f}%)")
        print(f"  {svc:5s} " + "  ".join(line))
except Exception as e:
    print("Prometheus 조회 실패:", e)

# 2) SLI 흔들림: 2분 창
print("\n[SLI 흔들림] 겹치지 않는 2분 창(실제 1시간에 해당)마다 SLI")
for svc in ("e1", "e10", "e100", "h1", "h10", "h100"):
    win = defaultdict(lambda: [0, 0])
    for ts, s, code, _ in rows:
        if s == svc:
            k = int((ts - t0) // 120)
            win[k][0] += 1
            win[k][1] += code >= 500 or code < 0
    ks = sorted(k for k in win if (k + 1) * 120 <= t1 - t0)
    slis = [100 * (1 - win[k][1] / win[k][0]) for k in ks if win[k][0]]
    tot = sum(win[k][0] for k in ks); bad = sum(win[k][1] for k in ks)
    zero = sum(1 for k in ks if win[k][1] == 0)
    print(f"  {svc:5s} 창 {len(ks)}개, 창당 요청 평균 {tot / len(ks):7.1f}, 전체 SLI {100 * (1 - bad / tot):.3f}%, "
          f"창별 SLI 최소 {min(slis):.2f}% 최대 {max(slis):.2f}% 표준편차 {st.pstdev(slis):.3f}%p, 에러 0건 창 {zero}개")

# 3) 지연 평균+3σ
print("\n[평균+3σ] 앞 절반으로 문턱을 정하고 뒤 절반에서 센다 (정규분포라면 0.135%)")
mid = t0 + (t1 - t0) / 2
for svc in ("lat-ln", "lat-bi"):
    fst = [l for ts, s, c, l in rows if s == svc and ts < mid and c == 200]
    snd = [l for ts, s, c, l in rows if s == svc and ts >= mid and c == 200]
    mu, sd, sd0 = st.fmean(fst), st.stdev(fst), st.pstdev(fst)
    thr = mu + 3 * sd
    over = sum(1 for l in snd if l > thr)
    over_same = sum(1 for l in fst if l > thr)
    print(f"  {svc}: 앞 절반 {len(fst)}건 평균 {mu:.1f}ms σ(n-1) {sd:.2f}ms σ(n) {sd0:.2f}ms → 문턱 {thr:.1f}ms")
    print(f"         뒤 절반 {len(snd)}건 중 {over}건 넘음 = {100 * over / len(snd):.3f}%  (같은 앞 절반 안에서는 {100 * over_same / len(fst):.3f}%)")
    print(f"         요청 p50 {pct(fst, .5):.1f} p90 {pct(fst, .9):.1f} p99 {pct(fst, .99):.1f} p99.9 {pct(fst, .999):.1f} ms")

# 4) 1분 평균 시계열의 p90 vs 요청 p90
print("\n[시간 기준 vs 요청 기준] 1분 평균 지연 시계열의 p90 과 전체 요청의 p90")
for svc in ("lat-ln", "lat-bi"):
    per = defaultdict(list)
    for ts, s, c, l in rows:
        if s == svc and c == 200:
            per[int((ts - t0) // 60)].append(l)
    full = [k for k in per if (k + 1) * 60 <= t1 - t0]
    avgs = [st.fmean(per[k]) for k in full]
    alls = [l for k in full for l in per[k]]
    print(f"  {svc}: 1분 평균 {len(avgs)}개의 p90 {pct(avgs, .9):.1f}ms, 최대 {max(avgs):.1f}ms  /  요청 {len(alls)}건의 p90 {pct(alls, .9):.1f}ms, p99 {pct(alls, .99):.1f}ms"
          f"  → 차이 {pct(alls, .9) - pct(avgs, .9):+.1f}ms")

# 5) 적은 기준 표본으로 문턱을 정하면: 앞 절반을 n건씩 잘라 문턱을 만들고 뒤 절반 전체에 댄다
print("\n[적은 기준 표본] 앞 절반을 n건씩 겹치지 않게 잘라 평균+3σ(n-1)를 정하고, 뒤 절반에서 넘는 비율")
for svc in ("lat-ln", "lat-bi"):
    fst = [l for ts, s, c, l in rows if s == svc and ts < mid and c == 200]
    snd = sorted(l for ts, s, c, l in rows if s == svc and ts >= mid and c == 200)
    import bisect
    for n in (30, 100, 1000):
        rates = []
        for k in range(0, min(len(fst) // n, 300)):
            chunk = fst[k * n:(k + 1) * n]
            thr = st.fmean(chunk) + 3 * st.stdev(chunk)
            rates.append(100 * (len(snd) - bisect.bisect_right(snd, thr)) / len(snd))
        rates.sort()
        lo, hi = rates[int(0.05 * len(rates))], rates[int(0.95 * len(rates)) - 1]
        print(f"  {svc} n={n:5d}: 문턱 {len(rates)}개, 넘는 비율 중앙값 {st.median(rates):.3f}%, 5~95% {lo:.3f}% ~ {hi:.3f}%")
