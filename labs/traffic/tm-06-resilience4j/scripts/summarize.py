"""phases.sh 가 남긴 out/phases.log 의 시각으로 구간을 나눠, 구간마다 대상별 숫자를 Prometheus 에서 뽑는다.
사용: python3 scripts/summarize.py   (tm-06-resilience4j 디렉터리에서, PROM 기본 http://localhost:28090)
구간 앞뒤 20초는 전환 중이라 뺀다."""
import json, os, re, time, urllib.parse, urllib.request, datetime

PROM = os.environ.get("PROM", "http://localhost:28090")
NAMES = ["정상", "느려짐(1000ms)", "정상", "빨리 실패(100%)", "정상"]

def q(expr, t):
    u = f"{PROM}/api/v1/query?" + urllib.parse.urlencode({"query": expr, "time": t})
    return json.load(urllib.request.urlopen(u))["data"]["result"]

today = datetime.date.today()
marks = []
for line in open("out/phases.log"):
    m = re.match(r"(\d\d:\d\d:\d\d) delayMs", line)
    if m:
        hh, mm, ss = map(int, m.group(1).split(":"))
        marks.append(datetime.datetime(today.year, today.month, today.day, hh, mm, ss).timestamp())
ends = marks[1:] + [marks[0] + 660]
apps = ["order-rl", "order-bh", "order-cb", "order-cbbh"]
for name, s, e in zip(NAMES, marks, ends):
    s, e = s + 20, e - 20
    w = int(e - s)
    print(f"\n== {name}  {time.strftime('%H:%M:%S', time.localtime(s))}~{time.strftime('%H:%M:%S', time.localtime(e))} ({w}s)")
    print(f"{'':12}{'200':>7}{'429':>7}{'502':>7}{'503':>7}  {'스레드max':>8}  {'/pay p99(서버)':>12}")
    down = {}
    for r in q(f'sum by (caller) (label_replace(increase(http_server_requests_seconds_count{{app="downstream",uri="/recommend"}}[{w}s]), "caller", "x", "", ""))', e):
        down = float(r["value"][1]) / w
    for a in apps:
        st = {r["metric"]["status"]: float(r["value"][1]) / w for r in q(f'sum by (status) (increase(http_server_requests_seconds_count{{app="{a}",uri="/recommend"}}[{w}s]))', e)}
        th = q(f'max_over_time(tomcat_threads_busy_threads{{app="{a}",name="http-nio-8080"}}[{w}s])', e)
        p99 = q(f'histogram_quantile(0.99, sum by (le) (increase(http_server_requests_seconds_bucket{{app="{a}",uri="/pay"}}[{w}s])))', e)
        row = "".join(f"{st.get(c, 0):7.1f}" for c in ["200", "429", "502", "503"])
        print(f"{a:12}{row}  {float(th[0]['value'][1]) if th else float('nan'):8.0f}  {float(p99[0]['value'][1])*1000 if p99 else float('nan'):7.0f}ms")
    print(f"downstream 가 받은 /recommend 초당 {down:.1f} (네 대 합)")
