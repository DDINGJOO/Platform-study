#!/usr/bin/env python3
"""로그 파일에서 가짜 개인정보가 몇 개 남았는지(줄마다 종류 수를 더한다) 경로(P1~P5)별로 센다.

같은 값이 다른 모양으로 남아도 잡도록 정규화한 뒤 찾는다.
  - HttpClient wire 로그의 바이트 표기 [0xffffffea] 를 바이트로 되돌려 UTF-8 로 읽는다
  - URL 인코딩(%20)을 푼다
  - NFKC 로 전각 숫자를 반각으로 바꾼다
  - 공백, 점, 여러 대시를 지운다
사용법: leaks.py out/a.log [out/b.log ...]       표
        leaks.py --lines out/a.log               걸린 줄
"""
import re, sys, unicodedata, urllib.parse

SENTINELS = {"이름": "김가짜", "주민번호": "9876543", "전화": "01000000000", "전화(011)": "0110000000"}
SEP = re.compile(r"[\s.\-‐-―−－]")

def decode_wire(line):
    def rep(m):
        bs = bytes(int(h, 16) & 0xFF for h in re.findall(r"\[0x([0-9a-f]+)\]", m.group(0)))
        return bs.decode("utf-8", "replace")
    return re.sub(r"(?:\[0x[0-9a-f]+\])+", rep, line)

def hits(line):
    t = unicodedata.normalize("NFKC", urllib.parse.unquote(decode_wire(line)))
    t = SEP.sub("", t)
    return [k for k, v in SENTINELS.items() if v in t]

def scan(path):
    per = {f"P{i}": 0 for i in range(1, 6)}
    found = []
    cur = None
    for line in open(path, encoding="utf-8"):
        m = re.match(r"### (P\d)", line)
        if m: cur = m.group(1); continue
        if line.startswith("### END"): cur = None; continue
        if cur and (h := hits(line)):
            per[cur] += len(h)
            found.append((cur, h, line.rstrip("\n")))
    return per, found

if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "--lines":
        for p, h, l in scan(args[1])[1]:
            print(f"{p} {'/'.join(h):<10} {l[:150]}")
        sys.exit()
    print(f"{'실행':<12}" + "".join(f"{'①②③④⑤'[i]:>5}" for i in range(5)) + "   합계")
    for a in args:
        per, _ = scan(a)
        name = a.split("/")[-1].removesuffix(".log")
        print(f"{name:<12}" + "".join(f"{per[f'P{i}']:>6}" for i in range(1, 6)) + f"{sum(per.values()):>7}")
