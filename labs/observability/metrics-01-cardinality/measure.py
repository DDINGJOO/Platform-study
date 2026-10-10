"""Prometheus 와 앱에서 시계열 수·스크레이프 크기·메모리를 한 줄로 찍는다.
사용: python3 measure.py [라벨]      (PROM_URL, APP_URL 로 주소를 바꾼다)"""
import json, os, sys, urllib.parse, urllib.request

PROM = os.environ.get("PROM_URL", "http://localhost:21090")
APP = os.environ.get("APP_URL", "http://localhost:21080")

def q(expr):
    url = f"{PROM}/api/v1/query?query={urllib.parse.quote(expr)}"
    r = json.load(urllib.request.urlopen(url))["data"]["result"]
    return float(r[0]["value"][1]) if r else float("nan")

body = urllib.request.urlopen(f"{APP}/actuator/prometheus").read()
lines = [l for l in body.decode().splitlines() if l and not l.startswith("#")]
row = {
    "head_series": q("prometheus_tsdb_head_series"),
    "app_series_now": q('count({job="app"})'),
    "scraped_samples": q('scrape_samples_scraped{job="app"}'),
    "scrape_body_KB": q('scrape_body_size_bytes{job="app"}') / 1024,
    "scrape_ms": q('scrape_duration_seconds{job="app"}') * 1000,
    "prom_heap_MB": q('go_memstats_heap_inuse_bytes{job="prometheus"}') / 2**20,
    "prom_rss_MB": q('process_resident_memory_bytes{job="prometheus"}') / 2**20,
    "app_heap_MB": q('sum(jvm_memory_used_bytes{job="app",area="heap"})') / 2**20,
    "endpoint_lines": len(lines),
    "endpoint_KB": len(body) / 1024,
}
label = sys.argv[1] if len(sys.argv) > 1 else "-"
print(label.ljust(22), "  ".join(f"{k}={v:,.1f}" if isinstance(v, float) else f"{k}={v:,}" for k, v in row.items()))
