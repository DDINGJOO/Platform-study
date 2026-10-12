#!/usr/bin/env python3
"""results/raw/ 의 원자료를 상대 시간(db 를 멈춘 순간 = 0초)으로 바꿔 results/<이름>.txt 로 요약한다.

    python3 scripts/summarize.py <이름>...      # 인자가 없으면 events.json 이 있는 시나리오 전부
"""
import glob, json, os, re, sys
from collections import Counter, defaultdict
from datetime import datetime

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(HERE, "results", "raw")
HUMAN = {"human", "page", "ticket"}          # 사람이 받는 수신자. log 는 기록만


def ts(s):
    s = re.sub(r"\.(\d{6})\d*", r".\1", s).replace("Z", "+00:00")   # 나노초는 마이크로초로 자른다
    return datetime.fromisoformat(s).timestamp()


def rel(t, ev):
    if ev["t1"] is not None and t >= ev["t1"]:
        return f"{t - ev['t0']:7.1f}s (복구 +{t - ev['t1']:.1f}s)"
    return f"{t - ev['t0']:7.1f}s"


def summarize(name):
    ev = json.load(open(os.path.join(RAW, f"{name}-events.json")))
    notes = [json.loads(l) for l in open(os.path.join(RAW, f"{name}.jsonl"))]
    polls = [json.loads(l) for l in open(os.path.join(RAW, f"{name}-poll.jsonl"))]
    out = []
    w = out.append
    w(f"시나리오 {name}  (alertmanager/{ev['config']})")
    w(f"db 멈춤 0초, 되살림 {ev['t1'] - ev['t0']:.1f}초, 이후 {ev['after_s']}초 관찰. 시각은 모두 db 를 멈춘 순간 기준")
    pts = [p["t"] for p in polls]
    end = ev["t1"] + ev["after_s"]
    gaps = [(round(a - ev["t0"]), round(b - a)) for a, b in zip(pts, pts[1:]) if b - a > 10]
    if end - pts[-1] > 10:
        gaps.append((round(pts[-1] - ev["t0"]), round(end - pts[-1])))
    if gaps:
        w(f"!! 2초 폴링이 10초 넘게 끊긴 구간(시작 초, 길이 초): {gaps}  호스트가 멈췄던 실행이라 믿을 수 없다")
    early = sorted({a["name"] for p in polls for a in p["prom"] if a.get("activeAt") and ts(a["activeAt"]) < ev["t0"]})
    if early:
        w(f"!! db 를 멈추기 전에 이미 pending/firing 이던 경고: {early}  정상 상태가 아니었던 실행이라 믿을 수 없다")
    pre = [r for r in notes if r["recv"] < ev["t0"]]
    if pre:
        w(f"!! db 를 멈추기 전에 받은 알림 {len(pre)}통. 앞 실행의 흔적이 섞인 실행이라 믿을 수 없다")
    if ev.get("stalls"):
        w(f"!! 폴링이 10초 넘게 멈춘 구간(시작 초, 길이 초): {ev['stalls']}  이 실행은 믿을 수 없다")
    w("")

    # Prometheus 쪽: 경고 이름별로 처음 firing 이 보인 시각, 최대 동시 firing
    first_fire, last_fire = {}, {}
    max_firing, max_t, max_supp, supp_t = 0, 0, 0, 0
    for p in polls:
        firing = [a for a in p["prom"] if a["state"] == "firing"]
        for a in firing:
            first_fire.setdefault(a["name"], p["t"])
            last_fire[a["name"]] = p["t"]
        if len(firing) > max_firing:
            max_firing, max_t = len(firing), p["t"]
        supp = sum(1 for a in p["am"] if a["state"] == "suppressed")
        if supp > max_supp:
            max_supp, supp_t = supp, p["t"]
    w("[Prometheus 가 본 경고] 2초 간격 폴링")
    for n in sorted(first_fire, key=first_fire.get):
        w(f"  {n:15} 처음 firing {rel(first_fire[n], ev)}   마지막 firing {rel(last_fire[n], ev)}")
    w(f"  동시에 firing 인 경고 최대 {max_firing}개 ({rel(max_t, ev).strip()})")
    w(f"  Alertmanager 에서 억제(suppressed)된 경고 최대 {max_supp}개" + (f" ({rel(supp_t, ev).strip()})" if max_supp else ""))
    w("")

    w("[받은 알림] 한 줄 = 웹훅 한 번 = 사람(또는 기록)에게 간 알림 한 통")
    w("  받은 시각                    수신자  상태      firing resolved  묶음 라벨")
    for r in notes:
        names = Counter(a["name"] for a in r["alerts"])
        gl = ",".join(f"{k}={v}" for k, v in sorted((r["groupLabels"] or {}).items())) or "(없음)"
        if gl.startswith("alertname=") and len(gl) > 40:
            gl = gl[:40] + "…"
        w(f"  {rel(r['recv'], ev):27} {r['receiver']:6} {r['status']:9} {r['firing']:6} {r['resolved']:8}  {gl}")
        w(f"  {'':27} {'':6} 담긴 경고: " + ", ".join(f"{k} {v}" for k, v in sorted(names.items())))
    w("")

    by_rcv = Counter(r["receiver"] for r in notes)
    human = [r for r in notes if r["receiver"] in HUMAN]
    during = [r for r in human if r["recv"] < ev["t1"]]
    after = [r for r in human if r["recv"] >= ev["t1"]]
    w("[합계]")
    w(f"  수신자별 알림 수: " + ", ".join(f"{k} {v}" for k, v in sorted(by_rcv.items())))
    w(f"  사람에게 간 알림: {len(human)}통 (장애 중 {len(during)}, 복구 뒤 {len(after)})")
    w(f"  그중 firing 상태 알림 {sum(1 for r in human if r['status']=='firing')}통, resolved 상태 알림 {sum(1 for r in human if r['status']=='resolved')}통")
    if human:
        w(f"  첫 알림: {rel(human[0]['recv'], ev).strip()}  ({', '.join(sorted(set(a['name'] for a in human[0]['alerts'])))})")
        db = next((r for r in human if any(a["name"] == "DBDown" for a in r["alerts"])), None)
        if db:
            w(f"  DBDown 이 처음 실린 알림: {rel(db['recv'], ev).strip()}")
    page = [r for r in notes if r["receiver"] == "page"]
    if page:
        w(f"  page 수신자(사람을 깨움): {len(page)}통, 첫 page {rel(page[0]['recv'], ev).strip()}")
    alerts = [a for r in notes for a in r["alerts"]]
    w(f"  알림에 실린 경고 {len(alerts)}건 중 runbook_url 주석이 있는 것 {sum(1 for a in alerts if a['runbook_url'])}건")
    ca = Counter(k for r in notes for k in r["commonAnnotations"])
    w(f"  commonAnnotations 에 runbook_url 이 들어 있던 알림 {ca.get('runbook_url', 0)}통 / {len(notes)}통")
    if any(r["truncatedAlerts"] for r in notes):
        w(f"  잘린 경고(truncatedAlerts) 있음: {sum(r['truncatedAlerts'] for r in notes)}")

    # 같은 묶음에 반복 알림이 간 간격(firing, 내용 변화 없음)
    reps = defaultdict(list)
    for r in notes:
        reps[(r["receiver"], r["groupKey"])].append(r)
    gaps = []
    for k, rs in reps.items():
        for a, b in zip(rs, rs[1:]):
            gaps.append(b["recv"] - a["recv"])
    if gaps:
        w(f"  같은 묶음에 연달아 간 알림 사이 간격(초): " + ", ".join(f"{g:.0f}" for g in sorted(gaps)))
    text = "\n".join(out) + "\n"
    open(os.path.join(HERE, "results", f"{name}.txt"), "w").write(text)
    print(text)


if __name__ == "__main__":
    names = sys.argv[1:] or sorted(os.path.basename(p)[:-12] for p in glob.glob(os.path.join(RAW, "*-events.json")))
    for n in names:
        summarize(n)
