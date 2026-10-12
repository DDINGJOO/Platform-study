#!/usr/bin/env python3
"""grep, FindMethods, JaCoCo 결과를 정답표에 맞춰 센다.

정답표는 소스의 꼬리 주석에서 읽는다.
  #S<n>  대상 호출(SLF4J Logger.info). 정탐이 되어야 하는 곳
  #G<n>  대상이 아닌데 글자가 비슷한 곳(주석, 문자열, 다른 타입의 info)
실습 디렉터리에서 python3 scripts/score.py
"""
import csv, glob, os, re, xml.etree.ElementTree as ET

SRC = "app/src/main/java/lab/co4"
RES = "results"


def ground_truth():
    sites = {}
    for path in sorted(glob.glob(f"{SRC}/*.java")):
        f = os.path.basename(path)
        for i, line in enumerate(open(path, encoding="utf-8"), 1):
            m = re.search(r"#([SG]\d+)\s*(.*)$", line)
            if m:
                sites[m.group(1)] = dict(file=f, line=i, desc=m.group(2).strip(), text=line.strip())
    return sites


def site_of(sites, f, line):
    """찾은 줄(line)이 어느 정답 줄에 해당하나. 여러 줄에 걸친 호출은 꼬리 주석이 마지막 줄에 있다."""
    for sid, s in sites.items():
        if s["file"] == f and s["line"] == line:
            return sid
    for sid, s in sites.items():
        if s["file"] == f and s["line"] - 2 <= line < s["line"]:
            return sid
    return None


def grep_hits(sites):
    hits = {}
    for row in open(f"{RES}/grep.txt", encoding="utf-8"):
        m = re.match(r"lab/co4/(\w+\.java):(\d+):", row)
        if m:
            sid = site_of(sites, m.group(1), int(m.group(2))) or f"?{m.group(1)}:{m.group(2)}"
            hits[sid] = hits.get(sid, 0) + 1
    return hits


def rewrite_hits(sites, name):
    """dryRun 패치에서 검색 표시(~~>)가 붙은 줄을 찾아 원래 소스의 줄 번호로 되돌린다."""
    path = f"{RES}/{name}/rewrite.patch"
    hits = {}
    if not os.path.exists(path):
        return hits, 0
    cur, newline = None, 0
    for row in open(path, encoding="utf-8"):
        if row.startswith("+++ "):
            cur = os.path.basename(row.split()[-1].strip())
        elif row.startswith("@@"):
            newline = int(re.search(r"\+(\d+)", row).group(1)) - 1
        elif row.startswith("-"):
            continue
        else:
            newline += 1
            if row.startswith("+") and "~~>" in row:
                sid = site_of(sites, cur, newline) or f"?{cur}:{newline}"
                hits[sid] = hits.get(sid, 0) + row.count("~~>")
    rows = 0
    for c in glob.glob(f"{RES}/{name}/*MethodCalls*.csv"):
        with open(c, encoding="utf-8") as fh:
            body = [r for r in csv.reader(fh) if r and not r[0].startswith("#")]
            rows += max(0, len(body) - 1)  # '#' 로 시작하는 설명 줄과 머리줄을 뺀다
    return hits, rows


def jacoco_hits(sites):
    path = f"{RES}/jacoco.xml"
    if not os.path.exists(path):
        return {}, {}
    root = ET.parse(path).getroot()
    lines = {}
    for sf in root.iter("sourcefile"):
        for ln in sf.iter("line"):
            lines[(sf.get("name"), int(ln.get("nr")))] = (int(ln.get("ci")), int(ln.get("mi")))
    ran, state = {}, {}
    for sid, s in sites.items():
        # 여러 줄 호출(S2)은 윗줄에 바이트코드가 붙을 수 있어 S 는 윗줄까지 본다. G 는 그 줄만
        ks = (0, 1) if sid.startswith("S") else (0,)
        cands = [lines.get((s["file"], s["line"] - k)) for k in ks]
        cands = [c for c in cands if c]
        if not cands:
            state[sid] = "코드 없음"
        elif any(ci > 0 for ci, _ in cands):
            ran[sid] = 1
            state[sid] = "실행됨"
        else:
            state[sid] = "실행 안 됨"
    return ran, state


def main():
    sites = ground_truth()
    g = grep_hits(sites)
    rd, rd_rows = rewrite_hits(sites, "rewrite-default")
    ro, ro_rows = rewrite_hits(sites, "rewrite-overrides")
    rn, rn_rows = rewrite_hits(sites, "rewrite-notypes")
    jr, js = jacoco_hits(sites)
    print(f"{'site':5s} {'grep':>4s} {'FM':>3s} {'FM+o':>4s} {'notype':>6s} {'JaCoCo':10s} 설명")
    for sid in sorted(sites, key=lambda x: (x[0] != "S", int(x[1:]))):
        s = sites[sid]
        print(f"{sid:5s} {g.get(sid, 0):4d} {rd.get(sid, 0):3d} {ro.get(sid, 0):4d} {rn.get(sid, 0):6d} "
              f"{js.get(sid, '-'):10s} {s['file']}:{s['line']} {s['desc']}")
    for name, d in [("grep", g), ("FindMethods", rd), ("FindMethods+overrides", ro), ("notypes", rn)]:
        extra = [k for k in d if k.startswith("?")]
        if extra:
            print(f"정답표 밖에서 {name} 이 찾은 줄: {extra}")
    S = [k for k in sites if k.startswith("S")]
    def summary(name, d):
        tp = sum(1 for k in S if d.get(k))
        fp = sum(1 for k in d if not k.startswith("S"))
        fn = len(S) - tp
        print(f"{name:24s} 찾은 곳 {len(d):2d}  정탐 {tp}  과다 {fp}  누락 {fn}")
    print()
    summary("grep", g)
    summary("FindMethods 기본", rd)
    summary("FindMethods matchOverrides", ro)
    summary("FindMethods 타입 없음", rn)
    summary("JaCoCo(부하 중 실행)", {k: v for k, v in jr.items() if k.startswith("S")})
    print("  참고: 대상이 아닌데 부하 중 실행된 줄(커버리지만으로는 대상과 구분 못 함):",
          [k for k in jr if k.startswith("G")])
    print(f"\nMethodCalls 데이터 테이블 행 수: 기본 {rd_rows}, overrides {ro_rows}, 타입 없음 {rn_rows}")


if __name__ == "__main__":
    main()
