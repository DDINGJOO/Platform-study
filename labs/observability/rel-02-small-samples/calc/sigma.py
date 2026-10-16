"""3편 계산: 지연 분포에 평균+3σ 문턱을 걸면 몇 %가 넘나, n과 n-1, 시간 기준과 요청 기준 (표준 라이브러리만)."""
import math, random, statistics as st

Phi = lambda z: 0.5 * math.erfc(-z / math.sqrt(2))

print("[1] 정규분포라면: P(X > μ+3σ) =", f"{100*(1-Phi(3)):.4f}%")

print("\n[2] 로그정규 지연(중앙값 100ms)에서 '진짜' 평균+3σ 를 넘는 비율")
for s in (0.25, 0.5, 1.0, 1.5):
    m = math.log(100)
    mean = math.exp(m + s * s / 2)
    sd = math.sqrt((math.exp(s * s) - 1) * math.exp(2 * m + s * s))
    t = mean + 3 * sd
    p = 1 - Phi((math.log(t) - m) / s)
    p999 = math.exp(m + s * 3.090232)
    print(f"  σ_log={s:<4} 평균 {mean:8.1f}ms  표준편차 {sd:9.1f}ms  μ+3σ={t:9.1f}ms  넘는 비율 {100*p:.3f}%  (참고 p99.9={p999:.0f}ms)")

print("\n[3] 두 봉우리(빠른 경로 95% 중앙값 20ms + 느린 경로 5% 중앙값 400ms, 각 σ_log 0.3)")
rnd = random.Random(42)
xs = [rnd.lognormvariate(math.log(20), 0.3) if rnd.random() < 0.95 else rnd.lognormvariate(math.log(400), 0.3) for _ in range(200000)]
mu, sd = st.fmean(xs), st.pstdev(xs)
t = mu + 3 * sd
print(f"  표본 20만 개: 평균 {mu:.1f}ms, 표준편차 {sd:.1f}ms, μ+3σ={t:.1f}ms, 넘는 비율 {100*sum(x>t for x in xs)/len(xs):.3f}%")
print(f"  μ+2σ={mu+2*sd:.1f}ms 넘는 비율 {100*sum(x>mu+2*sd for x in xs)/len(xs):.3f}% (정규 가정 2.275%)")
srt = sorted(xs)
print(f"  p50={srt[len(srt)//2]:.1f}ms p95={srt[int(.95*len(srt))]:.1f}ms p99={srt[int(.99*len(srt))]:.1f}ms")

print("\n[4] 적은 표본으로 μ, σ 를 추정해 문턱을 정하면 (로그정규 σ_log=1.0, 기준 구간 n개로 추정 → 새 요청 10만 개에 적용)")
for n in (30, 100, 1000):
    rates = []
    for rep in range(200):
        r = random.Random(1000 * n + rep)
        base = [r.lognormvariate(math.log(100), 1.0) for _ in range(n)]
        thr = st.fmean(base) + 3 * st.stdev(base)
        p = 1 - Phi((math.log(thr) - math.log(100)) / 1.0)
        rates.append(100 * p)
    rates.sort()
    print(f"  n={n:>5}: 넘는 비율 중앙값 {rates[100]:.3f}%, 5~95% 범위 {rates[10]:.3f}% ~ {rates[190]:.3f}%")

print("\n[5] n 과 n-1: 에러율 10개(0.054 ... 0.044)")
d = [0.054, 0.048, 0.043, 0.052, 0.049, 0.064, 0.062, 0.047, 0.045, 0.044]
print(f"  평균 {st.fmean(d):.4f}, n-1(표본, STDEV.S) {st.stdev(d):.5f}, n(모집단, STDEV.P, numpy 기본) {st.pstdev(d):.5f}, 비 {st.stdev(d)/st.pstdev(d):.4f} = sqrt(10/9) {math.sqrt(10/9):.4f}")

print("\n[6] 라플라스(위치 15, 척도 3): P(0<X<30) = 1-e^-5 =", f"{100*(1-math.exp(-5)):.3f}%", ", P(X<0) =", f"{100*0.5*math.exp(-5):.3f}%")

print("\n[7] '시간의 10%'와 '요청의 10%'")
for label, quiet_n, busy_n in (("바쁜 분이 느린 경우", 10, 500), ("조용한 분이 느린 경우", 500, 10)):
    # 60분 중 54분은 정상(100ms), 6분은 느림(3.5s). 분마다 요청 수가 다르다
    slow_req = 6 * busy_n; fast_req = 54 * quiet_n
    print(f"  {label}: 느린 6분(시간의 10%)에 든 요청 {slow_req}건 / 전체 {slow_req+fast_req}건 = 요청의 {100*slow_req/(slow_req+fast_req):.1f}%")

print("\n[8] 몬테카를로: 호출 셋을 차례로 부르고, 두 번째 호출은 1% 확률로 1초 타임아웃 뒤 한 번 재시도할 때 전체 > 1초 확률")
r = random.Random(7)
N = 200000; over = 0
for _ in range(N):
    a = r.lognormvariate(math.log(40), 0.5)
    b = r.lognormvariate(math.log(80), 0.6)
    if r.random() < 0.01:
        b = 1000 + r.lognormvariate(math.log(80), 0.6)
    c = r.lognormvariate(math.log(30), 0.4)
    over += (a + b + c) > 1000
p = over / N
print(f"  {N}번 시행: {100*p:.3f}% (표준오차 ±{100*math.sqrt(p*(1-p)/N):.3f}%p)")

print("\n[9] 로그를 씌운 뒤 평균+3σ (기하 문턱): exp(mean(ln x) + 3*sd(ln x))")
for name, gen in (("로그정규 σ_log 1.0", lambda r: r.lognormvariate(math.log(100), 1.0)),
                  ("두 봉우리(95% 20ms + 5% 400ms)", lambda r: r.lognormvariate(math.log(20), 0.3) if r.random() < 0.95 else r.lognormvariate(math.log(400), 0.3))):
    r = random.Random(11)
    xs = [gen(r) for _ in range(200000)]
    ls = [math.log(x) for x in xs]
    thr = math.exp(st.fmean(ls) + 3 * st.pstdev(ls))
    print(f"  {name}: 문턱 {thr:.1f}ms, 넘는 비율 {100*sum(x>thr for x in xs)/len(xs):.3f}%")

print("\n[10] 기준 구간이 장애를 품으면: 정상 로그정규(중앙값 100ms, σ_log 0.5) 1만 건 + 장애 구간 x% 가 2초로 느림")
for frac in (0, 0.005, 0.01, 0.02):
    r = random.Random(5)
    base = [r.lognormvariate(math.log(100), 0.5) for _ in range(10000)]
    k = int(frac * 10000)
    base[:k] = [2000.0] * k
    thr = st.fmean(base) + 3 * st.stdev(base)
    print(f"  장애 몫 {frac*100:.1f}%: 평균 {st.fmean(base):.0f}ms σ {st.stdev(base):.0f}ms → 문턱 {thr:.0f}ms")
