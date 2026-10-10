"""사건 시각 전후로 몇 가지 식의 값이 언제 바뀌었는지 1초 간격으로 찍는다.
사용: python3 timeline.py <시작 유닉스초> <끝 유닉스초>      (PROM_URL 기본 http://localhost:21290)
각 줄: 시각(시작 기준 +초)  식  값(없으면 '-')"""
import json, os, sys, time, urllib.parse, urllib.request

PROM = os.environ.get("PROM_URL", "http://localhost:21290")
start, end = int(sys.argv[1]), int(sys.argv[2])
EXPRS = {
    "pull up": 'max(up{job="pull-app"})',
    "pull 시계열": 'count(shop_orders_total{job="pull-app"})',
    "push 시계열(OTLP)": 'count(shop_orders_total{job="push-app"})',
    "push 시계열(Collector :8889)": 'count(shop_orders_total{job="otel-collector"})',
    "push 값(Collector :8889)": 'max(shop_orders_total{job="otel-collector"})',
    "pull 타깃 수": 'count(up{job="pull-app"})',
}
ALERTS = 'ALERTS{alertstate="firing"}'

def rng(q):
    u = f"{PROM}/api/v1/query_range?" + urllib.parse.urlencode({"query": q, "start": start, "end": end, "step": 1})
    return json.load(urllib.request.urlopen(u))["data"]["result"]

def fmt(t):
    return f"+{t - start:4d}s {time.strftime('%H:%M:%S', time.localtime(t))}"

for name, q in EXPRS.items():
    res = rng(q)
    vals = {int(t): v for t, v in res[0]["values"]} if res else {}
    prev = object()
    for t in range(start, end + 1):
        v = vals.get(t, "-")
        if v != prev:
            print(f"{fmt(t)}  {name:28s} {v}")
            prev = v
for s in rng(ALERTS):
    ts = [int(t) for t, _ in s["values"]]
    runs, a = [], ts[0]
    for x, y in zip(ts, ts[1:] + [None]):
        if y is None or y - x > 1:
            runs.append((a, x)); a = y
    for a, b in runs:
        print(f"{fmt(a)}  ALERT {s['metric']['alertname']} 발화 ~ {fmt(b)}")
