#!/usr/bin/env python3
"""analyze.py 가 남긴 out/drain-*.tsv 만으로 다시 세는 보조 계산. Loki·Docker 가 필요 없다.

  .venv/bin/python offline.py

1. 캐시 미스 템플릿의 비중을 (구간 x 인스턴스) 네 칸 모두 같은 분모로 낸다
   (분모: 정상 구간에도 있던 템플릿의 줄. analyze.py 의 "비중이 바뀐 템플릿" 과 같은 분모)
2. 분모를 고치기 전 방식(전체 줄을 분모로)으로 1.5배 기준에 걸리는 템플릿 수
3. 장애 구간에만 있고 같은 시각 정상 인스턴스에도 없는 템플릿으로 소스를 검색하는 일을
   기본 설정 템플릿과 마스킹 설정 템플릿 양쪽으로 해서 비교한다(검색 순서는 analyze.py 와 같다.
   첫 단계 "원문 한 줄" 은 실제 값이 들어 있어 늘 0건이므로 1번으로 세고 넘어간다)

결과: out/offline.txt
"""
import csv, importlib.util, os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
spec = importlib.util.spec_from_file_location("analyze", os.path.join(HERE, "analyze.py"))
analyze = importlib.util.module_from_spec(spec)
spec.loader.exec_module(analyze)
KEYS = ["normal_healthy", "normal_broken", "incident_healthy", "incident_broken"]
lines = []


def say(s=""):
    print(s)
    lines.append(s)


def load(name):
    return list(csv.DictReader(open(os.path.join(OUT, f"{name}.tsv")), delimiter="\t"))


rows = load("drain-default")
new = [r for r in rows if int(r["normal_healthy"]) + int(r["normal_broken"]) == 0]
old = [r for r in rows if r not in new]

# 1
cm = [r for r in rows if r["template"].startswith("Cache miss")][0]
say("[share] 캐시 미스 템플릿 비중 (분모: 정상 구간에도 있던 템플릿의 줄)")
for k in KEYS:
    tot = sum(int(r[k]) for r in old)
    say(f"[share]   {k:<17} {int(cm[k]):>5} / {tot:>6} = {int(cm[k]) / tot:.1%}")

# 2
tot_all = {k: sum(int(r[k]) for r in rows) for k in KEYS}
cand = shifted = 0
for r in old:
    a = int(r["normal_broken"]) / tot_all["normal_broken"]
    b = int(r["incident_broken"]) / tot_all["incident_broken"]
    if int(r["normal_broken"]) >= 30 and a > 0 and b > 0:
        cand += 1
        shifted += (b / a >= 1.5 or b / a <= 1 / 1.5)
say(f"[share] 전체 줄을 분모로 하면 1.5배 기준에 걸리는 템플릿 {shifted}개 / 대상 {cand}개")

# 3
say("")
for name in ("drain-default", "drain-masked"):
    total = found = 0
    for r in load(name):
        if int(r["normal_healthy"]) + int(r["normal_broken"]) + int(r["incident_healthy"]) > 0:
            continue
        tries = [("원문 한 줄", 0)]
        hits = []
        ch = analyze.literal_chunks(r["template"])
        if ch:
            hits = analyze.grep_hits(ch[0])
            tries.append((f"고정 조각 '{ch[0]}'", len(hits)))
        if len(hits) != 1 and len(ch) >= 2:
            t = r["template"]
            rx = (analyze.re.escape(ch[0]) + ".*" + analyze.re.escape(ch[1])) if t.find(ch[0]) < t.find(ch[1]) \
                else (analyze.re.escape(ch[1]) + ".*" + analyze.re.escape(ch[0]))
            hits = analyze.grep_hits(rx, fixed=False)
            tries.append(("조각 둘", len(hits)))
        total += len(tries)
        found += len(hits) == 1
        say(f"[search:{name}] {r['template'][:72]}")
        say(f"[search:{name}]   {' -> '.join(f'{a} {b}건' for a, b in tries)}  => {hits[0] if len(hits) == 1 else '못 찾음'}")
    say(f"[search:{name}] 검색 {total}번, 한 곳으로 좁힌 템플릿 {found}개")
    say("")

open(os.path.join(OUT, "offline.txt"), "w").write("\n".join(lines) + "\n")
