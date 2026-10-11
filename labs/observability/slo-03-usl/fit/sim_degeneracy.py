"""5편의 모의 실험: USL 곡선(λ=100, σ=0.05, κ=0.001)에 표준 편차 3% 오차를 섞은 가짜 측정 200벌을 만들고,
어디까지의 점으로 맞추느냐에 따라 계수와 예측이 얼마나 흩어지는지 본다. 실제 측정이 아니다.

사용: docker compose --profile fit run --rm --entrypoint python fit /fit/sim_degeneracy.py [시드 ...]
κ = 0 으로 맞춰진 벌은 N* = ∞ 로 세고 중앙값에 넣는다.
"""
import sys

import numpy as np
from scipy.optimize import curve_fit


def usl(n, l, s, k):
    return l * n / (1 + s * (n - 1) + k * n * (n - 1))


N = np.array([1, 2, 4, 6, 8, 12, 16, 24, 32, 48, 64], float)
TRUE = (100, 0.05, 0.001)
seeds = [int(x) for x in sys.argv[1:]] or [7]
for seed in seeds:
    rng = np.random.default_rng(seed)
    res = {8: [], 16: [], 64: []}
    for _ in range(200):
        X = usl(N, *TRUE) * (1 + rng.normal(0, 0.03, len(N)))
        for lim in res:
            m = N <= lim
            p, _ = curve_fit(usl, N[m], X[m], p0=[100, 0.01, 1e-4], bounds=([0, 0, 0], [np.inf, 1, 1]), maxfev=20000)
            ns = np.sqrt((1 - p[1]) / p[2]) if p[2] > 1e-9 else np.inf
            res[lim].append((p[2] <= 1e-9, ns, usl(64, *p)))
    for lim, r in res.items():
        k0 = np.mean([x[0] for x in r])
        ns = np.median([x[1] for x in r])
        x64 = np.percentile([x[2] for x in r], [10, 90])
        print(f"seed={seed} N<={lim:<2}  κ=0 비율 {k0:4.0%}  N* 중앙값(κ=0 은 ∞) {ns:6.1f}  X(64) 10~90% {x64[0]:6.0f} ~ {x64[1]:6.0f}")
