"""1분값의 변화로 커널이 매번 넣은 표본 n 을 거꾸로 구하고, 그 n 으로 5분값·15분값을 다시 계산해 본다.

세 평균에는 같은 n 이 들어간다. 그래서 1분값만 보고 구한 n 으로 나머지 둘이 재현되면
상수(1884, 2014, 2037)와 갱신 방식이 맞는다는 뜻이다. 다른 컨테이너의 부하(잡음)는 n 에 그대로 들어가므로 상관없다.
사용: python3 plot/infer_loadavg.py results/loadavg.csv
"""
import csv, math, sys
rows = list(csv.DictReader(open(sys.argv[1])))[1:]   # 첫 줄은 기록 시작 시점이라 갱신이 아니다
l1 = [float(r["l1"]) for r in rows]; l5 = [float(r["l5"]) for r in rows]; l15 = [float(r["l15"]) for r in rows]
e1 = 1884 / 2048
ns = [(b - a * e1) / (1 - e1) for a, b in zip(l1, l1[1:])]
print(f"구한 n: 최소 {min(ns):.1f}, 최대 {max(ns):.1f}, 평균 {sum(ns)/len(ns):.2f} ({len(ns)}번)")
for name, consts in (("커널 고정소수점 상수", (2014 / 2048, 2037 / 2048)), ("이론값 e^(-5.001/300), e^(-5.001/900)", (math.exp(-5.001 / 300), math.exp(-5.001 / 900)))):
    for label, series, e in (("5분", l5, consts[0]), ("15분", l15, consts[1])):
        v = series[0]; err = []
        for n, actual in zip(ns, series[1:]):
            v = v * e + n * (1 - e)
            err.append(v - actual)
        print(f"{name:28s} {label:3s}: 끝값 계산 {v:.2f} / 실제 {series[-1]:.2f}, 평균 |오차| {sum(map(abs, err))/len(err):.3f}, 최대 {max(map(abs, err)):.3f}")
