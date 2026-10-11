"""samples.csv(앱이 1초마다 남긴 값)로 그림 세 장을 그리고, 글에 쓴 숫자를 찍는다.

사용: docker run --rm -v "$PWD:/work" obs-lab/metrics-05-ewma-plot:dev plot/plot_ewma.py data/samples.csv out/
"""
import csv, math, sys, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

src, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
for f in font_manager.findSystemFonts():
    if "NanumGothic.ttf" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams.update({"font.family": "NanumGothic", "axes.unicode_minus": False, "font.size": 11,
                     "axes.spines.top": False, "axes.spines.right": False})
C = {"m1": "#4a7fb5", "m5": "#e5a33c", "m15": "#e5533c", "target": "#8a8272", "win": "#2e6b41", "step": "#7b5ea7"}
TAU = {"m1": 60.0, "m5": 300.0, "m15": 900.0}

rows = list(csv.DictReader(open(src)))
f = lambda r, k: float(r[k]) if r[k] != "" else math.nan
t = [float(r["t"]) for r in rows]
target = [float(r["target"]) for r in rows]
# 부하가 켜지고 꺼진 시각: target 이 바뀐 두 표본의 가운데
on_i = next(i for i, v in enumerate(target) if v > 0)
off_i = next(i for i in range(on_i, len(target)) if target[i] == 0)
t_on = (t[on_i - 1] + t[on_i]) / 2
t_off = (t[off_i - 1] + t[off_i]) / 2
R = 100.0
def theory(k, tt):
    tau = TAU[k]
    if tt < t_on:
        return 0.0
    if tt < t_off:
        return R * (1 - math.exp(-(tt - t_on) / tau))
    top = R * (1 - math.exp(-(t_off - t_on) / tau))
    return top * math.exp(-(tt - t_off) / tau)

m = lambda tt: (tt - t_on) / 60.0  # 부하 시작 기준 분
print(f"t_on={t_on:.1f}s t_off={t_off:.1f}s load={(t_off - t_on) / 60:.2f}min rows={len(rows)} last_t={t[-1]:.0f}s")

# ---------- 그림 1: 계단 응답 + 이론 곡선 ----------
fig, ax = plt.subplots(figsize=(9, 4.6), dpi=150)
ax.plot([m(x) for x in t], target, color=C["target"], lw=1.4, ls="--", label="넣은 부하 (초당 100건)")
for k in ("m1", "m5", "m15"):
    ax.plot([m(x) for x in t], [f(r, "early_" + k) for r in rows], color=C[k], lw=2.2, label=f"드롭위저드 {k} 실측")
    ax.plot([m(x) for x in t], [theory(k, x) for x in t], color="black", lw=0.9, ls=":")
ax.plot([], [], color="black", lw=0.9, ls=":", label="이론 100·(1-e^(-t/τ))")
ax.set_xlabel("부하를 켠 뒤 지난 시간 (분)"); ax.set_ylabel("초당 건수")
ax.set_xlim(m(t[0]), m(t[-1])); ax.set_ylim(0, 108)
ax.legend(loc="center right", fontsize=9, frameon=False)
ax.set_title("초당 100건을 30분 넣었다 뺐을 때 Meter 의 세 비율", fontsize=12)
fig.tight_layout(); fig.savefig(os.path.join(out, "step-response.png")); plt.close(fig)

# 글에 쓸 숫자: 특정 시점의 실측과 이론
def at(sec_from, base, key):
    tt = base + sec_from
    i = min(range(len(t)), key=lambda j: abs(t[j] - tt))
    return t[i], f(rows[i], key)
print("\n[부하 시작 후] 시점, m1/m5/m15 실측 (이론)")
for s in (60, 300, 900, t[off_i - 1] - t_on):   # 마지막은 끄기 직전 행
    tt, _ = at(s, t_on, "early_m1")
    vals = " ".join(f"{k}={f(rows[min(range(len(t)), key=lambda j: abs(t[j]-tt))], 'early_'+k):6.2f}({theory(k, tt):6.2f})" for k in ("m1", "m5", "m15"))
    print(f"  +{s:7.1f}s  {vals}")
print("[부하 끈 후]")
for s in (60, 276, 300, 900, 1380, 1800 - 5):
    tt, _ = at(s, t_off, "early_m1")
    if tt > t[-1]: continue
    i = min(range(len(t)), key=lambda j: abs(t[j] - tt))
    vals = " ".join(f"{k}={f(rows[i], 'early_'+k):7.3f}({theory(k, tt):7.3f})" for k in ("m1", "m5", "m15"))
    print(f"  +{s:5d}s  {vals}")
# 실측과 이론의 최대 차이(부하 구간 이후 20초 지난 뒤부터)
for k in ("m1", "m5", "m15"):
    d = [abs(f(r, "early_" + k) - theory(k, x)) for r, x in zip(rows, t) if x > t_on + 20]
    print(f"  max|실측-이론| {k} = {max(d):.2f}")
# 1% 밑으로 내려간 시각
for k in ("m1", "m5", "m15"):
    top = f(rows[off_i - 1], "early_" + k)
    hit = next((x for r, x in zip(rows, t) if x > t_off and f(r, "early_" + k) < 1.0), None)
    print(f"  {k}: 끌 때 {top:.2f} -> 1 미만까지 {('%.0fs' % (hit - t_off)) if hit else '도달 안 함'}")

# ---------- 그림 2: 같은 사건, 세 가지 1분 비율 ----------
fig, axes = plt.subplots(1, 2, figsize=(9, 3.8), dpi=150, sharey=True)
for ax, base, title in ((axes[0], t_on, "부하를 켠 직후"), (axes[1], t_off, "부하를 끈 직후")):
    sel = [i for i, x in enumerate(t) if base - 20 <= x <= base + 200]
    xs = [t[i] - base for i in sel]
    ax.plot(xs, [target[i] for i in sel], color=C["target"], lw=1.3, ls="--", label="넣은 부하")
    ax.plot(xs, [f(rows[i], "early_m1") for i in sel], color=C["m1"], lw=2.2, label="드롭위저드 m1 (EWMA)")
    ax.plot(xs, [f(rows[i], "win60") for i in sel], color=C["win"], lw=2.0, label="최근 60초 창 (rate[1m] 방식)")
    ax.plot(xs, [f(rows[i], "step60") for i in sel], color=C["step"], lw=2.0, label="마이크로미터 STEP 1분")
    ax.set_title(title, fontsize=11); ax.set_xlabel("초")
    ax.axvline(60, color="#cccccc", lw=0.8)
axes[0].set_ylabel("초당 건수"); axes[0].set_ylim(-3, 108)
axes[1].legend(loc="upper right", fontsize=8.5, frameon=False)
fig.tight_layout(); fig.savefig(os.path.join(out, "three-1m-rates.png")); plt.close(fig)

print("\n[1분 비율 비교] 켠 뒤/끈 뒤 +30s, +60s, +90s : m1 / win60 / step60")
for base, name in ((t_on, "켠 뒤"), (t_off, "끈 뒤")):
    for s in (30, 60, 61, 90, 120, 121):
        i = min(range(len(t)), key=lambda j: abs(t[j] - (base + s)))
        print(f"  {name} +{s:3d}s  m1={f(rows[i],'early_m1'):6.2f}  win60={f(rows[i],'win60'):6.2f}  step60={f(rows[i],'step60'):6.2f}")
# STEP 값이 바뀐 시각
prev = None
for r, x in zip(rows, t):
    v = f(r, "step60")
    if prev is not None and v != prev and abs(x - t_on) < 200:
        print(f"  step60 {prev:.2f} -> {v:.2f} at t_on{(x - t_on):+.1f}s")
    if prev is not None and v != prev and 0 < x - t_off < 200:
        print(f"  step60 {prev:.2f} -> {v:.2f} at t_off{(x - t_off):+.1f}s")
    prev = v

# ---------- 그림 3: 미리 만든 Meter vs 부하와 함께 만든 Meter ----------
fig, ax = plt.subplots(figsize=(9, 3.8), dpi=150)
sel = [i for i, x in enumerate(t) if t_on - 30 <= x <= t_on + 600]
xs = [t[i] - t_on for i in sel]
ax.plot(xs, [target[i] for i in sel], color=C["target"], lw=1.3, ls="--", label="넣은 부하")
ax.plot(xs, [f(rows[i], "early_m15") for i in sel], color=C["m15"], lw=2.2, label="m15, 앱이 뜰 때 만든 Meter")
ax.plot(xs, [f(rows[i], "late_m15") for i in sel], color="#3d3a34", lw=2.2, label="m15, 부하가 시작될 때 만든 Meter")
ax.set_xlabel("부하를 켠 뒤 지난 시간 (초)"); ax.set_ylabel("초당 건수"); ax.set_ylim(-3, 110)
ax.legend(loc=(0.06, 0.42), fontsize=9, frameon=False)
fig.tight_layout(); fig.savefig(os.path.join(out, "early-vs-late.png")); plt.close(fig)
first_late = next((x for r, x in zip(rows, t) if r["late_m15"] not in ("", "0.000000")), None)
if first_late:
    i = t.index(first_late)
    print(f"\n[late] 첫 0 아닌 값 at t_on{first_late - t_on:+.1f}s: m1={f(rows[i],'late_m1'):.2f} m5={f(rows[i],'late_m5'):.2f} m15={f(rows[i],'late_m15'):.2f}")
    print(f"       같은 시각 early: m1={f(rows[i],'early_m1'):.2f} m5={f(rows[i],'early_m5'):.2f} m15={f(rows[i],'early_m15'):.2f}")

# 실행 끝(마지막 행)의 m15, early vs late
r = rows[-1]
print(f"\n[실행 끝] t_off{t[-1] - t_off:+.1f}s: early m15={f(r,'early_m15'):.2f} (이론 {theory('m15', t[-1]):.2f}), late m15={f(r,'late_m15'):.2f}")
