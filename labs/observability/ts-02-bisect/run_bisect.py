#!/usr/bin/env python3
"""시나리오별로 git bisect run 을 돌리고 단계 수와 찾은 커밋을 센다.

  python3 run_bisect.py all            # 전부(수 분)
  python3 run_bisect.py single|flaky|two|nonmono|skip|linear

결과: out/<시나리오>.tsv(실행마다 한 줄), out/summary.txt(요약). 저장소는 work/ 아래에 만든다.
"""
import os, random, re, shutil, statistics, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(HERE, "work")
OUT = os.path.join(HERE, "out")
CHECK = os.path.join(HERE, "check.py")
N = 1024


def sh(args, cwd, env=None, check=True):
    return subprocess.run(args, cwd=cwd, env=env, check=check, text=True,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT).stdout


def make(name, *opts):
    d = os.path.join(WORK, name)
    if os.path.exists(d):
        shutil.rmtree(d)
    os.makedirs(WORK, exist_ok=True)
    sh([sys.executable, os.path.join(HERE, "make_repo.py"), d, "--n", str(N), *opts], HERE)
    return d


def commit_map(repo):
    m = {}
    for line in sh(["git", "log", "--format=%H %s", "main"], repo).splitlines():
        h, s = line.split(" ", 1)
        m[h] = int(s[1:5])
    return m


def bisect(repo, env_extra=None, good=None):
    """git bisect run 한 번. (찾은 커밋 번호 목록, 판정 호출 수, skip 호출 수, 출력 마지막 줄들)"""
    log = os.path.join(WORK, "check.log")
    if os.path.exists(log):
        os.remove(log)
    env = dict(os.environ, CHECK_LOG=log, **(env_extra or {}))
    cmap = commit_map(repo)
    rev = {v: k for k, v in cmap.items()}
    good_sha = rev[good if good is not None else 0]
    sh(["git", "bisect", "reset"], repo, check=False)
    sh(["git", "bisect", "start", "main", good_sha], repo)
    out = sh(["git", "bisect", "run", sys.executable, CHECK], repo, env=env, check=False)
    sh(["git", "bisect", "reset"], repo, check=False)
    found = []
    m = re.search(r"^([0-9a-f]{40}) is the first bad commit", out, re.M)
    if m:
        found = [cmap[m.group(1)]]
    elif "only 'skip'ped commits left" in out:
        tail = out.split("could be any of:", 1)[1]
        found = sorted(cmap[h] for h in re.findall(r"^([0-9a-f]{40})", tail, re.M))
    lines = open(log).read().split("\n") if os.path.exists(log) else []
    verdicts = [l.split()[1] for l in lines if l]
    tested = sum(1 for v in verdicts if v != "skip")
    skipped = sum(1 for v in verdicts if v == "skip")
    return found, tested, skipped, out


def w(name, header, rows):
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, name + ".tsv"), "w") as f:
        f.write("\t".join(header) + "\n")
        for r in rows:
            f.write("\t".join(str(x) for x in r) + "\n")


summary = []


def say(s):
    print(s, flush=True)
    summary.append(s)


def single():
    """회귀 하나, 위치를 무작위로 100번 바꿔 단계 수를 센다. 선형 탐색 횟수는 위치에서 계산."""
    rnd = random.Random(42)
    rows = []
    for t in range(100):
        r = rnd.randint(1, N - 1)
        repo = make("single", "--event", f"{r}:rounding=floor")
        found, tested, skipped, _ = bisect(repo)
        rows.append((t, r, found[0] if found else "-", tested, r, N - r))
    w("single", ["trial", "regression", "found", "bisect_tests", "linear_fwd", "linear_back"], rows)
    steps = [x[3] for x in rows]
    ok = sum(1 for x in rows if x[2] == x[1])
    say(f"[single] 100회: 정답 {ok}/100, 단계 수 분포 " +
        ", ".join(f"{k}번 {steps.count(k)}회" for k in sorted(set(steps))) +
        f", 평균 {statistics.mean(steps):.2f}")
    say(f"[single] 선형 탐색(앞에서부터) 평균 {statistics.mean(x[4] for x in rows):.1f}번, "
        f"(뒤에서부터) 평균 {statistics.mean(x[5] for x in rows):.1f}번")


def flaky():
    repo = make("flaky", "--event", "613:rounding=floor")
    rows = []
    cases = [("sym", 0.05, "1"), ("sym", 0.20, "1"), ("good-only", 0.05, "1"), ("good-only", 0.20, "1"),
             ("sym", 0.05, "maj3"), ("sym", 0.20, "maj3"), ("good-only", 0.05, "all3"), ("good-only", 0.20, "all3")]
    for mode, p, vote in cases:
        wrong, tests, founds = 0, [], {}
        for t in range(100):
            found, tested, _, _ = bisect(repo, {"FLAKE_P": str(p), "FLAKE_MODE": mode, "VOTE": vote, "TRIAL": str(t)})
            f = found[0] if found else -1
            wrong += f != 613
            tests.append(tested * (1 if vote == "1" else 3))
            founds[f] = founds.get(f, 0) + 1
            rows.append((mode, p, vote, t, f, tested))
        near = sorted(founds.items(), key=lambda kv: -kv[1])[:3]
        say(f"[flaky] {mode:9s} p={p:.2f} vote={vote:4s}: 오답 {wrong}/100, 시험 실행 평균 {statistics.mean(tests):.1f}회, "
            f"자주 나온 답 {near}")
    w("flaky", ["mode", "p", "vote", "trial", "found", "bisect_steps"], rows)


def two():
    """같은 테스트를 깨뜨리는 회귀 둘(300 반올림, 700 할인율)."""
    repo = make("two", "--event", "300:rounding=floor", "--event", "700:discount=5")
    found, tested, _, _ = bisect(repo)
    say(f"[two] 1차 bisect: 찾은 커밋 {found}, 시험 {tested}번")
    # HEAD 에서 찾은 커밋을 되돌려 시험
    cmap = commit_map(repo); rev = {v: k for k, v in cmap.items()}
    # 찾은 커밋의 pricing.py 변경만 HEAD 에서 거꾸로 적용한다(커밋 전체 revert 는 COMMIT_NO 충돌이 난다)
    diff = sh(["git", "show", rev[found[0]], "--", "src/pricing.py"], repo)
    subprocess.run(["git", "apply", "-R"], cwd=repo, input=diff, text=True, check=True)
    r = subprocess.run([sys.executable, CHECK], cwd=repo, env=dict(os.environ))
    say(f"[two] HEAD 에서 커밋 {found[0]} 의 pricing.py 변경을 되돌린 뒤 시험 종료 코드: {r.returncode} (0이면 정상)")
    sh(["git", "checkout", "-q", "--", "."], repo)
    found2, tested2, _, _ = bisect(repo, {"APPLY_FIX": "rounding"})
    say(f"[two] 2차 bisect(반올림 수정을 적용한 채로): 찾은 커밋 {found2}, 시험 {tested2}번")


def nonmono():
    """고장(a) -> 우연히 고침(b) -> 다시 고장(c). 첫 가운데 지점이 어디에 떨어지느냐에 따라 무엇을 찾나."""
    rows = []
    for (x, y, z) in [(300, 500, 700), (300, 600, 700), (300, 400, 900), (100, 200, 300)]:
        repo = make("nonmono", "--event", f"{x}:rounding=floor", "--event", f"{y}:rounding=half_up",
                    "--event", f"{z}:rounding=floor")
        found, tested, _, _ = bisect(repo)
        rows.append(("fixed", x, y, z, found[0] if found else "-", tested))
        say(f"[nonmono] 고장 {x} -> 고침 {y} -> 다시 고장 {z}: 찾은 커밋 {found}, 시험 {tested}번")
    rnd = random.Random(7)
    first = last = other = 0
    for t in range(100):
        x, y, z = sorted(rnd.sample(range(1, N - 1), 3))
        repo = make("nonmono", "--event", f"{x}:rounding=floor", "--event", f"{y}:rounding=half_up",
                    "--event", f"{z}:rounding=floor")
        found, tested, _, _ = bisect(repo)
        f = found[0] if found else -1
        first += f == x; last += f == z; other += f not in (x, z)
        rows.append(("random", x, y, z, f, tested))
    say(f"[nonmono] 무작위 위치 100회: 처음 고장(a)을 찾음 {first}, 다시 고장(c)을 찾음 {last}, 그 밖 {other}")
    w("nonmono", ["kind", "broke", "fixed", "broke_again", "found", "tests"], rows)


def skip():
    rows = []
    for frac in [0.1, 0.3, 0.5]:
        exact, tests, skips, cands = 0, [], [], []
        for t in range(30):
            repo = make("skip", "--event", "613:rounding=floor", "--broken-random", str(frac), "--seed", str(t))
            found, tested, skipped, _ = bisect(repo)
            exact += found == [613]
            tests.append(tested); skips.append(skipped); cands.append(len(found))
            rows.append((frac, t, ",".join(map(str, found)), tested, skipped))
        say(f"[skip] 깨진 빌드 {int(frac*100)}%: 하나로 좁힘 {exact}/30, 판정 시험 평균 {statistics.mean(tests):.1f}, "
            f"skip 평균 {statistics.mean(skips):.1f}, 합계 평균 {statistics.mean(a+b for a,b in zip(tests,skips)):.1f}, "
            f"후보 수 최대 {max(cands)}")
    # 범인 바로 앞뒤로 빌드가 깨진 구간
    repo = make("skip", "--event", "613:rounding=floor", "--broken", ",".join(str(i) for i in range(605, 621)))
    found, tested, skipped, out = bisect(repo)
    rows.append(("605-620", 0, ",".join(map(str, found)), tested, skipped))
    say(f"[skip] 605~620 빌드 깨짐(범인 613 포함): 후보 {len(found)}개 {found[:3]}...{found[-2:]}, "
        f"판정 {tested}번, skip {skipped}번")
    with open(os.path.join(OUT, "skip-range-output.txt"), "w") as f:
        f.write(re.sub(r"[0-9a-f]{40}", lambda m: m.group(0)[:7], out))
    w("skip", ["broken_frac", "seed", "found", "tested", "skipped"], rows)


def linear():
    """선형 탐색을 실제로 한 번 돌려 계산과 맞는지 본다(앞에서부터, 613이 범인)."""
    repo = make("linear", "--event", "613:rounding=floor")
    cmap = commit_map(repo); rev = {v: k for k, v in cmap.items()}
    t0 = time.time(); n = 0
    for c in range(1, N):
        sh(["git", "checkout", "-q", rev[c]], repo)
        n += 1
        if subprocess.run([sys.executable, CHECK], cwd=repo).returncode == 1:
            break
    sh(["git", "checkout", "-q", "main"], repo)
    lt = time.time() - t0
    t0 = time.time(); found, tested, _, _ = bisect(repo); bt = time.time() - t0
    say(f"[linear] 앞에서부터 선형 탐색: c{c} 에서 첫 실패, 시험 {n}번, {lt:.1f}초 / 같은 저장소 bisect: {found}, 시험 {tested}번, {bt:.1f}초")


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    fns = {"single": single, "flaky": flaky, "two": two, "nonmono": nonmono, "skip": skip, "linear": linear}
    t0 = time.time()
    for k, fn in fns.items():
        if which in (k, "all"):
            fn()
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, f"summary-{which}.txt"), "w") as f:
        f.write("git " + sh(["git", "--version"], HERE).strip().split()[2] + f", python {sys.version.split()[0]}\n")
        f.write("\n".join(summary) + f"\n총 {time.time()-t0:.0f}초\n")
