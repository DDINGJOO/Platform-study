"""한 실행(out/<mode>)을 요약한다. 시각은 장애 시작(F0) 기준 상대 초로 바꿔 results/<mode>/ 에 쓴다.
사용: python3 scripts/analyze.py out/unbounded"""
import json, os, sys
R = sys.argv[1]; mode = os.path.basename(R.rstrip("/"))
meta = dict(l.strip().split("=", 1) for l in open(f"{R}/meta.txt") if "=" in l)
F0, F1 = float(meta["fault_start"]), float(meta["fault_end"])
rel = lambda t: t - F0

load = []
for l in open(f"{R}/load.csv"):
    t, res = l.strip().split(",", 1); load.append((float(t), res))
load.sort()
inwin = [x for x in load if F0 <= x[0] <= F1]
errs = [t for t, r in inwin if r != "200"]

# 실패 덩어리: 10초 넘게 끊기면 다른 덩어리
bursts = []
for t in errs:
    if bursts and t - bursts[-1][1] <= 10: bursts[-1][1] = t; bursts[-1][2] += 1
    else: bursts.append([t, t, 1])

# ALERTS (1초 간격)
firing, pending = set(), set()
for s in json.load(open(f"{R}/alerts.json"))["data"]["result"]:
    tgt = firing if s["metric"]["alertstate"] == "firing" else pending
    for ts, v in s["values"]: tgt.add(round(float(ts)))
HF = float(meta["human_fix"]) if "human_fix" in meta else None   # 사람이 원인을 지운 시각
FE = HF if HF else F1                                              # 원인이 남아 있던 끝
secs = range(int(F0) + 1, int(FE))
fire_s = sum(1 for s in secs if s in firing)
off_s = len(secs) - fire_s
def intervals(S):
    out = []
    for s in sorted(S):
        if out and s - out[-1][1] <= 2: out[-1][1] = s
        else: out.append([s, s])
    return out
fire_iv = [iv for iv in intervals(firing) if iv[1] >= F0]
hidden = sum(1 for t in errs if round(t) not in firing)

ev = [json.loads(l) for l in open(f"{R}/events.jsonl")]
ev = [e for e in ev if e["t"] >= F0 - 5]
acts = [e for e in ev if e["type"] == "action"]
esc = [e for e in ev if e["type"] == "escalate"]
nots = [e for e in ev if e["type"] == "notification"]

out = []
p = out.append
p(f"# {mode} 실행 요약 (시각은 장애 시작 기준 초)\n")
p(f"- 장애 지속: {F1-F0:.0f}초, 그 동안 요청 {len(inwin)}건, 실패 {len(errs)}건 ({len(errs)/max(1,len(inwin)):.1%})")
p(f"- 자동 재시작 {len(acts)}번" + (f", 사람 호출(escalate) T+{rel(esc[0]['t']):.1f}" if esc else ", 사람 호출 없음"))
p(f"- 경고 firing {fire_s}초 / 꺼져 있던 시간 {off_s}초 (장애가 계속되는 동안)")
p(f"- 경고가 꺼져 있는 동안 난 실패 {hidden}건 (전체 실패의 {hidden/max(1,len(errs)):.1%})")
p(f"- 실패 덩어리 {len(bursts)}개")
if HF: p(f"- 사람이 원인을 지운 시각 T+{rel(HF):.1f}. 위 firing/꺼짐 초는 장애 시작부터 이 시각까지")
gaps = [round(acts[i]["t"] - acts[i-1]["t"], 1) for i in range(1, len(acts))]
p(f"- 재시작 시각(T+): {[round(rel(a['t']),1) for a in acts]}")
p(f"- 재시작 간격(초): {gaps}")
cnt = {}
for e in ev: cnt[e["type"]] = cnt.get(e["type"], 0) + 1
nf = sum(1 for e in nots if e["status"] == "firing"); nr = len(nots) - nf
p(f"- 알림 수신 {len(nots)}건(firing {nf}, resolved {nr}), 기록 종류별 {cnt}")
if esc:
    E = esc[0]["t"]; end2 = HF if HF else F1
    a = sum(1 for t in errs if t < E); b = sum(1 for t in errs if E <= t < end2); c = sum(1 for t in errs if t >= end2)
    p(f"- 실패 나눔: escalate 전 {a}, escalate~원인 제거 {b}, 원인 제거 뒤 {c}")
p("\n## 첫 번째 순환\n")
if errs:
    first_err = errs[0]
    fp = min((s for s in pending if s >= F0 - 1), default=None)
    ff = min((s for s in firing if s >= F0 - 1), default=None)
    n1 = next((e for e in nots if e["status"] == "firing"), None)
    a1 = acts[0] if acts else None
    p(f"| 사건 | T+초 |\n|---|---|")
    p(f"| 첫 실패 응답 | {rel(first_err):.1f} |")
    if fp: p(f"| 경고 pending (1초 해상도) | {rel(fp):.0f} |")
    if ff: p(f"| 경고 firing (1초 해상도) | {rel(ff):.0f} |")
    if n1: p(f"| firing 알림 수신 | {rel(n1['t']):.1f} |")
    if a1: p(f"| 재시작 요청 | {rel(a1['t']):.1f} |")
    p(f"| 첫 실패 덩어리의 마지막 실패 | {rel(bursts[0][1]):.1f} |")
p("\n## 실패 덩어리\n\n| # | 시작 | 끝 | 길이(초) | 실패 |\n|---|---|---|---|---|")
for i, (a, b, n) in enumerate(bursts, 1):
    p(f"| {i} | {rel(a):.1f} | {rel(b):.1f} | {b-a:.1f} | {n} |")
p("\n## 경고 firing 구간\n\n| # | 시작 | 끝 | 길이(초) |\n|---|---|---|---|")
for i, (a, b) in enumerate(fire_iv, 1):
    p(f"| {i} | {rel(a):.0f} | {rel(b):.0f} | {b-a+1} |")
p("\n## 자동 복구기 기록\n\n| T+초 | 종류 | 내용 |\n|---|---|---|")
for e in ev:
    if e["type"] == "start": continue
    d = {k: v for k, v in e.items() if k not in ("t", "mode", "type")}
    if e["type"] == "notification":
        d = {"status": e["status"], "alerts": [a["status"] for a in e["alerts"]]}
    p(f"| {rel(e['t']):.1f} | {e['type']} | {json.dumps(d, ensure_ascii=False)} |")
os.makedirs(f"results/{mode}", exist_ok=True)
open(f"results/{mode}/summary.md", "w").write("\n".join(out) + "\n")
print("\n".join(out[:20]))
