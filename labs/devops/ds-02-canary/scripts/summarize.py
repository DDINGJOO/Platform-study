"""results/raw/ 의 판정 로그를 사람이 읽을 표로 줄인다(시각은 첫 판정부터의 경과, 값은 ms 로 반올림).
사용: python3 scripts/summarize.py
raw/ 에는 유닉스 시각과 긴 소수가 들어 있어 커밋하지 않는다(.gitignore)."""
import json, os
R = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results")

def ms(v):
    return "-" if v is None else f"{v*1000:.1f}"

def row(d):
    cells = []
    for m in d["metrics"]:
        name = m[0] if isinstance(m, list) else m["name"]
        cls = m[1] if isinstance(m, list) else m["classification"]
        ne = m[3] if isinstance(m, list) else m.get("n_experiment")
        cm = m[4] if isinstance(m, list) else m.get("control_mean")
        em = m[5] if isinstance(m, list) else m.get("experiment_mean")
        if name == "error_ratio":
            cells.append(f"{name} {cls} n={ne} {'-' if cm is None else f'{cm:.4f}'}/{'-' if em is None else f'{em:.4f}'}")
        else:
            cells.append(f"{name} {cls} {ms(cm)}/{ms(em)}ms")
    return cells

out = []
src = os.path.join(R, "raw", "s2-judge-all.log")
lines = [json.loads(l) for l in open(src) if l.startswith("{") and '"score"' in l]
t0 = None
for d in lines:
    if t0 is None:
        t0 = d["t"]
    out.append(f"+{d['t']-t0:6.0f}s {d['label']:<14} {d['score']:>5} {d['verdict']:<8} | " + " | ".join(row(d)))
open(os.path.join(R, "s2-judgments.txt"), "w").write(
    "# 시나리오 2 판정 로그 요약. 앞 10줄 = 정상 버전 v2(s2a), 뒤 6줄 = 5ms 느린 v3-slow(s2b)\n"
    "# 지연은 대조군/카나리 평균(ms), error_ratio 는 비율. n 은 카나리 쪽 점 개수\n" + "\n".join(out) + "\n")

src = os.path.join(R, "raw", "s3-lowtraffic-rejudged.jsonl")
if os.path.exists(src):
    out = []
    for l in open(src):
        d = json.loads(l)
        if "metrics" not in d:
            out.append(f"{d.get('label')} ERROR {d.get('error')}")
            continue
        out.append(f"{d['label']:<16} {d['score']:>5} {d['verdict']:<8} | " + " | ".join(row(d)))
    open(os.path.join(R, "s3-lowtraffic.txt"), "w").write(
        "# 시나리오 3. 대조군 v2 vs 나쁜 카나리(+10ms, 에러 1%). 각 부하에서 10분 구간을 step 10/30/60초로 판정\n"
        + "\n".join(out) + "\n")
print("ok")
