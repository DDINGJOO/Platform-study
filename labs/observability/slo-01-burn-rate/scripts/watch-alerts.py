"""Prometheus 경고 상태와 burn rate 를 1초마다 읽어, 바뀔 때만 시각과 함께 찍는다.
사용: python3 scripts/watch-alerts.py   (PROM_URL 로 주소 변경, 기본 http://localhost:24090)"""
import json, os, time, urllib.parse, urllib.request
from datetime import datetime

PROM = os.environ.get("PROM_URL", "http://localhost:24090")
WINDOWS = ["10s", "2m", "1m", "12m", "4m", "48m", "12m", "2h24m"]

def q(expr):
    url = f"{PROM}/api/v1/query?" + urllib.parse.urlencode({"query": expr})
    return json.load(urllib.request.urlopen(url, timeout=5))["data"]["result"]

def burn(w):
    r = q(f'slo:sli_error:ratio_rate{w} / on() group_left() slo:error_budget:ratio')
    return float(r[0]["value"][1]) if r else float("nan")

last = None
while True:
    try:
        alerts = json.load(urllib.request.urlopen(f"{PROM}/api/v1/alerts", timeout=5))["data"]["alerts"]
        state = sorted(f"{a['labels'].get('severity')}={a['state']}" for a in alerts)
        if state != last:
            ws = "  ".join(f"{w}:{burn(w):.1f}" for w in dict.fromkeys(WINDOWS))
            act = " ".join(f"{a['labels'].get('severity')}.activeAt={a['activeAt'][11:19]}" for a in alerts)
            print(f"{datetime.utcnow():%H:%M:%S} UTC  {state or ['(none)']}  burn {ws}  {act}", flush=True)
            last = state
    except Exception as e:  # 스택이 아직 안 떴을 때
        print("err", e, flush=True)
    time.sleep(1)
