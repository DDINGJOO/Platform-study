"""이식한 분류기로 '표본 수와 차이 크기에 따라 High 가 나오는 비율'을 모의 실험한다.
베이스라인 값은 평균 100, 표준편차 10 의 정규분포. 카나리는 평균만 shift% 만큼 올린다.
각 조합을 200번 반복해 High 로 분류된 비율을 센다. 시드 고정.
"""
import random, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mannwhitney import classify

rng = random.Random(42)
shifts = [0, 1, 3, 5, 10]
ns = [10, 30, 60, 180]
print("n\\shift%", *shifts, sep="\t")
for n in ns:
    row = []
    for sh in shifts:
        hi = 0
        for _ in range(200):
            c = [rng.gauss(100, 10) for _ in range(n)]
            e = [rng.gauss(100 * (1 + sh / 100), 10) for _ in range(n)]
            hi += classify(c, e, "increase")["classification"] == "High"
        row.append(f"{hi/200:.0%}")
    print(n, *row, sep="\t")
print()
print("allowedIncrease=1.10 (평균이 10% 이상 늘어야 High)")
for n in ns:
    row = []
    for sh in shifts:
        hi = 0
        for _ in range(200):
            c = [rng.gauss(100, 10) for _ in range(n)]
            e = [rng.gauss(100 * (1 + sh / 100), 10) for _ in range(n)]
            hi += classify(c, e, "increase", allowed_increase=1.10)["classification"] == "High"
        row.append(f"{hi/200:.0%}")
    print(n, *row, sep="\t")
