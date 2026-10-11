"""CPU 시나리오 셋을 한 그래프에: 단계별 평균과 세 번(또는 두 번) 측정의 최소~최대."""
import csv
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

series = [
    ("cpu.csv", "spin 2ms by wall clock, quota cpus=2", "#e5a33c", "o"),
    ("cpu-fixed.csv", "fixed work (1.8M loops), quota cpus=2", "#e5533c", "s"),
    ("cpu-cpuset.csv", "fixed work, pinned to 2 cores, no quota", "#4a7fb5", "^"),
]
fig, ax = plt.subplots(figsize=(8, 4.6), dpi=120)
for f, label, color, m in series:
    g = defaultdict(list)
    for r in csv.DictReader(open(f)):
        g[float(r["n"])].append(float(r["x_rps"]))
    ns = sorted(g)
    mean = np.array([np.mean(g[n]) for n in ns])
    lo = mean - np.array([min(g[n]) for n in ns])
    hi = np.array([max(g[n]) for n in ns]) - mean
    ax.errorbar(ns, mean, yerr=[lo, hi], color=color, marker=m, ms=5, lw=1.8, capsize=3, label=label)
ax.axhline(1000, color="#8a8272", ls=":", lw=1.2)
ax.text(40, 1010, "2 cores / 2ms = 1,000 req/s", color="#8a8272", fontsize=8.5)
ax.set_xlabel("concurrency N (k6 VUs, closed loop)")
ax.set_ylabel("throughput X (req/s)  mean, min~max of runs")
ax.set_ylim(0, 1500)
ax.grid(alpha=0.25)
ax.legend(loc="lower right", fontsize=8.5, frameon=False)
fig.tight_layout()
fig.savefig("cpu-compare.png")
print("saved cpu-compare.png")
