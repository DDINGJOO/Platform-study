"""out/ 의 원자료를 요약해 results/summary.md 로 쓴다. 시각은 반영 시작 기준 상대 초로만 남긴다."""
import csv, glob, os, re, statistics as st
os.chdir(os.path.join(os.path.dirname(__file__), ".."))
os.makedirs("results", exist_ok=True)
L = []
kv = lambda s: dict(re.findall(r'(\w+)=(-?\d+)', s))

# e2, e2b: 동시 실행
for src, title in (("out/e2-concurrent.txt", "e2 같은 고객사를 동시에 두 번"), ("out/e2b-concurrent-diff.txt", "e2b 다른 고객사 둘(t1, t2)을 동시에")):
  if os.path.exists(src):
    L.append(f"## {title}\n")
    L.append("| 변형 | 시행 | 중복 행이 생긴 시행 | 중복 location 이 생긴 시행 | nginx 가 내려간 채 끝난 시행 | 경로 누락 시행 | 불일치 합 |")
    L.append("|---|---|---|---|---|---|---|")
    by = {}
    for line in open(src):
        v = re.search(r'variant="([^"]+)"', line).group(1)
        d = {k: int(x) for k, x in kv(line.split(" out=")[0]).items()}
        by.setdefault(v, []).append(d)
    for v, ds in by.items():
        L.append(f"| {v} | {len(ds)} | {sum(d['dup_rows']>0 for d in ds)} | {sum(d['dup_locations']>0 for d in ds)} | "
                 f"{sum(d['nginx_up']==0 for d in ds)} | {sum(d['missing_routes']>0 for d in ds)} | {sum(d['mismatch'] for d in ds)} |")
    L.append("")

def load_csv(p):
    return [(r["kind"], float(r["start"]), float(r["end"]), r["result"]) for r in csv.DictReader(open(p))]
def marks(p):
    m = {}
    for line in open(p):
        if "=" in line and line.split("=")[0] in ("apply_start", "apply_end", "rc", "stop_rc", "stop_timeout", "nginx_running"):
            k, v = line.strip().split("=", 1); m[k] = v
    return m
def stats(rows, a0):
    fails = [r for r in rows if r[3] != "200"]
    fast = [r for r in rows if r[0] == "fast"]; slow = [r for r in rows if r[0] == "slow"]
    ff = [r for r in fast if r[3] != "200"]; sf = [r for r in slow if r[3] != "200"]
    win = (max(r[2] for r in fails) - min(r[1] for r in fails)) if fails else 0.0
    kinds = {}
    for r in fails: kinds[r[3]] = kinds.get(r[3], 0) + 1
    first = (min(r[1] for r in fails) - a0) if fails else None
    return len(fast), len(ff), len(slow), len(sf), win, kinds, first

# e3: 부하 중 반영
L.append("## e3 부하(초당 100건 + 1초짜리 요청 4개 동시) 중 설정 반영\n")
L.append("| 변형 | 시행 | 빠른 요청 | 실패 | 1초 요청 | 실패 | 실패 구간(초) | 반영 소요(초) | 실패 종류 |")
L.append("|---|---|---|---|---|---|---|---|---|")
for v in ("naive", "idem"):
    for p in sorted(glob.glob(f"out/e3-{v}-*.csv")):
        i = p.split("-")[-1].split(".")[0]; m = marks(f"out/e3-{v}-{i}.marks")
        a0, a1 = float(m["apply_start"]), float(m["apply_end"])
        nf, ff, ns, sf, win, kinds, first = stats(load_csv(p), a0)
        L.append(f"| {v} | {i} | {nf} | {ff} | {ns} | {sf} | {win:.3f} | {a1-a0:.3f} | {kinds} |")
L.append("")
L.append("## e3b 틀린 설정(중복 location)을 반영할 때\n")
L.append("| 변형 | stop 종료 코드 | stop 대기 10초 초과 | 시작/reload 종료 코드 | 반영 뒤 nginx 프로세스 수 | 빠른 요청 | 실패 | 1초 요청 | 실패 | 첫 실패(반영 시작 기준 초) | 실패 구간(초) | 실패 종류 |")
L.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
for v in ("stopstart", "reload", "killstart"):
    p = f"out/e3b-{v}.csv"
    if not os.path.exists(p): continue
    m = marks(f"out/e3b-{v}.marks"); a0 = float(m["apply_start"])
    nf, ff, ns, sf, win, kinds, first = stats(load_csv(p), a0)
    L.append(f"| {v} | {m.get('stop_rc','-')} | {m.get('stop_timeout','0')} | {m.get('rc')} | {m.get('nginx_running')} | {nf} | {ff} | {ns} | {sf} | {first if first is None else round(first,3)} | {win:.3f} | {kinds} |")
L.append("")

if os.path.exists("out/e4-crash.txt"):
    L.append("## e4 중간에 끊고 다시 돌리기\n")
    L.append("| 변형 | 끊은 지점 | 끊긴 직후 불일치 | 다시 돌린 뒤 불일치 | 다시 돌린 결과 |")
    L.append("|---|---|---|---|---|")
    for line in open("out/e4-crash.txt"):
        v = re.search(r'variant="([^"]+)"', line).group(1); p = re.search(r'crash_at=(\S+)', line).group(1)
        k1 = re.search(r'after_crash: (.*?) rerun=', line).group(1); k2 = re.search(r'after_rerun: (.*)$', line).group(1)
        rr = re.search(r'rerun="([^"]*)"', line).group(1).strip("|")
        L.append(f"| {v} | {p} | {k1} | {k2} | {rr} |")
open("results/summary.md", "w").write("# 실습-1 요약 (scripts/summarize.py 가 out/ 에서 만든다)\n\n" + "\n".join(L) + "\n")
print("\n".join(L))
