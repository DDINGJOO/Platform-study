"""USL 계수를 비선형 최소제곱으로 맞추고 그래프를 그린다.

  X(N) = λN / (1 + σ(N-1) + κN(N-1))

사용: docker compose --profile fit run --rm fit <csv> [--train-max N] [--out png] [--title 문자열]
  --train-max  이 값 이하의 N 만으로 맞춘다(나머지는 '예측을 확인할 점'으로 남긴다)
"""
import argparse
import csv
import math
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import curve_fit


def usl(n, lam, sigma, kappa):
    return lam * n / (1 + sigma * (n - 1) + kappa * n * (n - 1))


SIGMA_MIN = 0.0   # --free-sigma 이면 -1 (σ 가 음수로 내려가는 것을 허용)


def fit(ns, xs):
    lam0 = max(x for n, x in zip(ns, xs) if n == min(ns)) / min(ns)
    p, cov = curve_fit(usl, ns, xs, p0=[lam0, 0.01, 0.0001],
                       bounds=([0, SIGMA_MIN, 0], [np.inf, 1, 1]), maxfev=20000)
    err = np.sqrt(np.diag(cov))
    pred = usl(np.array(ns), *p)
    ss_res = float(np.sum((np.array(xs) - pred) ** 2))
    ss_tot = float(np.sum((np.array(xs) - np.mean(xs)) ** 2))
    return p, err, 1 - ss_res / ss_tot


def peak(lam, sigma, kappa):
    if kappa <= 0:
        return math.inf, lam / sigma if sigma > 0 else math.inf
    n = math.sqrt((1 - sigma) / kappa)
    return n, usl(n, lam, sigma, kappa)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--train-max", type=float, default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--title", default=None)
    ap.add_argument("--extra", default=None, help="맞춤에는 쓰지 않고 그래프에만 얹을 CSV (예: 정점 근처를 촘촘히 잰 것)")
    ap.add_argument("--free-sigma", action="store_true", help="σ ≥ 0 제약을 풀고 맞춘다(기본은 σ, κ ∈ [0, 1])")
    a = ap.parse_args()
    global SIGMA_MIN
    if a.free_sigma:
        SIGMA_MIN = -1.0
        print("# σ 제약 없음(σ ≥ -1)")

    rows = list(csv.DictReader(open(a.csv)))
    ns = [float(r["n"]) for r in rows]
    xs = [float(r["x_rps"]) for r in rows]

    by_n = defaultdict(list)
    for r in rows:
        by_n[float(r["n"])].append(r)

    print(f"# {a.csv}: {len(rows)} points, N = {sorted(by_n)}")
    print(f"{'N':>4} {'X 평균':>8} {'X 최소~최대':>15} {'흔들림%':>7} {'k6 avg ms':>9} {'N/X ms':>8} {'락대기 ms':>8} {'load1':>14}")
    for n in sorted(by_n):
        g = by_n[n]
        x = [float(r["x_rps"]) for r in g]
        avg = [float(r["avg_ms"]) for r in g]
        wait = [float(r["lock_wait_ms"]) for r in g]
        loads = "/".join(r["loadavg1"] for r in g)
        spread = (max(x) - min(x)) / np.mean(x) * 100
        print(f"{n:4.0f} {np.mean(x):8.1f} {min(x):7.1f}~{max(x):7.1f} {spread:7.1f} {np.mean(avg):9.2f} {n/np.mean(x)*1000:8.2f} {np.mean(wait):8.2f} {loads:>14}")

    fits = {}
    p, err, r2 = fit(ns, xs)
    fits["all"] = p
    print("\n[모든 점으로 맞춤]")
    print(f"  λ = {p[0]:.2f} ± {err[0]:.2f}   σ = {p[1]:.5f} ± {err[1]:.5f}   κ = {p[2]:.6f} ± {err[2]:.6f}   R² = {r2:.4f}")
    n_star, x_star = peak(*p)
    print(f"  최대 처리량 지점 N* = {n_star:.1f}, 그때 X = {x_star:.1f}")

    if a.train_max:
        tn = [n for n in ns if n <= a.train_max]
        tx = [x for n, x in zip(ns, xs) if n <= a.train_max]
        p2, err2, r22 = fit(tn, tx)
        fits["train"] = p2
        print(f"\n[N ≤ {a.train_max:g} 만으로 맞춤: 점 {len(tn)}개]")
        print(f"  λ = {p2[0]:.2f} ± {err2[0]:.2f}   σ = {p2[1]:.5f} ± {err2[1]:.5f}   κ = {p2[2]:.6f} ± {err2[2]:.6f}   R² = {r22:.4f}")
        n2, x2 = peak(*p2)
        print(f"  예측 N* = {n2:.1f}, 예측 최대 X = {x2:.1f}")
        print(f"  {'N':>4} {'실측 평균':>9} {'예측':>8} {'오차%':>7}")
        for n in sorted(by_n):
            if n > a.train_max:
                m = np.mean([float(r["x_rps"]) for r in by_n[n]])
                pr = usl(n, *p2)
                print(f"  {n:4.0f} {m:9.1f} {pr:8.1f} {(pr - m) / m * 100:7.1f}")

    # 비교용: κ 를 0 으로 묶은 암달의 법칙
    pa, erra = curve_fit(lambda n, lam, sigma: usl(n, lam, sigma, 0.0), ns, xs, p0=[xs[0], 0.01],
                         bounds=([0, 0], [np.inf, 1]), maxfev=20000)
    pred_a = usl(np.array(ns), pa[0], pa[1], 0.0)
    r2a = 1 - float(np.sum((np.array(xs) - pred_a) ** 2)) / float(np.sum((np.array(xs) - np.mean(xs)) ** 2))
    print(f"\n[κ = 0 으로 묶은 암달 맞춤] λ = {pa[0]:.2f}   σ = {pa[1]:.5f}   천장 λ/σ = {pa[0] / pa[1]:.1f}   R² = {r2a:.4f}")

    best_n = max(by_n, key=lambda n: np.mean([float(r['x_rps']) for r in by_n[n]]))
    print(f"\n실측 최대: N = {best_n:g}, X 평균 = {np.mean([float(r['x_rps']) for r in by_n[best_n]]):.1f}")

    if a.out:
        fig, ax = plt.subplots(figsize=(8, 4.6), dpi=120)
        grid = np.linspace(1, max(ns) * 1.05, 400)
        x1 = np.mean([float(r["x_rps"]) for r in by_n[min(by_n)]]) / min(by_n)
        ax.plot(grid, x1 * grid, ":", color="#8a8272", lw=1.2, label="linear (X(1)·N)")
        ax.scatter(ns, xs, s=22, color="#3d3a34", zorder=3, label="measured (each run)")
        ax.plot(grid, usl(grid, *fits["all"]), color="#4a7fb5", lw=2.2,
                label=f"USL fit, all points (σ={fits['all'][1]:.3f}, κ={fits['all'][2]:.5f})")
        if a.extra:
            er = list(csv.DictReader(open(a.extra)))
            ax.scatter([float(r["n"]) for r in er], [float(r["x_rps"]) for r in er], s=26, marker="x",
                       color="#c07f18", zorder=4, label=f"measured, fine steps ({a.extra}, not used in fit)")
        if "train" in fits:
            ax.plot(grid, usl(grid, *fits["train"]), "--", color="#e5533c", lw=2,
                    label=f"USL fit, N≤{a.train_max:g} only (σ={fits['train'][1]:.3f}, κ={fits['train'][2]:.5f})")
            ax.axvline(a.train_max, color="#e5a33c", lw=1, alpha=0.6)
        ax.set_ylim(0, max(xs) * 1.35)
        ax.set_xlim(0, max(ns) * 1.05)
        ax.set_xlabel("concurrency N (k6 VUs, closed loop)")
        ax.set_ylabel("throughput X (req/s)")
        if a.title:
            ax.set_title(a.title)
        ax.grid(alpha=0.25)
        ax.legend(loc="upper right", fontsize=8.5, frameon=False)
        fig.tight_layout()
        fig.savefig(a.out)
        print(f"\nsaved {a.out}")


if __name__ == "__main__":
    main()
