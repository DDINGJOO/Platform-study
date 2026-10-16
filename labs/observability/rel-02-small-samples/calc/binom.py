"""2편 계산 1: 이항 신뢰구간과 '에러 몇 건이 버짓 전부인가' (표준 라이브러리만)."""
import math

def binom_cdf(k, n, p):
    # P(X <= k), 로그 공간에서 더한다
    if k < 0: return 0.0
    if k >= n: return 1.0
    s = 0.0
    lp, lq = math.log(p) if p > 0 else -math.inf, math.log1p(-p) if p < 1 else -math.inf
    for i in range(0, k + 1):
        lc = math.lgamma(n + 1) - math.lgamma(i + 1) - math.lgamma(n - i + 1)
        t = lc + (i * lp if i else 0.0) + ((n - i) * lq if n - i else 0.0)
        s += math.exp(t)
    return min(1.0, s)

def bisect(f, lo, hi, it=200):
    for _ in range(it):
        mid = (lo + hi) / 2
        if f(mid): hi = mid
        else: lo = mid
    return (lo + hi) / 2

def clopper_pearson(x, n, alpha=0.05):
    """실패 x건 / n건의 실패율 p 에 대한 정확한(보수적) 구간."""
    lo = 0.0 if x == 0 else bisect(lambda p: 1 - binom_cdf(x - 1, n, p) >= alpha / 2, 0, 1)
    hi = 1.0 if x == n else bisect(lambda p: binom_cdf(x, n, p) <= alpha / 2, 0, 1)
    return lo, hi

def wilson(x, n, z=1.959964):
    ph = x / n
    c = (ph + z * z / (2 * n)) / (1 + z * z / n)
    h = z * math.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return c - h, c + h

print("관측된 성공률의 95% 신뢰구간 (실패 x건 / 전체 n건)")
print(f"{'n':>8} {'x':>5} {'관측 SLI':>10}  {'Wilson':>22}  {'Clopper-Pearson(정확)':>24}")
for n, x in [(100, 0), (1000, 0), (1000, 1), (10000, 10), (100000, 100), (1000000, 1000)]:
    w = wilson(x, n); c = clopper_pearson(x, n)
    print(f"{n:>8} {x:>5} {100*(1-x/n):>9.3f}%  {100*(1-w[1]):>9.3f}% ~ {100*(1-w[0]):>8.3f}%  {100*(1-c[1]):>10.3f}% ~ {100*(1-c[0]):>8.3f}%")

print("\n실패 0건일 때 '진짜 성공률이 이 값 이상'이라고 95%로 말할 수 있는 하한 (단측, 1-0.05^(1/n))")
for n in (100, 300, 1000, 3000, 10000):
    print(f"  n={n:>6}: {100*(0.05**(1/n)):.3f}%   (3/n 근사: {100*(1-3/n):.3f}%)")

print("\n소수 둘째 자리 SLI의 표준오차: p=78.56%")
for n in (1000, 10000, 100000):
    se = math.sqrt(0.7856 * 0.2144 / n)
    print(f"  n={n:>6}: 표준오차 {100*se:.2f}%p, 95% 폭 ±{196*se:.2f}%p")

print("\n99.9% SLO, 30일 동안 받는 요청 수별 에러 예산(건)")
for per_hour in (1, 10, 100, 1000, 10000):
    n = per_hour * 720
    print(f"  시간당 {per_hour:>6}건 → 30일 {n:>8}건, 예산 {n*0.001:>8.1f}건, 에러 1건 = 예산의 {100/(n*0.001):.2f}%")

print("\n한 건의 실패가 창 하나의 burn rate 를 얼마로 만드나 (SLO 99.9%)")
for per_hour in (10, 70, 100, 1000):
    for win, mins in (("1시간", 60), ("5분", 5)):
        n = per_hour * mins / 60
        print(f"  시간당 {per_hour:>5}건, {win} 창(요청 {n:7.1f}건): 실패 1건이면 burn rate {(1/n)/0.001:8.1f}")
print("  14.4배 문턱을 실패 1건이 넘지 않으려면 창 안 요청이", math.ceil(1/0.0144), "건 이상 필요")
print("  6배 문턱을 실패 1건이 넘지 않으려면 창 안 요청이", math.ceil(1/0.006), "건 이상 필요")

print("\n한 달 요청 n건, 진짜 실패율 p 일 때 월간 SLI 가 99.9% 밑으로 찍힐 확률 (실패 > 0.001n 건)")
for p in (0.0005, 0.001, 0.002):
    line = []
    for n in (1000, 10000, 100000):
        k = math.floor(0.001 * n + 1e-9)       # 허용 실패 수. 이보다 많으면 위반
        line.append(f"n={n:>6}: {100*(1-binom_cdf(k, n, p)):5.1f}%")
    print(f"  p={p*100:.2f}% (진짜 SLI {100-p*100:.2f}%)  " + "   ".join(line))

print("\n진짜 SLI 99.9% 근처를 95% 구간 반폭 h 로 재려면 필요한 요청 수 (정규 근사 n = 1.96^2 p(1-p) / h^2)")
for h in (0.1, 0.05, 0.02, 0.01):
    n = 1.959964 ** 2 * 0.001 * 0.999 / (h / 100) ** 2
    print(f"  ±{h:.2f}%p → 약 {n:,.0f}건")
