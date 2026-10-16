#!/usr/bin/env python3
"""합성 저장소를 만든다. 커밋 N개, 그중 몇 개가 회귀(테스트를 깨뜨리는 변경)다.

git fast-import 로 한 번에 써서 커밋 1,024개도 1초 안팎에 만든다.
커밋마다 src/mod_XX.py 중 하나에 줄을 하나 덧붙이고(평범한 변경),
지정한 커밋에서만 src/pricing.py 의 값을 바꾼다(회귀).

  python3 make_repo.py <디렉터리> [--n 1024] [--event 613:rounding=floor ...]
                       [--broken 10,11,12] [--broken-random 0.3 --seed 1]

--event  커밋번호:키=값. pricing.py 의 키를 그 커밋에서 바꾼다.
         rounding=floor   반올림 대신 내림(금액이 1원 틀어진다)
         rounding=half_up 원래대로(고친 커밋)
         discount=5       할인율 기본값을 바꾼다
--broken 이 커밋들에서는 src/BUILD 가 broken 이 된다(다음 커밋에서 ok 로 돌아온다).
         빌드가 깨져 시험할 수 없는 커밋을 흉내 낸다.
"""
import argparse, os, random, subprocess, sys

PRICING = '''# 주문 금액 계산
ROUNDING = "{rounding}"


def amount(unit_price, qty):
    gross = unit_price * qty * (100 - DISCOUNT_PCT) / 100 * 1.1   # 부가세 10%
    if ROUNDING == "floor":
        return int(gross)
    return int(gross + 0.5)


# 기본 할인율(%)
DISCOUNT_PCT = {discount}
'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("--n", type=int, default=1024)
    ap.add_argument("--event", action="append", default=[])
    ap.add_argument("--broken", default="")
    ap.add_argument("--broken-random", type=float, default=0.0)
    ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args()

    events = {}
    for e in a.event:
        c, kv = e.split(":", 1)
        k, v = kv.split("=", 1)
        events.setdefault(int(c), []).append((k, v))
    broken = set(int(x) for x in a.broken.split(",") if x)
    if a.broken_random > 0:
        rnd = random.Random(a.seed)
        # 양 끝(0번 정상, 마지막 HEAD)은 시험할 수 있어야 하니 빼고 고른다
        broken |= {i for i in range(1, a.n - 1) if rnd.random() < a.broken_random}

    os.makedirs(a.dir, exist_ok=False)
    subprocess.run(["git", "init", "-q", "-b", "main", a.dir], check=True)
    fi = subprocess.Popen(["git", "-C", a.dir, "fast-import", "--quiet"], stdin=subprocess.PIPE)
    w = fi.stdin.write

    def blob(data):
        b = data.encode()
        w(b"data %d\n" % len(b)); w(b); w(b"\n")

    state = {"rounding": "half_up", "discount": "0"}
    mods = {i: "" for i in range(40)}
    ts = 1_700_000_000
    for c in range(a.n):
        for k, v in events.get(c, []):
            state[k] = v
        m = c % 40
        mods[m] += f"x_{c} = {c}\n"
        msg = f"c{c:04d}"
        if c in events:
            msg += " " + ",".join(f"{k}={v}" for k, v in events[c])
        w(b"commit refs/heads/main\n")
        w(b"mark :%d\n" % (c + 1))
        w(b"author lab <> %d +0000\n" % (ts + c * 60))
        w(b"committer lab <> %d +0000\n" % (ts + c * 60))
        blob(msg)
        if c > 0:
            w(b"from :%d\n" % c)
        w(b"M 100644 inline src/pricing.py\n"); blob(PRICING.format(**state))
        w(b"M 100644 inline src/COMMIT_NO\n"); blob(f"{c}\n")
        w(b"M 100644 inline src/BUILD\n"); blob("broken\n" if c in broken else "ok\n")
        w(b"M 100644 inline src/mod_%02d.py\n" % m); blob(mods[m])
    fi.stdin.close()
    if fi.wait() != 0:
        sys.exit("fast-import failed")
    subprocess.run(["git", "-C", a.dir, "checkout", "-q", "main"], check=True)
    print(f"{a.dir}: {a.n} commits, events={sorted(events)}, broken={len(broken)}")


if __name__ == "__main__":
    main()
