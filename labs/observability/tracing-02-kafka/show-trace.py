"""Tempo 에서 트레이스를 꺼내 스팬을 시작 시각 순으로 찍는다. 실습-1 스크립트에 링크와 메시징 속성을 더했다.
사용: python3 show-trace.py [traceID | TraceQL]   (없으면 payment 가 들어간 최근 트레이스)"""
import base64, json, os, sys, time, urllib.parse, urllib.request

TEMPO = os.environ.get("TEMPO_URL", "http://localhost:25001")
SHOW = ("messaging.operation.type", "messaging.batch.message_count", "messaging.kafka.message.offset", "thread.name")

def get(path):
    with urllib.request.urlopen(TEMPO + path) as r:
        return json.load(r)

def hx(b64):
    return base64.b64decode(b64).hex() if b64 else ""

def val(v):
    return next(iter(v.values()))

arg = sys.argv[1] if len(sys.argv) > 1 else '{resource.service.name="order" && kind=server}'
if arg.startswith("{"):
    found = get(f"/api/search?q={urllib.parse.quote(arg)}&limit=5000&spss=50&start={int(time.time()) - 600}&end={int(time.time()) + 60}")["traces"]
    tid = max(found, key=lambda t: int(t["startTimeUnixNano"]))["traceID"].rjust(32, "0")   # 가장 최근
else:
    tid = arg.rjust(32, "0")

spans = []
for b in get(f"/api/traces/{tid}")["batches"]:
    svc = next(a["value"]["stringValue"] for a in b["resource"]["attributes"] if a["key"] == "service.name")
    for ss in b.get("scopeSpans", []):
        for s in ss["spans"]:
            attrs = {a["key"]: val(a["value"]) for a in s.get("attributes", [])}
            extra = " ".join(f"{k.split('.')[-1]}={attrs[k]}" for k in SHOW if k in attrs)
            links = [hx(l["traceId"])[:8] + "../" + hx(l["spanId"]) for l in s.get("links", [])]
            spans.append((int(s["startTimeUnixNano"]), int(s["endTimeUnixNano"]), svc, s["name"],
                          s["kind"].replace("SPAN_KIND_", ""), hx(s["spanId"]), hx(s.get("parentSpanId", "")), links, extra))
spans.sort()
t0 = spans[0][0]
ids = {s[5]: s for s in spans}
def depth(s):
    d = 0
    while s[6] in ids:
        s, d = ids[s[6]], d + 1
    return d
print(f"traceID {tid}")
for s in spans:
    name = "  " * depth(s) + s[3]
    root = "" if s[6] in ids else ("  (부모 없음)" if not s[6] else f"  (부모 {s[6]} 는 이 트레이스에 없음)")
    link = f"  link→{','.join(s[7])}" if s[7] else ""
    print(f"+{(s[0]-t0)/1e6:7.1f}ms {(s[1]-s[0])/1e6:6.1f}ms  {s[2]:<8} {s[4]:<8} {name:<34} {s[5]}{root}{link}  {s[8]}")
