"""loadavg.csv(/proc/loadavg 가 바뀐 순간들)로 그림 한 장과 갱신 간격을 낸다.

사용: docker run --rm -v "$PWD:/work" obs-lab/metrics-05-ewma-plot:dev plot/plot_loadavg.py data/loadavg.csv out/ [태운 프로세스 수, 기본 8]
"""
import csv, math, os, statistics, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

src, out = sys.argv[1], sys.argv[2]
N = int(sys.argv[3]) if len(sys.argv) > 3 else 8
os.makedirs(out, exist_ok=True)
for f in font_manager.findSystemFonts():
    if "NanumGothic.ttf" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams.update({"font.family": "NanumGothic", "axes.unicode_minus": False, "font.size": 11,
                     "axes.spines.top": False, "axes.spines.right": False})

rows = list(csv.DictReader(open(src)))
t = [float(r["t"]) for r in rows]
L = {k: [float(r[k]) for r in rows] for k in ("l1", "l5", "l15")}
ph = [r["phase"] for r in rows]
t_on = next(x for x, p in zip(t, ph) if p == "on")
t_off = next(x for x, p in zip(t, ph) if p == "off")

# 갱신 간격. 첫 줄은 기록 시작이라 뺀다
iv = [b - a for a, b in zip(t[1:], t[2:])]
ok = [x for x in iv if 4.5 < x < 5.5]
print(f"갱신 {len(t)-1}번, 간격 중앙값 {statistics.median(ok):.4f}s, 평균 {statistics.mean(ok):.4f}s, "
      f"4.5~5.5초 밖 {len(iv)-len(ok)}번 {[round(x,3) for x in iv if not 4.5 < x < 5.5][:10]}")
span = t[-1] - t[1]; n = round(span / 5.0)
print(f"두 번째 갱신부터 마지막 갱신까지 {span:.3f}s / {n}번 = {span/n:.5f}s")

# 기준선: 태우기 직전 60초의 1분값 평균
B = statistics.mean([v for x, v in zip(t, L["l1"]) if t_on - 60 <= x < t_on])
TAU = {"l1": -5.001 / math.log(1884 / 2048), "l5": -5.001 / math.log(2014 / 2048), "l15": -5.001 / math.log(2037 / 2048)}
start = {k: next(v for x, v in zip(t, L[k]) if x >= t_on) for k in L}
def theory(k, x):
    tau = TAU[k]
    if x < t_on:
        return math.nan
    if x < t_off:
        return B + (start[k] - B) * math.exp(-(x - t_on) / tau) + N * (1 - math.exp(-(x - t_on) / tau))
    top = theory(k, t_off - 1e-9)
    return B + (top - B) * math.exp(-(x - t_off) / tau)
print(f"기준선 B = {B:.2f} (태우기 전 60초 1분값 평균), N = {N}, 실효 τ = " + ", ".join(f"{k} {TAU[k]:.1f}s" for k in TAU))
for base, name in ((t_on, "켠 뒤"), (t_off, "끈 뒤")):
    for s in (60, 300, 600, 900):
        x = base + s
        if x > t[-1] or (name == "켠 뒤" and x > t_off):
            continue
        i = min(range(len(t)), key=lambda j: abs(t[j] - x))
        print(f"  {name} +{s:4d}s  " + "  ".join(f"{k}={L[k][i]:5.2f}(이론 {theory(k, t[i]):5.2f})" for k in L))
for k in L:
    d = [v - theory(k, x) for x, v in zip(t, L[k]) if x > t_on + 30]
    print(f"  {k}: 실측-이론 평균 {statistics.mean(d):+.2f}, 최대 |차이| {max(abs(v) for v in d):.2f}")

C = {"l1": "#4a7fb5", "l5": "#e5a33c", "l15": "#e5533c"}
NAME = {"l1": "1분", "l5": "5분", "l15": "15분"}
fig, ax = plt.subplots(figsize=(9, 4.4), dpi=150)
mm = lambda x: (x - t_on) / 60
ax.axvspan(0, mm(t_off), color="#fdf3dd", lw=0)
for k in L:
    ax.plot([mm(x) for x in t], L[k], color=C[k], lw=2.0, label=f"/proc/loadavg {NAME[k]}")
    ax.plot([mm(x) for x in t], [theory(k, x) for x in t], color="black", lw=0.9, ls=":")
ax.plot([], [], color="black", lw=0.9, ls=":", label=f"이론: 기준선 {B:.1f} + {N}·(1-e^(-t/τ))")
ax.axhline(B, color="#8a8272", lw=0.8, ls="--")
ax.set_xlabel(f"CPU 태우기 {N}개를 켠 뒤 지난 시간 (분), 노란 구간이 켜 둔 시간"); ax.set_ylabel("로드 애버리지")
ax.legend(loc="upper right", fontsize=9, frameon=False)
fig.tight_layout(); fig.savefig(os.path.join(out, "loadavg.png")); plt.close(fig)
