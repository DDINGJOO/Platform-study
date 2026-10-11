"""phases.sh 가 남긴 out/phases.log 의 시각으로 구간을 나눠, 구간마다 앱별 숫자를 Prometheus 에서 뽑는다.
사용: python3 scripts/summarize.py   (tm-07-adaptive 디렉터리에서, PROM 기본 http://localhost:28290)
구간 앞 30초는 전환 중이라 뺀다. 지표를 못 긁은 구간은 빈칸(-)으로 나온다."""
import json, os, re, time, urllib.parse, urllib.request, datetime

PROM = os.environ.get("PROM", "http://localhost:28290")
NAMES = ["하위 50ms", "하위 500ms (과부하)", "하위 50ms (회복)"]
APPS = os.environ.get("APPS", "fixed,gradient2-windowed,vegas").split(",")

def q(expr, t):
    u = f"{PROM}/api/v1/query?" + urllib.parse.urlencode({"query": expr, "time": t})
    r = json.load(urllib.request.urlopen(u))["data"]["result"]
    return float(r[0]["value"][1]) if r else None

def f(v, fmt):
    return "-".rjust(len(fmt % 0)) if v is None or v != v else fmt % v

today = datetime.date.today()
marks = []
for line in open("out/phases.log"):
    m = re.match(r"(\d\d:\d\d:\d\d) delay", line)
    if m:
        hh, mm, ss = map(int, m.group(1).split(":"))
        marks.append(datetime.datetime(today.year, today.month, today.day, hh, mm, ss).timestamp())
ends = marks[1:] + [marks[0] + 780]
for name, s, e in zip(NAMES, marks, ends):
    s += 30
    w = int(e - s)
    print(f"\n== {name}  {time.strftime('%H:%M:%S', time.localtime(s))}~{time.strftime('%H:%M:%S', time.localtime(e))} ({w}s)")
    print(f"{'':20}{'200/s':>7}{'429/s':>7}{'p50':>8}{'p99':>8}{'limit 평균(최소~최대)':>22}{'in-flight':>10}{'자원 대기':>9}")
    for a in APPS:
        ok = q(f'sum(increase(http_server_requests_seconds_count{{app="{a}",uri="/work",status="200"}}[{w}s]))', e)
        rj = q(f'sum(increase(http_server_requests_seconds_count{{app="{a}",status="429"}}[{w}s]))', e)
        p50 = q(f'histogram_quantile(0.5, sum by (le) (increase(http_server_requests_seconds_bucket{{app="{a}",uri="/work",status="200"}}[{w}s])))', e)
        p99 = q(f'histogram_quantile(0.99, sum by (le) (increase(http_server_requests_seconds_bucket{{app="{a}",uri="/work",status="200"}}[{w}s])))', e)
        la = q(f'avg_over_time(concurrency_limits_limit{{app="{a}"}}[{w}s])', e)
        ln = q(f'min_over_time(concurrency_limits_limit{{app="{a}"}}[{w}s])', e)
        lx = q(f'max_over_time(concurrency_limits_limit{{app="{a}"}}[{w}s])', e)
        inf = q(f'avg_over_time(lab_limiter_inflight{{app="{a}"}}[{w}s])', e)
        wt = q(f'avg_over_time(lab_pool_waiting{{app="{a}"}}[{w}s])', e)
        up = q(f'avg_over_time(up{{instance="app-{a}:9090"}}[{w}s])', e)
        lim = "-" if la is None else f"{la:.0f} ({ln:.0f}~{lx:.0f})"
        print(f"{a:20}{f(ok and ok/w,'%7.1f')}{f(rj and rj/w if rj is not None else None,'%7.1f')}"
              f"{f(p50 and p50*1000,'%6.0fms')}{f(p99 and p99*1000,'%6.0fms')}{lim:>22}{f(inf,'%10.1f')}{f(wt,'%9.1f')}"
              + ("" if up is None or up > 0.99 else f"   (스크레이프 성공 {up*100:.0f}%)"))
