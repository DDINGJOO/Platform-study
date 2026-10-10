"""최근 N초의 주문 트레이스를 모아 구간별 걸린 시간의 중앙값과 p90 을 낸다.
사용: python3 breakdown.py [초] [끝난 지 몇 초 전까지]   (기본 40 0)"""
import base64, json, os, sys, time, urllib.parse, urllib.request
from collections import defaultdict

TEMPO = os.environ.get("TEMPO_URL", "http://localhost:25001")
S = int(sys.argv[1]) if len(sys.argv) > 1 else 40
E = int(sys.argv[2]) if len(sys.argv) > 2 else 0

def get(path):
    with urllib.request.urlopen(TEMPO + path) as r:
        return json.load(r)

now = int(time.time())
q = urllib.parse.quote('{resource.service.name="order" && kind=server}')
traces = get(f"/api/search?q={q}&limit=5000&start={now - S}&end={now - E}")["traces"]
rows = defaultdict(list)
for t in traces:
    spans = []
    for b in get(f"/api/traces/{t['traceID'].rjust(32, '0')}")["batches"]:
        svc = next(a["value"]["stringValue"] for a in b["resource"]["attributes"] if a["key"] == "service.name")
        for ss in b["scopeSpans"]:
            for s in ss["spans"]:
                spans.append((svc, s["name"], int(s["startTimeUnixNano"]), int(s["endTimeUnixNano"])))
    by = {(sv, n): (st, en) for sv, n, st, en in spans}
    for k, (st, en) in by.items():
        rows[f"{k[0]} {k[1]}"].append((en - st) / 1e6)
    if ("order", "GET") in by and ("inventory", "GET /stock/{sku}") in by:
        rows["(order GET 시작 → inventory 서버 스팬 시작)"].append((by[("inventory", "GET /stock/{sku}")][0] - by[("order", "GET")][0]) / 1e6)
print(f"주문 트레이스 {len(traces)}개")
for k, v in sorted(rows.items(), key=lambda kv: -sorted(kv[1])[len(kv[1]) // 2]):
    v.sort()
    print(f"  {k:<44} {len(v):4d}건  중앙값 {v[len(v)//2]:8.1f}ms  p90 {v[int(len(v)*0.9)]:8.1f}ms")
