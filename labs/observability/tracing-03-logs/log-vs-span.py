"""결제 에러 로그 한 줄마다, Loki 에 찍힌 시각이 그 로그를 남긴 결제 SERVER 스팬 구간 안에 드는지 센다.
Grafana 의 trace -> logs 는 기본으로 스팬 시작~끝 구간만 Loki 에 묻기 때문이다.
사용: python3 log-vs-span.py [초]   (최근 N초, 기본 900)"""
import base64, json, os, re, sys, time, urllib.parse, urllib.request
from datetime import datetime

LOKI = os.environ.get("LOKI_URL", "http://localhost:25004")
TEMPO = os.environ.get("TEMPO_URL", "http://localhost:25001")
S = int(sys.argv[1]) if len(sys.argv) > 1 else 900

def get(url):
    with urllib.request.urlopen(url) as r:
        return json.load(r)

now = time.time()
q = urllib.parse.urlencode({"query": '{service_name="payment"} |= "PG 승인 거절"', "limit": 5000,
                            "start": int((now - S) * 1e9), "end": int(now * 1e9)})
lines = [(int(ts), line) for s in get(f"{LOKI}/loki/api/v1/query_range?{q}")["data"]["result"] for ts, line in s["values"]]
inside = after = before = ms_cut = 0
lag = []   # Loki 시각 - 앱이 찍은 시각 (ms)
gap = []   # Loki 시각 - 스팬 끝 (ms)
for ts, line in lines:
    tid = re.search(r"trace_id=(\w+)", line).group(1)
    sid = re.search(r"span_id=(\w+)", line).group(1)
    app = datetime.fromisoformat(line.split()[0].replace("Z", "+00:00")).timestamp() * 1e9
    lag.append((ts - app) / 1e6)
    for b in get(f"{TEMPO}/api/traces/{tid}")["batches"]:
        for ss in b["scopeSpans"]:
            for sp in ss["spans"]:
                if base64.b64decode(sp["spanId"]).hex() == sid:
                    st, en = int(sp["startTimeUnixNano"]), int(sp["endTimeUnixNano"])
                    gap.append((ts - en) / 1e6)
                    if ts < st: before += 1
                    elif ts > en: after += 1
                    else: inside += 1
                    if ts > en // 1_000_000 * 1_000_000: ms_cut += 1   # 끝을 ms 로 자르면 밖
lag.sort(); gap.sort()
n = len(lines)
print(f"결제 에러 로그 {n}줄")
print(f"  스팬 구간 안 {inside} / 스팬이 끝난 뒤 {after} / 시작 전 {before}")
print(f"  스팬 끝을 밀리초로 내림하면 구간 밖이 되는 줄 {ms_cut}")
print(f"  Loki 시각 - 앱 로그 시각: 중앙값 {lag[n//2]:.2f}ms, 최대 {lag[-1]:.2f}ms")
print(f"  Loki 시각 - 스팬 끝:      중앙값 {gap[n//2]:+.2f}ms, 최소 {gap[0]:+.2f}ms, 최대 {gap[-1]:+.2f}ms")
