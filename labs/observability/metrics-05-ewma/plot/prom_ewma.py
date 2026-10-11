"""프로메테우스에 남은 누적 카운트만으로 드롭위저드 m1/m5/m15 를 다시 계산해 본다.

5초 간격으로 긁어 간 lab_events_total 의 증가분을 5초로 나눠 '5초 비율'을 만들고,
드롭위저드와 같은 식(rate += alpha * (instant - rate))을 그대로 돌린다.
같은 시각에 긁어 간 lab_ewma_rate{meter="early"} 와 비교한다. 표준 라이브러리만 쓴다.

사용: python3 plot/prom_ewma.py [프로메테우스 주소, 기본 http://localhost:23390]
"""
import json, math, sys, urllib.parse, urllib.request

PROM = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:23390"

def q(expr, start, end, step=5):
    u = f"{PROM}/api/v1/query_range?" + urllib.parse.urlencode({"query": expr, "start": start, "end": end, "step": step})
    r = json.load(urllib.request.urlopen(u))["data"]["result"]
    return {float(t): float(v) for t, v in r[0]["values"]} if r else {}

now = json.load(urllib.request.urlopen(f"{PROM}/api/v1/query?query=time()"))["data"]["result"][0]
end = float(now)
start = end - 3 * 3600
cnt = q("lab_events_total", start, end)
ts = sorted(cnt)
start = ts[0]
real = {k: q(f'lab_ewma_rate{{meter="early",window="{k}"}}', start, end) for k in ("m1", "m5", "m15")}

alpha = {"m1": 1 - math.exp(-5 / 60), "m5": 1 - math.exp(-5 / 300), "m15": 1 - math.exp(-5 / 900)}
est = {k: {} for k in alpha}
rate = {k: None for k in alpha}
for a, b in zip(ts, ts[1:]):
    inst = (cnt[b] - cnt[a]) / (b - a)
    for k in alpha:
        rate[k] = inst if rate[k] is None else rate[k] + alpha[k] * (inst - rate[k])
        est[k][b] = rate[k]

print(f"점 {len(ts)}개, {(ts[-1]-ts[0])/60:.1f}분")
for k in alpha:
    diffs = [abs(est[k][t] - real[k][t]) for t in est[k] if t in real[k] and t - ts[0] > 30]
    big = max(diffs)
    print(f"{k}: 비교한 점 {len(diffs)}개, 평균 |차이| {sum(diffs)/len(diffs):.3f}, 최대 |차이| {big:.3f} (초당 건수)")
# 몇 시점 표본
for k in ("m1", "m15"):
    pts = [t for t in est[k] if t in real[k]]
    for t in pts[::len(pts)//6]:
        print(f"  {k} +{(t-ts[0])/60:5.1f}분  카운트로 계산 {est[k][t]:7.3f}  Meter 가 낸 값 {real[k][t]:7.3f}")
