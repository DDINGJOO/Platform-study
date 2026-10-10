"""Tempo 에서 트레이스 하나를 꺼내 스팬을 시작 시각 순으로 찍는다.
사용: python3 show-trace.py [traceID]   (없으면 결제까지 간 최근 트레이스)"""
import json, os, sys, urllib.parse, urllib.request

TEMPO = os.environ.get("TEMPO_URL", "http://localhost:3200")

def get(path):
    with urllib.request.urlopen(TEMPO + path) as r:
        return json.load(r)

if len(sys.argv) > 1:
    tid = sys.argv[1]
else:
    q = urllib.parse.quote('{resource.service.name="payment"}')
    tid = get(f"/api/search?q={q}&limit=1")["traces"][0]["traceID"]

spans = []
for b in get(f"/api/traces/{tid}")["batches"]:
    svc = next(a["value"]["stringValue"] for a in b["resource"]["attributes"] if a["key"] == "service.name")
    for ss in b.get("scopeSpans", []):
        for s in ss["spans"]:
            start, end = int(s["startTimeUnixNano"]), int(s["endTimeUnixNano"])
            spans.append((start, end, svc, s["name"], s["kind"].replace("SPAN_KIND_", ""),
                          ss["scope"]["name"], s["spanId"], s.get("parentSpanId", "")))
spans.sort()
t0 = spans[0][0]
ids = {s[6]: s for s in spans}
def depth(s):
    d = 0
    while s[7] in ids:
        s, d = ids[s[7]], d + 1
    return d
print(f"traceID {tid}")
for s in spans:
    name = "  " * depth(s) + s[3]
    print(f"+{(s[0]-t0)/1e6:6.1f}ms {(s[1]-s[0])/1e6:6.1f}ms  {s[2]:<9} {s[4]:<8} {name:<42} {s[5]}")
