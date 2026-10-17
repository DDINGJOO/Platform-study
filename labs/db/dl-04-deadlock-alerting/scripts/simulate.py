"""카운터 시계열을 만들어 규칙 R1~R4 를 돌린다(MySQL 없이). 1분 해상도, 포아송 도착, seed 고정.

시나리오
  S1 수정 전후: 2일 시간당 8건 → 28일 시간당 0.3건
  S2 정상 0.3건 → 회귀: 3일 0.3건 → 4일 2건 (새 패턴이 생긴 경우)
  S3 버스트: 3일 0.3건 → 30분 동안 분당 1건(배포 직후 핫스팟) → 3일 0.3건
  rate 표: 7일 동안 고정 비율 r 건/시간
"""
import math, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rules import RULES, increments, episodes, first_true

SEEDS = range(1, 21)


def poisson(rnd, lam):
    l, k, p = math.exp(-lam), 0, 1.0
    while True:
        p *= rnd.random()
        if p <= l:
            return k
        k += 1


def series(rnd, rates_per_min):
    c, out = 0, []
    for lam in rates_per_min:
        c += poisson(rnd, lam)
        out.append(c)
    return out


def rate_seg(per_hour, minutes):
    return [per_hour / 60.0] * minutes


DAY = 1440


def first_rise(states, times, after):
    """after 이후 처음 꺼짐→켜짐 전이가 난 시각. 이미 켜져 있던 상태가 이어지는 건 새 알람이 아니다."""
    prev = False
    for s, t in zip(states, times):
        if t >= after and s and not prev:
            return t
        prev = s
    return None


def run(label, build, change_at=None):
    tot = {name: [] for name, _ in RULES}
    det = {name: [] for name, _ in RULES}
    onr = {name: [] for name, _ in RULES}
    dead = []
    for s in SEEDS:
        rnd = random.Random(s)
        rates = build()
        cnt = series(rnd, rates)
        inc = increments(cnt)
        if change_at is None:
            dead.append(sum(inc))
        else:
            dead.append((sum(inc[:change_at]), sum(inc[change_at:])))
        for name, fn in RULES:
            times, states = fn(inc)
            if change_at is None:
                tot[name].append(episodes(states))
                onr[name].append(sum(states) / float(len(states)))
            else:
                pre = [x for t, x in zip(times, states) if t < change_at]
                post = [x for t, x in zip(times, states) if t >= change_at]
                tot[name].append((episodes(pre), episodes([pre[-1] if pre else False] + post) - (1 if pre and pre[-1] else 0)))
                onr[name].append(sum(post) / float(len(post)))
                ft = first_rise(states, times, change_at)
                det[name].append(None if ft is None else ft - change_at)
    return dead, tot, det, onr


def avg(xs):
    return sum(xs) / len(xs)


def fmt_det(ds):
    hit = [d for d in ds if d is not None]
    if not hit:
        return "못 잡음(0/%d)" % len(ds)
    hit.sort()
    med = hit[len(hit) // 2]
    return "%d/%d, 중앙 %s" % (len(hit), len(ds), ("%d분" % med) if med < 120 else ("%.1f시간" % (med / 60.0)))


def main():
    print("seed %d개 평균. 알람 수는 꺼짐→켜짐 전이 수.\n" % len(SEEDS))
    print("== 고정 비율 7일")
    print("칸 = 알람 수 (켜져 있던 시간 비율)")
    print("%-8s %8s" % ("건/시간", "교착 수") + "".join("  %-16s" % n.split(" ")[0] for n, _ in RULES))
    for r in [0.1, 0.3, 1, 2, 4, 8, 20]:
        dead, tot, _, onr = run("rate", lambda r=r: rate_seg(r, 7 * DAY))
        print("%-8s %8.1f" % (r, avg(dead)) + "".join("  %-16s" % ("%.1f (%.0f%%)" % (avg(tot[n]), 100 * avg(onr[n]))) for n, _ in RULES))

    for label, build, at in [
        ("S1 수정 전후: 2일 8건/시간 → 28일 0.3건/시간", lambda: rate_seg(8, 2 * DAY) + rate_seg(0.3, 28 * DAY), 2 * DAY),
        ("S2 회귀: 3일 0.3건/시간 → 4일 2건/시간", lambda: rate_seg(0.3, 3 * DAY) + rate_seg(2, 4 * DAY), 3 * DAY),
        ("S3 버스트: 3일 0.3건 → 30분 분당 1건 → 3일 0.3건", lambda: rate_seg(0.3, 3 * DAY) + [1.0] * 30 + rate_seg(0.3, 3 * DAY), 3 * DAY),
    ]:
        dead, tot, det, onr = run(label, build, at)
        print("\n== " + label)
        print("교착 수 평균: 전 %.1f  후 %.1f" % (avg([d[0] for d in dead]), avg([d[1] for d in dead])))
        print("%-44s %7s %7s %9s   %s" % ("규칙", "전 알람", "후 알람", "후 켜짐%", "변화 뒤 새 알람(seed 수, 중앙 지연)"))
        for n, _ in RULES:
            print("%-44s %7.1f %7.1f %8.0f%%   %s" % (n, avg([x[0] for x in tot[n]]), avg([x[1] for x in tot[n]]), 100 * avg(onr[n]), fmt_det(det[n])))


if __name__ == "__main__":
    main()
