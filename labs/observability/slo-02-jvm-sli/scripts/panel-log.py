"""대시보드 패널의 대표값을 5초마다 Prometheus 에서 읽어 CSV 로 찍는다. 어느 패널이 먼저 움직였는지 비교용.
사용: python3 scripts/panel-log.py <서비스이름> > out.csv   (PROM_URL 기본 http://localhost:24190)"""
import json, os, sys, time, urllib.parse, urllib.request
from datetime import datetime, timezone

PROM = os.environ.get("PROM_URL", "http://localhost:24190")
APP = sys.argv[1]
A = f'application="{APP}"'
R = f'{A}, uri!~"/actuator.*"'
W = "[30s]"
PANELS = {
    "availability": f'1 - (sum(rate(http_server_requests_seconds_count{{{R}, status=~"5.."}}{W})) or vector(0)) / sum(rate(http_server_requests_seconds_count{{{R}}}{W}))',
    "server_p99": f'histogram_quantile(0.99, sum by (le) (rate(http_server_requests_seconds_bucket{{{R}}}{W})))',
    "k6_p99": f'histogram_quantile(0.99, sum(rate(k6_http_req_duration_seconds{{url=~"http://{APP}:8080/.*"}}{W})))',
    "rps": f'sum(rate(http_server_requests_seconds_count{{{R}}}{W}))',
    "active_req": f'sum(http_server_requests_active_seconds_gcount{{{R}}})',
    "gc_pause_frac": f'sum(rate(jvm_gc_pause_seconds_sum{{{A}}}{W}))',
    "gc_pause_max": f'max(jvm_gc_pause_seconds_max{{{A}}})',
    "gc_overhead": f'max(jvm_gc_overhead{{{A}}})',
    "gc_per_s": f'sum(rate(jvm_gc_pause_seconds_count{{{A}}}{W}))',
    "heap_used": f'sum(jvm_memory_used_bytes{{{A}, area="heap"}}) / sum(jvm_memory_max_bytes{{{A}, area="heap"}} > 0)',
    "heap_after_gc": f'max(jvm_memory_usage_after_gc{{{A}}})',
    "cpu": f'max(process_cpu_usage{{{A}}})',
    "threads_busy": f'max(tomcat_threads_busy_threads{{{A}}})',
    "fd": f'max(process_files_open_files{{{A}}} / process_files_max_files{{{A}}})',
}

def q(e):
    try:
        r = json.load(urllib.request.urlopen(f"{PROM}/api/v1/query?" + urllib.parse.urlencode({"query": e}), timeout=5))["data"]["result"]
        return float(r[0]["value"][1]) if r else float("nan")
    except Exception:
        return float("nan")

print("time," + ",".join(PANELS), flush=True)
while True:
    t0 = time.time()
    print(datetime.now(timezone.utc).strftime("%H:%M:%S") + "," + ",".join(f"{q(e):.4g}" for e in PANELS.values()), flush=True)
    time.sleep(max(0, 5 - (time.time() - t0)))
