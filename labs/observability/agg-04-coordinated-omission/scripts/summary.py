"""k6 CSV 세 개와 Prometheus 에서 이번 실행의 숫자를 한 표로 뽑는다.
사용(실습 디렉터리에서): python3 scripts/summary.py
k6 쪽 백분위는 CSV 의 모든 요청을 정렬해서 구한 정확한 값(nearest-rank)이다.
서버 쪽은 앱이 기동한 뒤 쌓인 http_server_requests 버킷 전체로 계산한 histogram_quantile 이다.
그래서 앱을 다시 띄운 직후 한 번만 돌린 실행이어야 두 숫자가 같은 구간을 본다.
서버 max 는 Micrometer 의 시간 창 max(http_server_requests_seconds_max)를 10분 동안 가장 큰 값으로 본 것이다."""
import csv, json, math, os, urllib.parse, urllib.request

PROM = os.environ.get("PROM_URL", "http://localhost:21090")
RUNS = [("closed", "app-closed"), ("open", "app-open"), ("starved", "app-starved")]


def pct(sorted_vals, p):
    if not sorted_vals:
        return float("nan")
    k = max(0, math.ceil(p / 100 * len(sorted_vals)) - 1)
    return sorted_vals[k]


def prom(q):
    u = f"{PROM}/api/v1/query?" + urllib.parse.urlencode({"query": q})
    r = json.load(urllib.request.urlopen(u))["data"]["result"]
    return float(r[0]["value"][1]) if r else float("nan")


def fmt(ms):
    return f"{ms:,.0f}ms" if ms >= 100 else f"{ms:.2f}ms"


print(f"{'':16}{'건수':>8}{'p50':>10}{'p90':>10}{'p99':>10}{'p99.9':>10}{'max':>10}{'100ms 초과':>12}{'버린 반복':>10}")
for run, app in RUNS:
    vals, dropped = [], 0
    with open(f"out/{run}.csv") as f:
        for row in csv.DictReader(f):
            if row["metric_name"] == "http_req_duration":
                vals.append(float(row["metric_value"]))
            elif row["metric_name"] == "dropped_iterations":
                dropped += int(float(row["metric_value"]))
    vals.sort()
    slow = sum(1 for v in vals if v > 100)
    print(f"k6 {run:<13}{len(vals):>8,}" + "".join(f"{fmt(pct(vals, p)):>10}" for p in (50, 90, 99, 99.9))
          + f"{fmt(vals[-1]):>10}{slow:>12,}{dropped:>10,}")
    sel = f'job="app",instance="{app}:8080",uri="/work"'
    n = prom(f"sum(http_server_requests_seconds_count{{{sel}}})")
    qs = [prom(f"histogram_quantile({p}, sum by (le) (http_server_requests_seconds_bucket{{{sel}}}))") * 1000
          for p in (0.5, 0.9, 0.99, 0.999)]
    mx = prom(f"max_over_time(http_server_requests_seconds_max{{{sel}}}[10m])") * 1000
    print(f"서버 {app:<12}{n:>8,.0f}" + "".join(f"{fmt(q):>10}" for q in qs) + f"{fmt(mx):>10}{'-':>12}{'':>10}")

# 0.1118초 버킷 경계를 넘은 서버 요청 수(멈춘 순간 처리 중이던 요청). 글 5절의 표.
print("\n서버 버킷: 0.1118초 경계 이하 / 전체 / 차이")
for run, app in RUNS:
    sel = f'job="app",instance="{app}:8080",uri="/work"'
    le = prom(f'sum(http_server_requests_seconds_bucket{{{sel},le=~"0[.]11.*"}})')  # 0.1118초 경계 하나
    inf = prom(f'sum(http_server_requests_seconds_bucket{{{sel},le="+Inf"}})')
    print(f"  {app:<12}{le:>8,.0f}{inf:>8,.0f}{inf - le:>6,.0f}")

