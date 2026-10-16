#!/usr/bin/env python3
"""Loki 에 쌓인 로그를 꺼내 템플릿으로 묶고, 정상 구간과 장애 구간을 비교한다.

  .venv/bin/python analyze.py            (LOKI_URL 기본 http://localhost:35100)

1. Loki 에서 두 인스턴스의 로그를 전부 꺼낸다(query_range 를 5,000줄씩 넘겨 가며)
2. Drain3 로 템플릿을 뽑는다. 두 가지로: 기본 설정, 마스킹(UUID·IP·URL·숫자)을 건 설정
   - 장애 구간에만 나온 템플릿을 고르고, 같은 시각의 정상 인스턴스에도 없는지 한 번 더 거른다
   - 양쪽 구간에 다 있는 템플릿 중 고장 인스턴스 안에서 비중이 1.5배 넘게 바뀐 것을 고른다
3. 각 줄이 shop-src 의 어느 log 문장에서 왔는지(정답)를 형식 문자열로 맞춰, 템플릿이 문장과 1:1인지 본다
4. Loki pattern ingester 가 뽑은 패턴(/loki/api/v1/patterns)을 같은 기준으로 센다.
   표본은 10초 구간 단위라 구간 경계가 걸친 칸은 정상·장애 어느 쪽에도 넣지 않는다.
   어떤 패턴에도 들어가지 않은 줄을 문장별로 센다(질의 단계에서 30줄 미만 패턴이 잘린다)
5. 장애 구간에만 나온 템플릿마다 고정 문자열로 shop-src 를 검색해, 소스 위치 하나로 좁히기까지 몇 번 검색했는지 센다
6. 두 인스턴스 컨테이너의 환경변수와 설정 파일 diff 줄 수를 센다

스택이 떠 있을 때(앱 컨테이너가 끝 문장을 찍고 대기 중일 때) 돌린다. 6번이 컨테이너를 docker inspect 한다.

결과: out/analysis.txt(요약), out/drain-*.tsv, out/loki-patterns.tsv, out/loki-metrics.txt, out/search.tsv, out/env-diff.txt
(out/loki-metrics.txt 는 이 줄을 넣은 뒤 실행부터 생긴다. 글에 쓴 지표 값은 그 전 실행에서 손으로 본 값이다)
보조 계산(Loki 없이 tsv 만으로): offline.py -> out/offline.txt
"""
import collections, difflib, json, os, re, subprocess, sys, time, urllib.parse, urllib.request

from drain3 import TemplateMiner
from drain3.masking import MaskingInstruction
from drain3.template_miner_config import TemplateMinerConfig

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
SRC = os.path.join(HERE, "shop-src")
LOKI = os.environ.get("LOKI_URL", "http://localhost:35100")
INSTANCES = ["app-healthy", "app-broken"]
report = []


def say(s=""):
    print(s, flush=True)
    report.append(s)


def get(path, params):
    url = LOKI + path + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.load(r)


# ---------- 1. 로그 꺼내기 ----------
def fetch(instance, start_ns, end_ns):
    rows, cur = [], start_ns
    while True:
        d = get("/loki/api/v1/query_range", {"query": f'{{service_name="shop", instance="{instance}"}}',
                                               "start": cur, "end": end_ns, "limit": 5000, "direction": "forward"})
        batch = []
        for s in d["data"]["result"]:
            batch += [(int(ts), line) for ts, line in s["values"]]
        if not batch:
            break
        batch.sort()
        rows += batch
        if len(batch) < 5000:
            break
        cur = batch[-1][0] + 1
    return rows


def message(line):
    # "날짜 시각 레벨 pid --- [스레드] 로거 : 메시지" 에서 메시지만
    i = line.find(" : ")
    return line[i + 3:].rstrip("\n") if i >= 0 else line.rstrip("\n")


# ---------- 3. 정답(소스 문장) ----------
STMT = re.compile(r'log\.(info|warn|error|debug)\("((?:[^"\\]|\\.)*)"')


def source_statements():
    st = []
    for root, _, files in os.walk(SRC):
        for fn in sorted(files):
            if fn.endswith(".java"):
                p = os.path.join(root, fn)
                for i, line in enumerate(open(p), 1):
                    m = STMT.search(line)
                    if m:
                        fmt = m.group(2)
                        rx = re.compile("^" + "(.+?)".join(re.escape(x) for x in fmt.split("{}")) + "$")
                        st.append({"where": f"{os.path.relpath(p, HERE)}:{i}", "fmt": fmt, "rx": rx})
    return st


def truth_of(msg, stmts):
    for s in stmts:
        if s["rx"].match(msg):
            return s["where"]
    return "?"


# ---------- 2. Drain3 ----------
def miner(masked):
    cfg = TemplateMinerConfig()
    cfg.profiling_enabled = False
    if masked:
        cfg.masking_instructions = [
            MaskingInstruction(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", "UUID"),
            MaskingInstruction(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", "IP"),
            MaskingInstruction(r"https?://[^\s)]+", "URL"),
            MaskingInstruction(r"(?<![A-Za-z])-?\d+(\.\d+)?(?![A-Za-z])", "NUM"),
        ]
    return TemplateMiner(config=cfg)


def run_drain(lines, masked):
    tm = miner(masked)
    ids = []
    for _, _, msg, _ in lines:
        ids.append(tm.add_log_message(msg)["cluster_id"])
    clusters = {c.cluster_id: c.get_template() for c in tm.drain.clusters}
    return ids, clusters


def literal_chunks(template):
    parts = re.split(r"<\*>|<[A-Z]+>|<_>", template)
    return sorted((p.strip(" :,()=") for p in parts if len(p.strip(" :,()=")) >= 4), key=len, reverse=True)


def grep_hits(pattern, fixed=True):
    args = ["grep", "-rn", "-F" if fixed else "-E", "--include=*.java", pattern, SRC]
    out = subprocess.run(args, capture_output=True, text=True).stdout
    return [l.split(":")[0].replace(SRC + "/", "") + ":" + l.split(":")[1] for l in out.splitlines()]


def search_steps(example, template):
    """한 줄 원문 -> 가장 긴 고정 조각 -> 긴 조각 두 개를 이은 정규식 순으로 검색. 하나로 좁혀질 때까지 횟수."""
    tries = []
    hits = grep_hits(example)
    tries.append(("원문 한 줄", len(hits)))
    if len(hits) == 1:
        return tries, hits
    ch = literal_chunks(template)
    if ch:
        hits = grep_hits(ch[0])
        tries.append((f"고정 조각 '{ch[0]}'", len(hits)))
        if len(hits) == 1:
            return tries, hits
    if len(ch) >= 2:
        rx = re.escape(ch[0]) + ".*" + re.escape(ch[1]) if template.find(ch[0]) < template.find(ch[1]) \
            else re.escape(ch[1]) + ".*" + re.escape(ch[0])
        hits = grep_hits(rx, fixed=False)
        tries.append((f"조각 둘 '{ch[0]}' + '{ch[1]}'", len(hits)))
    return tries, hits


def main():
    os.makedirs(OUT, exist_ok=True)
    ph = {i: json.load(open(os.path.join(OUT, f"phase-{i}.json"))) for i in INSTANCES}
    t_start = min(p["start"] for p in ph.values()) - 5
    t_end = max(p["end"] for p in ph.values()) + 30
    boundary = ph["app-broken"]["boundary"]
    say(f"정상 구간 {ph['app-broken']['boundary'] - ph['app-broken']['start']:.0f}초, "
        f"장애 구간 {ph['app-broken']['end'] - ph['app-broken']['boundary']:.0f}초")

    stmts = source_statements()
    lines = []      # (ts_ns, instance, msg, window)
    for inst in INSTANCES:
        rows = fetch(inst, int(t_start * 1e9), int(t_end * 1e9))
        made = ph[inst].get("lines")
        say(f"{inst}: Loki 에서 꺼낸 줄 {len(rows):,} (생성기가 찍은 줄 {made:,})" if made else f"{inst}: {len(rows):,}")
        for ts, line in rows:
            lines.append((ts, inst, message(line), "incident" if ts / 1e9 >= boundary else "normal"))
    lines.sort()
    say(f"합계 {len(lines):,}줄")
    truth = [truth_of(m, stmts) for _, _, m, _ in lines]
    used = collections.Counter(truth)
    say(f"소스의 log 문장 {len(stmts)}개 중 실제로 찍힌 문장 {len([k for k in used if k != '?'])}개, 정답 못 맞춘 줄 {used.get('?', 0)}")

    # ---- Drain3 ----
    for masked in (False, True):
        name = "drain-masked" if masked else "drain-default"
        t0 = time.time()
        ids, clusters = run_drain(lines, masked)
        el = time.time() - t0
        by_c = collections.defaultdict(collections.Counter)      # cluster -> 정답 문장 분포
        by_t = collections.defaultdict(set)                      # 정답 문장 -> cluster 들
        win = collections.defaultdict(collections.Counter)       # cluster -> (window, instance) 수
        example = {}
        for (ts, inst, msg, w), cid, tr in zip(lines, ids, truth):
            by_c[cid][tr] += 1
            by_t[tr].add(cid)
            win[cid][(w, inst)] += 1
            example.setdefault(cid, msg)
        merged = sum(1 for c in by_c.values() if len(c) > 1)
        split = sum(1 for t, cs in by_t.items() if len(cs) > 1)
        say("")
        say(f"[{name}] 템플릿 {len(clusters)}개 ({el:.1f}초). 문장 둘 이상을 합친 템플릿 {merged}개, "
            f"템플릿 여러 개로 쪼개진 문장 {split}개")
        only_inc = [c for c in clusters if sum(v for (w, i), v in win[c].items() if w == "normal") == 0]
        # 시간 축만 보면 끝 무렵 한 번 찍힌 줄도 "장애 구간에만" 이 된다. 같은 시각의 정상 인스턴스에도 없어야 후보로 본다
        only_both = [c for c in only_inc if win[c][("incident", "app-healthy")] == 0]
        say(f"[{name}] 장애 구간에만 나온 템플릿 {len(only_inc)}개, 그중 같은 시각 정상 인스턴스에도 없는 것 {len(only_both)}개")
        # 양쪽 구간에 다 있지만 고장 인스턴스 안에서 비중이 크게 바뀐 템플릿.
        # 생성기는 초당 줄 수가 고정이라 새 템플릿이 끼면 나머지 비중이 고르게 줄어든다. 그래서 비중의 분모는
        # 정상 구간에도 있던 템플릿의 줄만으로 잡는다(새로 생긴 템플릿 몫을 빼고 본다)
        tot = collections.Counter()
        for c in clusters:
            if c in only_inc:
                continue
            for k, v in win[c].items():
                tot[k] += v
        def share(c, k):
            return win[c][k] / tot[k] if tot[k] else 0.0
        shifted = []
        for c in clusters:
            if c in only_inc:
                continue
            a, b = share(c, ("normal", "app-broken")), share(c, ("incident", "app-broken"))
            h = share(c, ("incident", "app-healthy"))
            if a > 0 and b > 0 and win[c][("normal", "app-broken")] >= 30 and (b / a >= 1.5 or b / a <= 1 / 1.5):
                shifted.append((c, a, b, h))
        say(f"[{name}] 양쪽 구간에 다 있고 고장 인스턴스 안에서 비중이 1.5배 넘게 바뀐 템플릿 {len(shifted)}개")
        for c, a, b, h in shifted:
            say(f"[{name}] 비중이 바뀐 템플릿: {clusters[c][:60]}  고장 인스턴스 정상 {a:.1%} -> 장애 {b:.1%} (같은 시각 정상 인스턴스 {h:.1%})")
        split_list = [t for t, cs in by_t.items() if len(cs) > 1]
        for t in split_list:
            say(f"[{name}] 쪼개진 문장 {t.replace('shop-src/src/main/java/lab/shop/', '')}: 템플릿 {len(by_t[t])}개")
        with open(os.path.join(OUT, f"{name}.tsv"), "w") as f:
            f.write("cluster\tnormal_healthy\tnormal_broken\tincident_healthy\tincident_broken\tsource\ttemplate\n")
            for c in sorted(clusters, key=lambda c: -sum(win[c].values())):
                src = ",".join(f"{k}x{v}" for k, v in by_c[c].most_common())
                f.write(f"{c}\t{win[c][('normal','app-healthy')]}\t{win[c][('normal','app-broken')]}\t"
                        f"{win[c][('incident','app-healthy')]}\t{win[c][('incident','app-broken')]}\t{src}\t{clusters[c]}\n")
        if masked:
            drain_only = [(c, clusters[c], example[c], c in only_both) for c in only_inc]

    # ---- 4. Loki patterns ----
    say("")
    pats = []
    STEP = 10
    for inst in INSTANCES:
        d = get("/loki/api/v1/patterns", {"query": f'{{service_name="shop", instance="{inst}"}}',
                                           "start": int(t_start * 1e9), "end": int(t_end * 1e9), "step": f"{STEP}s"})
        for p in d.get("data", []):
            # 표본 하나는 [t, t+STEP) 구간의 줄 수다. 경계가 걸친 구간은 어느 쪽에도 넣지 않고 따로 센다
            n_norm = sum(int(v) for t, v in p["samples"] if t + STEP <= boundary)
            n_inc = sum(int(v) for t, v in p["samples"] if t >= boundary)
            n_edge = sum(int(v) for t, v in p["samples"] if t < boundary < t + STEP)
            pats.append((inst, p["pattern"], n_norm, n_inc, n_edge))
    with open(os.path.join(OUT, "loki-patterns.tsv"), "w") as f:
        f.write("instance\tnormal\tboundary_bucket\tincident\tpattern\n")
        for inst, pat, a, b, e in pats:
            f.write(f"{inst}\t{a}\t{e}\t{b}\t{pat}\n")
    for inst in INSTANCES:
        mine = [p for p in pats if p[0] == inst]
        say(f"[loki] {inst}: 패턴 {len(mine)}개, 표본 합계 {sum(a + b + e for _, _, a, b, e in mine):,}, "
            f"장애 구간에만 나온 패턴 {sum(1 for p in mine if p[2] == 0 and p[3] > 0)}개")
    # 패턴은 헤더까지 포함한 줄 전체에서 뽑힌다. " : " 뒤(메시지)만 떼어 <_> 를 와일드카드로 바꿔 각 줄에 맞춘다
    pat_rx = collections.defaultdict(list)
    for inst, pat, a, b, e in pats:
        body = pat.split(" : ", 1)[1] if " : " in pat else pat
        pat_rx[inst].append((pat, re.compile("^" + ".*?".join(re.escape(x) for x in body.split("<_>")) + "$")))
    cover = collections.defaultdict(set)          # 패턴 -> 맞는 정답 문장들
    stmt_pats = collections.defaultdict(set)      # 정답 문장 -> 맞는 패턴들
    uncovered = collections.Counter()             # 정답 문장 -> 어떤 패턴에도 안 맞은 줄 수
    for (ts, inst, msg, w), tr in zip(lines, truth):
        hit = False
        for pat, rx in pat_rx[inst]:
            if rx.match(msg):
                cover[(inst, pat)].add(tr)
                stmt_pats[tr].add((inst, pat))
                hit = True
        if not hit:
            uncovered[tr] += 1
    merged_l = sum(1 for k, v in cover.items() if len(v) > 1)
    say(f"[loki] (한 줄이 일반 패턴과 특수 패턴에 함께 맞을 수 있다. 예: 'State Index <_> - <_>' 와 'State Index <_> - Utah')")
    say(f"[loki] 정답 문장 둘 이상에 맞는 패턴 {merged_l}개, 어떤 줄에도 맞지 않는 패턴 "
        f"{sum(1 for inst, pat, a, b, e in pats if not cover[(inst, pat)])}개")
    say(f"[loki] 어떤 패턴에도 안 들어간 줄 {sum(uncovered.values()):,}")
    for tr, n in uncovered.most_common():
        say(f"[loki]   {tr.replace('shop-src/src/main/java/lab/shop/', '')}: {n}줄, 이 문장에 맞는 패턴 {len(stmt_pats[tr])}개")
    for tr in sorted(stmt_pats, key=lambda t: -len(stmt_pats[t])):
        per = collections.Counter(i for i, _ in stmt_pats[tr])
        if per and max(per.values()) > 1:
            say(f"[loki] 쪼개진 문장 {tr.replace('shop-src/src/main/java/lab/shop/', '')}: "
                + ", ".join(f"{i} 패턴 {n}개" for i, n in sorted(per.items())))

    # pattern ingester 지표(학습한 줄, 버린 줄, 질의에서 잘린 패턴 수). 누적값이라 이 스크립트 밖의 질의도 들어간다
    try:
        with urllib.request.urlopen(LOKI + "/metrics", timeout=30) as r:
            m = [l for l in r.read().decode().splitlines()
                 if l.startswith(("loki_pattern_ingester_tokens_per_line_count", "loki_pattern_ingester_patterns_dropped_total",
                                  "loki_pattern_ingester_query_pruned_total", "loki_pattern_ingester_query_retained_total",
                                  "loki_pattern_ingester_patterns_detected_total"))]
        open(os.path.join(OUT, "loki-metrics.txt"), "w").write("\n".join(m) + "\n")
    except OSError as e:
        say(f"[loki] /metrics 를 못 읽었다: {e}")

    # ---- 5. 소스 검색 ----
    say("")
    with open(os.path.join(OUT, "search.tsv"), "w") as f:
        f.write("template\thealthy_also_absent\tsteps\ttries\tfound\n")
        total = total_both = 0
        for c, tpl, ex, both in drain_only:
            tries, hits = search_steps(ex, tpl)
            n = len(tries)
            total += n
            total_both += n if both else 0
            ok = len(hits) == 1
            f.write(f"{tpl}\t{both}\t{n}\t{' | '.join(f'{a}={b}건' for a, b in tries)}\t{hits[0] if ok else ','.join(hits)}\n")
            say(f"[search] {tpl[:70]}{'' if both else '   (정상 인스턴스에도 같은 시각에 있음)'}")
            say(f"         {' -> '.join(f'{a} {b}건' for a, b in tries)}  => {hits[0] if ok else hits}")
        say(f"[search] 장애 구간에만 나온 템플릿 {len(drain_only)}개, 검색 합계 {total}번 "
            f"(정상 인스턴스에도 없는 {sum(1 for x in drain_only if x[3])}개만 세면 {total_both}번)")

    # ---- 6. env / 설정 diff ----
    say("")
    envs = {}
    for inst in INSTANCES:
        cid = subprocess.run(["docker", "compose", "ps", "-q", inst], cwd=HERE, capture_output=True, text=True).stdout.strip()
        envs[inst] = sorted(json.loads(subprocess.run(["docker", "inspect", cid], capture_output=True, text=True).stdout)[0]["Config"]["Env"])
    d_env = [l for l in difflib.unified_diff(envs["app-healthy"], envs["app-broken"], "app-healthy", "app-broken", lineterm="", n=0)
             if l[:1] in "+-" and not l.startswith(("+++", "---"))]
    cfg_h = open(os.path.join(HERE, "config/healthy.yaml")).read().splitlines()
    cfg_b = open(os.path.join(HERE, "config/broken.yaml")).read().splitlines()
    d_cfg = [l for l in difflib.unified_diff(cfg_h, cfg_b, lineterm="", n=0) if l[:1] in "+-" and not l.startswith(("+++", "---"))]
    with open(os.path.join(OUT, "env-diff.txt"), "w") as f:
        f.write(f"# 환경변수 {len(envs['app-healthy'])}개 / {len(envs['app-broken'])}개\n")
        f.write("\n".join(d_env) + "\n\n# config/healthy.yaml vs config/broken.yaml\n" + "\n".join(d_cfg) + "\n")
    say(f"[diff] 환경변수 {len(envs['app-healthy'])}개 중 다른 줄 {len(d_env)}줄(+/- 합계), 설정 파일 다른 줄 {len(d_cfg)}줄")

    open(os.path.join(OUT, "analysis.txt"), "w").write("\n".join(report) + "\n")


if __name__ == "__main__":
    main()
