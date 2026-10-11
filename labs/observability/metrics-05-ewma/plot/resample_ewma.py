"""results/samples.csv(1초 간격 누적 카운트)를 Δt 초 간격으로 솎아 m1/m5/m15 를 다시 계산하고 Meter 값과 비교한다.
α 는 간격에 맞춰 1 - e^(-Δt/τ) 로 다시 잡는다. 사용: python3 plot/resample_ewma.py results/samples.csv
"""
import csv, math, sys
rows = list(csv.DictReader(open(sys.argv[1])))
t = [float(r["t"]) for r in rows]; c = [int(r["count"]) for r in rows]
TAU = {"m1": 60, "m5": 300, "m15": 900}
for dt in (5, 30, 60):
    idx = list(range(0, len(rows), dt))
    out = []
    for k, tau in TAU.items():
        a = 1 - math.exp(-dt / tau); rate = None; err = []
        for i, j in zip(idx, idx[1:]):
            inst = (c[j] - c[i]) / (t[j] - t[i])
            rate = inst if rate is None else rate + a * (inst - rate)
            if t[j] > 150:   # 부하 시작(120.5초) 직후 몇 칸은 계단 위치 차이가 크다
                err.append(abs(rate - float(rows[j]["early_" + k])))
        out.append(f"{k} 평균 {sum(err)/len(err):.3f} 최대 {max(err):.2f}")
    print(f"간격 {dt:2d}초: " + ", ".join(out))
