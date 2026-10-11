"""Kayenta NetflixACAJudge 의 지표 분류 부분을 파이썬으로 옮긴 것.

원본(spinnaker/kayenta, master 5310ab7):
  kayenta-mannwhitney/.../MannWhitney.scala          검정, 신뢰구간, Hodges-Lehmann 추정치
  kayenta-judge/.../MannWhitneyClassifier.scala      Pass / High / Low 분류
  kayenta-judge/.../NetflixACAJudge.scala            tolerance=0.25, confLevel=0.98 고정
  kayenta-judge/.../scorers/WeightedSumScorer.scala  그룹 점수, critical, Nodata 50%

표준 라이브러리만 쓴다. 근 찾기는 Kayenta 의 BrentSolver.java(R uniroot 와 같은 zeroin)를 그대로 옮겼다.
"""
from __future__ import annotations

import math
import random
from statistics import NormalDist, mean


def _rank(values):
    """NaturalRanking(NaNStrategy.MAXIMAL, TiesStrategy.AVERAGE) 와 같은 평균 순위."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        r = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[order[k]] = r
        i = j + 1
    return ranks


def wilcoxon_diff(mu, quantile, x, y):
    nx, ny = float(len(x)), float(len(y))
    dr = _rank([v - mu for v in x] + list(y))
    ties = {}
    for r in dr:
        ties[r] = ties.get(r, 0) + 1
    dz = sum(dr[: len(x)]) - nx * (nx + 1) / 2 - nx * ny / 2
    correction = (0.0 if dz == 0 else math.copysign(1.0, dz)) * 0.5
    tie_term = sum(v ** 3 - v for v in ties.values()) / ((nx + ny) * (nx + ny - 1))
    sigma = math.sqrt((nx * ny / 12) * ((nx + ny + 1) - tie_term))
    if sigma == 0:
        raise ValueError("cannot compute confidence interval when all observations are tied")
    return (dz - correction) / sigma - quantile


def _solve(ax, bx, fa, fb, func):
    """BrentSolver.java 를 그대로 옮겼다(R 의 zeroin, TOLERANCE 1e-4, 최대 1000회)."""
    eps, tol = 2.220446049250313e-16, 1e-4
    a, b, c, fc = ax, bx, ax, fa
    if fa == 0:
        return a
    if fb == 0:
        return b
    for _ in range(1001):
        prev_step = b - a
        if abs(fc) < abs(fb):
            a, b, c = b, c, b
            fa, fb, fc = fb, fc, fb
        tol_act = 2 * eps * abs(b) + tol / 2
        new_step = (c - b) / 2
        if abs(new_step) <= tol_act or fb == 0:
            return b
        if abs(prev_step) >= tol_act and abs(fa) > abs(fb):
            cb = c - b
            if a == c:
                t1 = fb / fa
                p = cb * t1
                q = 1.0 - t1
            else:
                q = fa / fc
                t1 = fb / fc
                t2 = fb / fa
                p = t2 * (cb * q * (q - t1) - (b - a) * (t1 - 1.0))
                q = (q - 1.0) * (t1 - 1.0) * (t2 - 1.0)
            if p > 0.0:
                q = -q
            else:
                p = -p
            if p < (0.75 * cb * q - abs(tol_act * q) / 2) and p < abs(prev_step * q / 2):
                new_step = p / q
        if abs(new_step) < tol_act:
            new_step = tol_act if new_step > 0 else -tol_act
        a, fa = b, fb
        b += new_step
        fb = func(b)
        if (fb > 0 and fc > 0) or (fb < 0 and fc < 0):
            c, fc = a, fa
    return b


def mann_whitney_u_test(x, y, confidence_level=0.95):
    """x = experiment(카나리), y = control(베이스라인). (신뢰구간 하한, 상한, 추정치) 반환."""
    alpha = 1.0 - confidence_level
    mu_min = min(x) - max(y)
    mu_max = max(x) - min(y)

    def root(zq):
        flo = wilcoxon_diff(mu_min, zq, x, y)
        fhi = wilcoxon_diff(mu_max, zq, x, y)
        if flo <= 0:
            return mu_min
        if fhi >= 0:
            return mu_max
        return _solve(mu_min, mu_max, flo, fhi, lambda m: wilcoxon_diff(m, zq, x, y))

    zq = NormalDist().inv_cdf(alpha / 2)
    ci = (root(-zq), root(zq))
    flo = wilcoxon_diff(mu_min, 0, x, y)
    fhi = wilcoxon_diff(mu_max, 0, x, y)
    est = _solve(mu_min, mu_max, flo, fhi, lambda m: wilcoxon_diff(m, 0, x, y))
    return ci[0], ci[1], est


def mean_ratio(control, experiment):
    c, e = mean(control), mean(experiment)
    return float("nan") if c == 0 or e == 0 else e / c


def classify(control, experiment, direction="either", tolerance=0.25, confidence_level=0.98,
             allowed_increase=1.0, allowed_decrease=1.0, critical=False, rng=None):
    """MannWhitneyClassifier.classify 의 nanStrategy=remove 경로.

    반환: dict(classification, reason, lower, upper, estimate, bound, ratio, n_control, n_experiment)
    """
    control = [v for v in control if not math.isnan(v)]
    experiment = [v for v in experiment if not math.isnan(v)]
    out = {"n_control": len(control), "n_experiment": len(experiment)}
    if not control or not experiment:
        return {**out, "classification": "Nodata", "reason": "missing data", "critical": critical}
    if sorted(control) == sorted(experiment):
        return {**out, "classification": "Pass", "reason": "identical", "critical": False}
    if len(set(control) | set(experiment)) == 1:
        return {**out, "classification": "Pass", "reason": "single value", "critical": False}

    x, y = experiment, control
    if len(set(x)) == 1 and len(set(y)) == 1:
        # 원본: 두 쪽 모두 값이 하나뿐이면 값의 1e-5 배 표준편차로 가우스 잡음을 섞는다
        rng = rng or random.Random(0)
        x = [v + rng.gauss(0, x[0] * 1e-5) for v in x]
        y = [v + rng.gauss(0, y[0] * 1e-5) for v in y]

    lower, upper, est = mann_whitney_u_test(x, y, confidence_level)
    bound = tolerance * abs(est)
    ratio = mean_ratio(y, x)
    effect_ok_high = math.isnan(ratio) or ratio >= allowed_increase
    effect_ok_low = math.isnan(ratio) or ratio <= allowed_decrease
    label = "Pass"
    if direction in ("increase", "either") and lower > bound and effect_ok_high:
        label = "High"
    elif direction in ("decrease", "either") and upper < -bound and effect_ok_low:
        label = "Low"
    return {**out, "classification": label, "lower": lower, "upper": upper, "estimate": est,
            "bound": bound, "ratio": ratio, "critical": critical and label in ("High", "Low")}


def score(results, group_weights=None):
    """WeightedSumScorer.score. results: [{name, group, classification, critical}]"""
    group_weights = group_weights or {}
    crit = [r for r in results if r.get("critical") and r["classification"] != "Pass"]
    if crit:
        return 0.0, f"Canary Failed: {crit[0]['name']} critical {crit[0]['classification']}"
    nodata = sum(1 for r in results if r["classification"] == "Nodata")
    if results and nodata / len(results) * 100 >= 50:
        return 0.0, "Canary Failed: 50% or more metrics returned NODATA"
    groups = {}
    for r in results:
        groups.setdefault(r.get("group", "default"), []).append(r["classification"])
    unweighted = [g for g in groups if g not in group_weights]
    calc = (100 - sum(group_weights.values())) / len(unweighted) if unweighted else 0.0
    total = 0.0
    for g, labels in groups.items():
        counted = [l for l in labels if l in ("Pass", "High", "Low", "NodataFailMetric")]
        s = 100.0 if not counted else labels.count("Pass") / len(counted) * 100
        total += s * (group_weights.get(g, calc) / 100)
    return round(total, 2), None
