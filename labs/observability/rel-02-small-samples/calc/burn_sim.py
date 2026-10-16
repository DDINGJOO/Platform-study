"""2편 계산 2: 건강한 서비스(진짜 에러율 = 예산 그대로, burn rate 1)에 다중 창 burn rate 경고를 걸면
트래픽 양에 따라 한 달에 몇 번 울리나. 몬테카를로, 표준 라이브러리만.

- 1분 단위로 요청 수 ~ 포아송(시간당 R/60), 실패 수 ~ 이항(요청 수, p)
- 매 분 평가: page 빠른 단 = 1시간 창과 5분 창의 burn rate 가 둘 다 14.4 초과
              page 느린 단 = 6시간 창과 30분 창이 둘 다 6 초과
- 창 안 요청이 0건이면 그 창은 판정하지 않는다(PromQL 에서 0/0 은 NaN 이라 비교가 거짓이 된다)
- 경고가 꺼진 상태에서 켜지는 순간을 1회로 센다
"""
import math, random, sys

def poisson(rnd, lam):
    if lam < 30:
        L, k, p = math.exp(-lam), 0, 1.0
        while True:
            p *= rnd.random()
            if p <= L: return k
            k += 1
    return max(0, int(round(rnd.gauss(lam, math.sqrt(lam)))))

def binom(rnd, n, p):
    if n < 200:
        return sum(1 for _ in range(n) if rnd.random() < p)
    return poisson(rnd, n * p)

def month(rnd, per_hour, p, slo=0.999, minutes=30 * 1440, start=60):
    req, err = [0], [0]
    for _ in range(minutes):
        n = poisson(rnd, per_hour / 60)
        req.append(req[-1] + n); err.append(err[-1] + binom(rnd, n, p))
    budget = 1 - slo
    def br(t, w):
        a = max(0, t - w)
        n = req[t] - req[a]
        return None if n == 0 else (err[t] - err[a]) / n / budget
    fires = {"fast": 0, "slow": 0}; state = {"fast": False, "slow": False}; firing_min = {"fast": 0, "slow": 0}
    for t in range(start, minutes + 1):
        for name, (lw, sw, thr) in (("fast", (60, 5, 14.4)), ("slow", (360, 30, 6))):
            if t < lw: continue
            bl, bs = br(t, lw), br(t, sw)
            on = bl is not None and bs is not None and bl > thr and bs > thr
            if on and not state[name]: fires[name] += 1
            if on: firing_min[name] += 1
            state[name] = on
    return fires, firing_min, err[-1], req[-1]

if __name__ == "__main__":
    reps = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    p = float(sys.argv[2]) if len(sys.argv) > 2 else 0.001
    hours = float(sys.argv[3]) if len(sys.argv) > 3 else 720
    levels = [int(x) for x in sys.argv[4].split(",")] if len(sys.argv) > 4 else [10, 100, 1000, 10000]
    skip = float(sys.argv[5]) if len(sys.argv) > 5 else 1   # 앞 몇 시간은 세지 않는다(실습-2 는 6시간)
    print(f"진짜 에러율 {p*100:g}% (SLO 99.9% 기준 burn rate {p/0.001:g}), {hours:g}시간 x {reps}번 반복, 시드 1~{reps}"
          + ("" if hours == 720 else f"  (앞 {skip:g}시간을 빼고 센 횟수)"))
    print(f"{'시간당 요청':>10} {'빠른 단 발생':>14} {'느린 단 발생':>14} {'빠른 단 켜진 분':>16} {'SLI 범위':>20}")
    for per_hour in levels:
        tot = {"fast": 0, "slow": 0}; mins = {"fast": 0, "slow": 0}; slis = []
        for s in range(1, reps + 1):
            f, m, e, r = month(random.Random(s * 1000 + per_hour), per_hour, p, minutes=int(hours * 60), start=int(skip * 60))
            for k in tot: tot[k] += f[k]; mins[k] += m[k]
            slis.append(100 * (1 - e / r))
        print(f"{per_hour:>10} {tot['fast']/reps:>14.1f} {tot['slow']/reps:>14.1f} {mins['fast']/reps:>16.1f} {min(slis):>9.3f}~{max(slis):.3f}%")
