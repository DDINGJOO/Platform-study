"""한 번의 실행(out/<RUN>/)을 시간표와 간격으로 정리한다. 시각은 전부 '시작 기준 초'로 바꿔 적는다.
사용: python3 scripts/analyze.py out/run1   (스택이 아직 떠 있어야 Prometheus 를 읽을 수 있다)"""
import bisect, csv, gzip, json, os, sys, urllib.parse, urllib.request

OUT = sys.argv[1]
P = f"http://localhost:{os.environ.get('PROM_PORT', '34090')}"
SLO = 0.300  # p99 기준 300ms

ev = []
for line in open(f"{OUT}/events.raw", encoding="utf-8"):
    ts, rest = line.rstrip("\n").split(" ", 1)
    ev.append((int(ts), rest))
start = next(t for t, e in ev if e == "start")
end = next((t for t, e in ev if e == "end"), max(t for t, _ in ev))
rel = lambda t: t - start
deploys = [(rel(t), e) for t, e in ev if e.startswith("deploy")]
gaps = [(rel(t), e) for t, e in ev if e.startswith("gap")]

def rng(expr, step=5):
    qs = urllib.parse.urlencode({"query": expr, "start": start, "end": end, "step": step})
    r = json.load(urllib.request.urlopen(f"{P}/api/v1/query_range?{qs}"))["data"]["result"]
    return {int(float(t)) - start: float(v) for t, v in r[0]["values"]} if r else {}

U = 'uri="/orders/recent"'
S = {
    "rows": rng('pg_stat_user_tables_n_live_tup{relname="orders"}'),
    "rows_read_per_s": rng('rate(pg_stat_user_tables_seq_tup_read{relname="orders"}[15s])'),
    "seq_scans_per_s": rng('rate(pg_stat_user_tables_seq_scan{relname="orders"}[15s])'),
    "p99_server_1m": rng(f'histogram_quantile(0.99, sum by (le) (rate(http_server_requests_seconds_bucket{{{U}}}[1m])))'),
    "err5xx_server_per_s": rng(f'sum(rate(http_server_requests_seconds_count{{{U}, status=~"5.."}}[15s]))'),
    "hikari_pending": rng('max(hikaricp_connections_pending)'),
    "hikari_timeouts_total": rng('sum(hikaricp_connections_timeout_total)'),
}

# k6 원자료: 요청 하나하나의 시각(초), 지연(ms), 상태 코드, 오류 코드
reqs = []
k6 = [f for f in os.listdir("out") if f.startswith(os.path.basename(OUT)) and f.endswith("k6.csv.gz")]
with gzip.open(f"out/{k6[0]}", "rt") as f:
    for row in csv.DictReader(f):
        if row["metric_name"] == "http_req_duration":
            reqs.append((int(row["timestamp"]) - start, float(row["metric_value"]), row["status"], row.get("error_code", "")))
reqs.sort()
times = [r[0] for r in reqs]

def window(a, b):
    return reqs[bisect.bisect_left(times, a):bisect.bisect_left(times, b)]

def p99(rs):
    d = sorted(r[1] for r in rs)
    return d[min(len(d) - 1, int(0.99 * len(d)))] / 1000 if d else float("nan")

cpu = {}
if os.path.exists(f"{OUT}/cpu.raw"):
    for line in open(f"{OUT}/cpu.raw"):
        ts, v = line.split()
        cpu[rel(int(ts))] = float(v.rstrip("%"))
cpu_t = sorted(cpu)

def cpu_at(t):
    i = bisect.bisect_right(cpu_t, t) - 1
    return cpu[cpu_t[i]] if i >= 0 else float("nan")

T = list(range(0, rel(end) + 1, 5))
rows = []
for t in T:
    w60, w10 = window(t - 60, t), window(t - 10, t)
    rows.append({
        "t": t,
        **{k: S[k].get(t, "") for k in S},
        "db_cpu_pct": cpu_at(t),
        "client_rps_10s": len(w10) / 10,
        "client_p99_60s": p99(w60),
        "client_500_10s": sum(1 for r in w10 if r[2] == "500"),
        "client_timeout_10s": sum(1 for r in w10 if r[3] == "1050"),
        "client_other_err_10s": sum(1 for r in w10 if r[2] not in ("200", "500") and r[3] != "1050"),
    })
def tidy(r):
    # 커밋 전 마스킹 검사가 8자리 이상 숫자를 ID 로 의심하므로, 행/초는 천 단위로 줄이고 소수는 4자리로 자른다
    o = {}
    for k, v in r.items():
        if k == "rows_read_per_s":
            k, v = "rows_read_k_per_s", ("" if v == "" else round(v / 1000, 1))
        elif isinstance(v, float):
            v = "" if v != v else round(v, 4)
        o[k] = v
    return o
with open(f"{OUT}/timeline.csv", "w", newline="") as f:
    tl = [tidy(r) for r in rows]
    w = csv.DictWriter(f, fieldnames=list(tl[0]))
    w.writeheader(); w.writerows(tl)

t_change = deploys[0][0]
def first(cond, after):
    return next((r["t"] for r in rows if r["t"] > after and cond(r)), None)

base_read = max([r["rows_read_per_s"] or 0 for r in rows if r["t"] < t_change] + [1])
t_db = first(lambda r: (r["rows_read_per_s"] or 0) > 10 * base_read and (r["rows_read_per_s"] or 0) > 1000, t_change)
t_slo_c = first(lambda r: r["client_p99_60s"] == r["client_p99_60s"] and r["client_p99_60s"] > SLO and r["t"] - 60 >= t_change, t_change)
t_slo_s = first(lambda r: r["p99_server_1m"] != "" and r["p99_server_1m"] > SLO, t_change)
t_500 = next((r[0] for r in reqs if r[0] > t_change and r[2] == "500"), None)
t_k6to = next((r[0] for r in reqs if r[0] > t_change and r[3] == "1050"), None)
t_hik = first(lambda r: (r["hikari_timeouts_total"] or 0) > 0, t_change)

def last_deploy_before(t):
    c = [d for d in deploys if d[0] <= t]
    return c[-1] if c else None

fmt = lambda s: "없음" if s is None else f"{s}초 ({s/60:.1f}분)"
lines = [
    f"실행: {OUT}",
    f"끝: {fmt(rel(end))}",
    f"시계 공백(>30초): {gaps if gaps else '없음'}",
    "",
    "배포 (시작 기준)",
    *[f"  {fmt(t):>18}  {e}" for t, e in deploys],
    "",
    f"쿼리 변경 배포                   {fmt(t_change)}",
    f"DB 순차 스캔 행 수 급증          {fmt(t_db)}   (변경 전 최대 {base_read:.0f} 행/초의 10배 초과)",
    f"p99 300ms 초과 (k6, 60초 창)     {fmt(t_slo_c)}",
    f"p99 300ms 초과 (서버, 1분 rate)  {fmt(t_slo_s)}",
    f"첫 500 응답 (k6)                 {fmt(t_500)}",
    f"첫 Hikari 커넥션 타임아웃         {fmt(t_hik)}",
    f"첫 k6 요청 타임아웃(3초)          {fmt(t_k6to)}",
    "",
    "간격",
    f"  변경 → DB 지표   {fmt(None if t_db is None else t_db - t_change)}",
    f"  변경 → SLO 위반  {fmt(None if t_slo_c is None else t_slo_c - t_change)}",
    f"  변경 → 첫 500    {fmt(None if t_500 is None else t_500 - t_change)}",
    "",
    f"SLO 위반 직전 배포        {last_deploy_before(t_slo_c) if t_slo_c else '-'}",
    f"DB 지표 급증 직전 배포    {last_deploy_before(t_db) if t_db else '-'}",
]
# annotation 을 짚어 원인 배포까지 가는 단계 수 (1편이 예고한 측정)
#  증상 패널: SLO 위반 시각에서 거꾸로, 그 앞의 배포 annotation 을 최근 것부터 하나씩 짚는다
#  원인 쪽 패널: DB 순차 스캔 행이 급증한 시각에서 거꾸로 짚는다
cause = deploys[0]
def steps_back(t):
    if t is None:
        return None
    before = [d for d in deploys if d[0] <= t][::-1]
    return before.index(cause) + 1 if cause in before else None
lines += [
    "",
    "원인 배포(쿼리 변경)까지 annotation 을 최근 것부터 짚은 단계 수",
    f"  증상 패널(SLO 위반 시각부터)      {steps_back(t_slo_c)}",
    f"  원인 쪽 패널(DB 지표 급증 시각부터) {steps_back(t_db)}",
]
# 되돌리기 뒤 구간별 상태
rb = [d for d in deploys if "되돌리기" in d[1]]
for i, (t0, e) in enumerate(rb):
    t1 = rb[i + 1][0] if i + 1 < len(rb) else rel(end)
    seg = window(t0 + 15, t1)
    ok = [r for r in seg if r[2] == "200"]
    lines.append(f"\n[{e}] 뒤 {t0+15}~{t1}초: 요청 {len(seg)}건, 200 {len(ok)}건, 500 {sum(1 for r in seg if r[2]=='500')}건, "
                 f"타임아웃 {sum(1 for r in seg if r[3]=='1050')}건, p99 {p99(seg):.3f}초")
    rec = first(lambda r: r["client_p99_60s"] == r["client_p99_60s"] and r["client_p99_60s"] < SLO and r["t"] - 60 >= t0, t0)
    lines.append(f"  60초 창 p99 가 300ms 아래로 돌아온 시각: {fmt(rec)}" + ("" if rec is None or rec > t1 else f" (되돌린 뒤 {rec - t0}초)"))
open(f"{OUT}/summary.txt", "w", encoding="utf-8").write("\n".join(lines) + "\n")
print("\n".join(lines))
