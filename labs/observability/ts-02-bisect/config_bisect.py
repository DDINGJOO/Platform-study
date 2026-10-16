#!/usr/bin/env python3
"""설정 키 64개를 반으로 나눠 기동 실패의 원인 키를 찾는다.

옛 설정(정상)과 새 설정(기동 실패)이 64개 키에서 다르다. 시험은 "옛 설정에 새 값 일부를 덮어
기동 검사를 돌린다" 이다. 기동 검사는 실제 서비스가 하듯 값의 범위와 키 사이의 관계를 본다.

경우 1  키 하나가 혼자 실패를 만든다(cache.ttl_seconds = -1)
경우 2  두 키가 함께 있어야 실패한다(풀 크기 x 레플리카 > DB 최대 연결 수)

  python3 config_bisect.py     -> out/config.txt
"""
import os, random, statistics

HERE = os.path.dirname(os.path.abspath(__file__))
REPLICAS = 4


def configs(case):
    """키 64개가 바뀐 옛/새 설정 쌍. 나머지는 실패와 무관하게 바뀐 키다."""
    old = {"cache.ttl_seconds": 300, "db.pool.max_size": 20, "db.max_connections": 200}
    new = dict(old)
    if case == 1:
        new["cache.ttl_seconds"] = -1                       # 혼자서 기동을 깨뜨린다
        neutral = 63
    else:
        new["db.pool.max_size"] = 50                        # 50 x 4 = 200 > 80
        new["db.max_connections"] = 80                      # 둘 중 하나만이면 통과
        neutral = 62
    for i in range(neutral):
        old[f"feature.k{i:02d}"] = i
        new[f"feature.k{i:02d}"] = i + 1
    return old, new


def boot_ok(cfg):
    """기동 검사. 실패하면 False."""
    if cfg["cache.ttl_seconds"] < 0:
        return False
    if cfg["db.pool.max_size"] * REPLICAS > cfg["db.max_connections"]:
        return False
    return True


class Tester:
    def __init__(self, old, new):
        self.old, self.new, self.calls = old, new, 0

    def fails(self, keys):
        """옛 설정에 keys 의 새 값만 덮어 기동해 본다. 실패하면 True."""
        self.calls += 1
        cfg = dict(self.old)
        for k in keys:
            cfg[k] = self.new[k]
        return not boot_ok(cfg)


def bisect(t, keys):
    """단순 반분. 두 절반이 모두 통과하면 그 자리에서 멈추고 남은 후보를 돌려준다."""
    cand = list(keys)
    while len(cand) > 1:
        half = cand[: len(cand) // 2]
        rest = cand[len(cand) // 2:]
        if t.fails(half):
            cand = half
        elif t.fails(rest):
            cand = rest
        else:
            return cand, "두 절반 모두 통과(원인이 갈라져 있다)"
    return cand, "하나로 좁힘"


def bisect_one_test(t, keys):
    """한 단계에 시험 한 번만 하는 반분(앞 절반만 시험하고, 통과하면 뒤 절반이라고 '가정'한다).
    git bisect 와 같은 방식이다. 상호작용이 있으면 틀린 답을 낸다."""
    cand = list(keys)
    while len(cand) > 1:
        half = cand[: len(cand) // 2]
        cand = half if t.fails(half) else cand[len(cand) // 2:]
    return cand


def ddmin(t, keys):
    """Zeller & Hildebrandt(2002) ddmin. 실패를 유지하는 최소 변경 집합을 찾는다."""
    c, n = list(keys), 2
    while len(c) >= 2:
        size = len(c) // n
        chunks = [c[i * size:(i + 1) * size] for i in range(n - 1)] + [c[(n - 1) * size:]]
        reduced = False
        for ch in chunks:                                   # 부분집합만으로 실패하나
            if t.fails(ch):
                c, n, reduced = ch, 2, True
                break
        if not reduced:
            for ch in chunks:                               # 여집합만으로 실패하나
                comp = [k for k in c if k not in ch]
                if t.fails(comp):
                    c, n, reduced = comp, max(n - 1, 2), True
                    break
        if not reduced:
            if n >= len(c):
                break
            n = min(len(c), n * 2)
    return c


def main():
    lines = []
    rnd = random.Random(3)
    old, new1 = configs(1)
    keys1 = [k for k in new1 if new1[k] != old[k]]
    steps = []
    for trial in range(100):
        order = keys1[:]; rnd.shuffle(order)
        t = Tester(old, new1)
        found, how = bisect(t, order)
        t2 = Tester(old, new1)
        found2 = bisect_one_test(t2, order)
        steps.append((t2.calls, t.calls, found2 == ["cache.ttl_seconds"]))
    lines.append(f"경우 1(키 {len(keys1)}개 중 하나가 원인), 순서를 바꿔 100회:")
    lines.append(f"  단계당 시험 1번(git bisect 방식): 시험 수 {sorted(set(s[0] for s in steps))}, 정답 {sum(s[2] for s in steps)}/100")
    lines.append(f"  단계당 양쪽을 다 시험: 시험 수 평균 {statistics.mean(s[1] for s in steps):.1f}")

    # 경우 2: pool x replicas > max_connections (둘이 함께 있어야 실패). ttl 은 정상 값
    old, new2 = configs(2)
    keys2 = [k for k in new2 if new2[k] != old[k]]
    t = Tester(old, new2)
    assert t.fails(keys2) and not t.fails([])
    res = {"split": 0, "same_half": 0, "one_test_wrong": 0, "one_test_right": 0}
    dd_calls, dd_ok, bis_calls = [], 0, []
    for trial in range(100):
        order = keys2[:]; rnd.shuffle(order)
        t = Tester(old, new2)
        found, how = bisect(t, order)
        bis_calls.append(t.calls)
        res["split" if how.startswith("두") else "same_half"] += 1
        t1 = Tester(old, new2)
        f1 = bisect_one_test(t1, order)
        res["one_test_right" if f1[0] in ("db.pool.max_size", "db.max_connections") else "one_test_wrong"] += 1
        t3 = Tester(old, new2)
        d = ddmin(t3, order)
        dd_calls.append(t3.calls)
        dd_ok += sorted(d) == ["db.max_connections", "db.pool.max_size"]
    lines.append(f"경우 2(키 {len(keys2)}개 중 두 키가 함께 있어야 실패), 순서를 바꿔 100회:")
    lines.append(f"  양쪽 시험 반분: 어느 단계에서 두 절반이 모두 통과해 멈춤 {res['split']}회 "
                 f"(시험 수 평균 {statistics.mean(bis_calls):.1f})")
    lines.append(f"  단계당 시험 1번(git bisect 방식): 찾은 키가 두 원인 중 하나 {res['one_test_right']}회, "
                 f"무관한 키 {res['one_test_wrong']}회")
    lines.append(f"  ddmin: 두 키를 정확히 찾음 {dd_ok}/100, 시험 수 평균 {statistics.mean(dd_calls):.1f}, "
                 f"최소 {min(dd_calls)}, 최대 {max(dd_calls)}")
    os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
    open(os.path.join(HERE, "out", "config.txt"), "w").write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
