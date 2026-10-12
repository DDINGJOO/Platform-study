#!/usr/bin/env python3
"""게임데이 한 번의 타임라인을 자동으로 만든다.

세 곳에서 사건을 모은다.
  1) raw/events.jsonl        gd.py 가 남긴 명령 기록(주입, 진단, 완화, 복구, 사람의 판단)
  2) raw/notifications.jsonl 웹훅 수신기가 받은 Alertmanager 알림(받은 시각)
  3) Prometheus             ALERTS 시계열(pending/firing 전환), 실패율 기록 규칙, 503 카운터
모든 시각은 주입(inject) 시각을 0으로 한 상대 시간으로 바꿔 results/<run>/ 에 쓴다(유닉스 시각은 남기지 않는다).

  timeline.py <run>        gd.py event start <run> 부터 다음 start 이벤트(또는 지금)까지
"""
import json, math, os, sys, time, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(HERE, "raw")
PROM = os.environ.get("PROM_URL", "http://localhost:28090")
THRESH = 0.05


def jl(name):
    p = os.path.join(RAW, name)
    return [json.loads(l) for l in open(p)] if os.path.exists(p) else []


def qr(expr, start, end, step=1):
    u = f"{PROM}/api/v1/query_range?" + urllib.parse.urlencode(
        {"query": expr, "start": start, "end": end, "step": step})
    return json.loads(urllib.request.urlopen(u, timeout=30).read())["data"]["result"]


def rel(t, t0):
    s = t - t0
    sign = "-" if s < 0 else "+"
    s = abs(s)
    return f"T{sign}{int(s // 60):02d}:{s % 60:04.1f}"


def iso(s):  # Alertmanager 의 RFC3339 시각 → epoch
    import calendar, re
    m = re.match(r"(\d+)-(\d+)-(\d+)T(\d+):(\d+):(\d+)(\.\d+)?Z", s)
    y, mo, d, h, mi, se = (int(x) for x in m.groups()[:6])
    return calendar.timegm((y, mo, d, h, mi, se)) + float(m.group(7) or 0)


def main():
    run = sys.argv[1]
    ev = jl("events.jsonl")
    starts = [i for i, e in enumerate(ev) if e["kind"] == "start"]
    i0 = next(i for i in starts if ev[i]["note"] == run)
    nxt = [i for i in starts if i > i0]
    t_start = ev[i0]["t"]
    t_end = ev[nxt[0]]["t"] if nxt else time.time()
    events = [e for e in ev[i0:(nxt[0] if nxt else None)]]
    t0 = next(e["t"] for e in events if e["kind"] == "inject")

    rows = []  # (t, source, what)
    for e in events:
        rows.append((e["t"], "명령 기록", f"[{e['kind']}] {e['note'].strip()}"))
    for n in jl("notifications.jsonl"):
        if t_start <= n["received"] <= t_end:
            for a in n["alerts"]:
                extra = f"startsAt={rel(iso(a['startsAt']), t0)}"
                if a["status"] == "resolved":
                    extra += f", endsAt={rel(iso(a['endsAt']), t0)}"
                rows.append((n["received"], "웹훅 수신", f"{a['alertname']} {a['status']} ({a['severity']}) {extra}"))

    # Prometheus: ALERTS 전환
    trans = {}
    for s in qr('ALERTS{alertname=~"Order.*"}', t_start, t_end):
        name, st = s["metric"]["alertname"], s["metric"]["alertstate"]
        ts = [float(v[0]) for v in s["values"]]
        # 연속 구간(평가 간격보다 큰 빈틈이 없는 구간)으로 나눈다
        segs, a = [], ts[0]
        for x, y in zip(ts, ts[1:]):
            if y - x > 1.5:
                segs.append((a, x)); a = y
        segs.append((a, ts[-1]))
        for a, b in segs:
            rows.append((a, "Prometheus", f"{name} {st} 시작"))
            rows.append((b, "Prometheus", f"{name} {st} 마지막 관측"))
        trans.setdefault((name, st), []).extend(segs)

    # 실패율 기준선 통과
    er = qr("order:error_ratio:rate1m", t_start, t_end)
    cross_up = cross_down = None
    peak = 0.0
    if er:
        prev = 0.0
        for t, v in er[0]["values"]:
            t, v = float(t), float(v)
            if math.isnan(v):
                continue
            peak = max(peak, v)
            if cross_up is None and prev <= THRESH < v and t >= t0:
                cross_up = t; rows.append((t, "Prometheus", f"실패율 기록 규칙이 {THRESH:.0%} 를 넘음"))
            if cross_up and cross_down is None and prev > THRESH >= v:
                cross_down = t; rows.append((t, "Prometheus", f"실패율 기록 규칙이 {THRESH:.0%} 아래로"))
            prev = v

    # 503 카운터: 영향 시작과 끝, 실패 건수
    def series(expr):
        r = qr(expr, t_start, t_end)
        return [(float(t), float(v)) for t, v in r[0]["values"]] if r else []
    fail = series('sum(http_server_requests_total{service="order",code="503"}) or vector(0)')
    total = series('sum(http_server_requests_total{service="order"})')
    deferred = series('sum(order_deferred_total) or vector(0)')
    first_fail = last_fail = None
    base = fail[0][1] if fail else 0
    lastv = base
    for t, v in fail:
        if v > lastv:
            if first_fail is None:
                first_fail = t
            last_fail = t
        lastv = v
    n_fail = (fail[-1][1] - base) if fail else 0
    if first_fail:
        rows.append((first_fail, "Prometheus", "503 카운터가 처음 늘어난 스크레이프(영향 시작)"))
        rows.append((last_fail, "Prometheus", "503 카운터가 마지막으로 늘어난 스크레이프(영향 끝)"))

    def in_window(ser, a, b):
        if not ser or a is None:
            return None
        before = [v for t, v in ser if t < a]
        upto = [v for t, v in ser if t <= b]
        return int(upto[-1] - (before[-1] if before else ser[0][1]))

    rows.sort(key=lambda r: r[0])
    out = os.path.join(HERE, "results", run)
    os.makedirs(out, exist_ok=True)

    def first(kind):
        return next((e["t"] for e in events if e["kind"] == kind), None)

    def first_notif(name, status):
        return next((r[0] for r in rows if r[1] == "웹훅 수신" and r[2].startswith(f"{name} {status}")), None)

    # 실행이 믿을 만한지: 스크레이프 누락(호스트나 Docker VM 이 멈추면 생긴다)과 부하 최저치
    win = int(t_end - t_start)
    u = f"{PROM}/api/v1/query?" + urllib.parse.urlencode({"query": f'count_over_time(up{{job="order"}}[{win}s])', "time": t_end})
    got = json.loads(urllib.request.urlopen(u, timeout=30).read())["data"]["result"]
    scrapes = int(float(got[0]["value"][1])) if got else 0
    rate = series('sum(rate(http_server_requests_total{service="order"}[30s]))')
    min_rate = round(min(v for t, v in rate if t >= t_start + 30), 1) if rate else None
    t_page = first_notif("OrderErrorRatioHigh", "firing")
    det_check = None
    if t_page:
        dwin = int(t_page - t_start)
        u = f"{PROM}/api/v1/query?" + urllib.parse.urlencode({"query": f'count_over_time(up{{job="order"}}[{dwin}s])', "time": t_page})
        got = json.loads(urllib.request.urlopen(u, timeout=30).read())["data"]["result"]
        det_check = f"{int(float(got[0]['value'][1])) if got else 0} / {dwin // 5}"
    t_mit = first(  "mitigate")
    t_restore = next((e["t"] for e in events if e["kind"] == "restore"), None)
    pend = trans.get(("OrderErrorRatioHigh", "pending"), [(None, None)])[0][0]
    fire = trans.get(("OrderErrorRatioHigh", "firing"), [(None, None)])[0][0]
    d = lambda a, b: None if a is None or b is None else round(b - a, 1)
    summary = {
        "run": run,
        "주입→영향 시작(첫 503 스크레이프)": d(t0, first_fail),
        "주입→실패율 기준 초과": d(t0, cross_up),
        "주입→pending": d(t0, pend),
        "주입→firing": d(t0, fire),
        "주입→page 알림 수신 (TTD)": d(t0, t_page),
        "page 알림→완화 명령": d(t_page, t_mit),
        "주입→완화 명령": d(t0, t_mit),
        "주입→영향 끝(마지막 503 스크레이프) (TTM)": d(t0, last_fail),
        "주입→정상 경로 복귀 명령 (TTR)": d(t0, t_restore),
        "실패한 주문(503) 건수": int(n_fail),
        "영향 구간(첫~마지막 503 스크레이프) 전체 주문 건수": in_window(total, first_fail, last_fail),
        "재고 확인 보류로 받은 주문 건수": int(deferred[-1][1] - deferred[0][1]) if deferred else None,
        "실패율 최고값(1m 창)": round(peak, 3),
        "점검: 스크레이프 수 / 기대값(5초 간격)": f"{scrapes} / {win // 5}",
        "점검: 주문 요청률 최저(30s 창, 건/초)": min_rate,
        "점검: 탐지 구간(start→page 수신) 스크레이프 수 / 기대값": det_check,
    }
    with open(os.path.join(out, "timeline.md"), "w") as f:
        f.write(f"# 타임라인: {run}\n\n시각은 장애 주입을 T+00:00 으로 둔 상대 시간. 자동 생성(scripts/timeline.py).\n\n")
        f.write("| 시각 | 출처 | 사건 |\n|---|---|---|\n")
        for t, src, what in rows:
            f.write(f"| {rel(t, t0)} | {src} | {what.replace('|', '/')} |\n")
        f.write("\n## 측정값 (초)\n\n")
        for k, v in summary.items():
            f.write(f"- {k}: {v}\n")
    json.dump({"summary": summary, "rows": [{"t": round(t - t0, 1), "source": s, "what": w} for t, s, w in rows]},
              open(os.path.join(out, "timeline.json"), "w"), ensure_ascii=False, indent=1)
    # 받은 알림 본문(상대 시각)도 남긴다: runbook_url 이 실려 왔는지 확인용
    with open(os.path.join(out, "notifications.json"), "w") as f:
        keep = []
        for n in jl("notifications.jsonl"):
            if t_start <= n["received"] <= t_end:
                keep.append({"received": rel(n["received"], t0), "status": n["status"],
                             "alerts": [{**a, "startsAt": rel(iso(a["startsAt"]), t0),
                                         "endsAt": rel(iso(a["endsAt"]), t0) if a["status"] == "resolved" else None}
                                        for a in n["alerts"]]})
        json.dump(keep, f, ensure_ascii=False, indent=1)
    print(open(os.path.join(out, "timeline.md")).read())


if __name__ == "__main__":
    main()
