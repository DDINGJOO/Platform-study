#!/usr/bin/env python3
"""실습 실행 화면을 터미널 모양 PNG 로 찍는다 — PR 에 실행 결과 스크린샷을 붙이듯 글에 붙인다.

    V=~/.local/share/tistory-uploader/venv/bin/python
    $V term-shot.py --run "python3 scripts/analyze.py out/run1" --cwd labs/x/y -o posts/.../images/lab-04/analyze.png
    $V term-shot.py --cmd "scripts/run_all.sh e2" --from out/e2.txt -o ...      # 이미 저장된 출력을 찍는다
    $V term-shot.py ... --lines 1-40                                            # 일부만
    $V term-shot.py ... --source out/e2.txt                                     # 바닥글에 원자료 경로

--run 은 명령을 실제로 돌려 stdout+stderr 를 찍는다. --from 은 저장된 출력 파일을 찍는다.
바닥글에는 찍은 시각과 실행 디렉터리(또는 원자료 경로)가 들어간다. 감사자가 원자료와 대조하는 단서다.

**찍기 전에 텍스트로 마스킹 검사를 한다.** 이미지가 되면 mask-check 와 pre-commit 훅이
글자를 읽지 못한다. 걸리면 찍지 않고 멈춘다(--extra 목록은 mask-check 와 같은 파일).
.mask-allow 의 오탐 허용은 그대로 적용된다.

글에는 jsDelivr 주소로 건다(업로더에 이미지 업로드가 없다). 이미지를 main 에 먼저 푸시해야 한다.
    <img src="https://cdn.jsdelivr.net/gh/DDINGJOO/Platform-study@main/posts/<시리즈>/images/lab-NN/<파일>.png"
         alt="(무엇을 실행한 화면인지, 핵심 숫자)" style="max-width:100%">
"""
import argparse
import datetime
import html
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
ANSI = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")

CSS = """
body { margin: 0; background: transparent; }
.win { display: inline-block; min-width: 640px; max-width: 1100px; margin: 12px;
       background: #1e1f22; border-radius: 10px; box-shadow: 0 6px 22px rgba(0,0,0,.28); overflow: hidden;
       font-family: 'JetBrains Mono', 'D2Coding', Menlo, 'Apple SD Gothic Neo', monospace; }
.bar { background: #2b2d31; padding: 9px 14px; display: flex; align-items: center; gap: 8px; }
.dot { width: 12px; height: 12px; border-radius: 50%; display: inline-block; }
.title { color: #9aa0a6; font-size: 12.5px; margin-left: 10px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
pre { margin: 0; padding: 14px 18px 16px; color: #d8dadf; font-size: 13.5px; line-height: 1.5;
      white-space: pre-wrap; word-break: break-all; font-family: inherit; }
.prompt { color: #7ec699; } .cmd { color: #f0f0f0; font-weight: 600; }
.foot { border-top: 1px solid #34363b; color: #80868b; font-size: 11.5px; padding: 6px 18px 8px; }
"""


def mask_ok(text, extra):
    """mask-check.py 의 패턴과 .mask-allow 를 그대로 써서 텍스트를 검사한다."""
    sys.path.insert(0, HERE)
    import importlib.util
    spec = importlib.util.spec_from_file_location("mc", os.path.join(HERE, "mask-check.py"))
    mc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mc)
    allow = set()
    p = os.path.join(ROOT, ".mask-allow")
    if os.path.exists(p):
        for line in open(p, encoding="utf-8"):
            v = line.split("#", 1)[0].strip()
            if v:
                allow.add(v)
    hits = []
    for name, pat in mc.GENERIC:
        for m in re.finditer(pat, text):
            if m.group(0) not in allow:
                hits.append(f"[일반] {name}: {m.group(0)}")
    if extra and os.path.exists(extra):
        for line in open(extra, encoding="utf-8"):
            needle = line.split("=", 1)[0].strip()
            if needle and not needle.startswith("#") and needle.lower() in text.lower():
                hits.append("[조직] 조직 목록 적중")
    return hits


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--run", help="실제로 실행할 명령")
    g.add_argument("--from", dest="src", help="이미 저장된 출력 파일")
    ap.add_argument("--cmd", help="--from 일 때 화면에 보일 명령 줄")
    ap.add_argument("--cwd", default=".", help="--run 을 실행할 디렉터리(화면 제목에도 쓴다)")
    ap.add_argument("--lines", help="보일 줄 범위, 예: 1-40")
    ap.add_argument("--source", help="바닥글에 적을 원자료 경로")
    ap.add_argument("--title", help="창 제목(기본: 디렉터리)")
    ap.add_argument("--extra", default=os.path.expanduser("~/.config/blog-mask.txt"))
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--scale", type=float, default=2.0, help="해상도 배율")
    a = ap.parse_args()

    if a.run:
        r = subprocess.run(a.run, shell=True, cwd=a.cwd, capture_output=True, text=True)
        out, cmd = r.stdout + r.stderr, a.run
    else:
        out, cmd = open(a.src, encoding="utf-8", errors="replace").read(), a.cmd or ""
    out = ANSI.sub("", out).rstrip("\n")
    if a.lines:
        s, _, e = a.lines.partition("-")
        lines = out.split("\n")
        out = "\n".join(lines[int(s) - 1:int(e) if e else None])

    cwd_rel = os.path.relpath(os.path.abspath(a.cwd), ROOT)
    foot = f"{datetime.datetime.now():%Y-%m-%d %H:%M} · {a.source or cwd_rel}"
    title = a.title or cwd_rel
    hits = mask_ok("\n".join([cmd, out, foot, title]), a.extra)
    if hits:
        print("✗ 마스킹 검사에 걸려 찍지 않는다:", *hits[:10], sep="\n  ")
        sys.exit(2)

    body = (f'<span class="prompt">$</span> <span class="cmd">{html.escape(cmd)}</span>\n' if cmd else "") + html.escape(out)
    page = (f"<!doctype html><meta charset='utf-8'><style>{CSS}</style><div class='win'><div class='bar'>"
            "<span class='dot' style='background:#ff5f57'></span><span class='dot' style='background:#febc2e'></span>"
            f"<span class='dot' style='background:#28c840'></span><span class='title'>{html.escape(title)}</span></div>"
            f"<pre>{body}</pre><div class='foot'>{html.escape(foot)}</div></div>")
    from playwright.sync_api import sync_playwright
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as f:
        f.write(page)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome")
        pg = b.new_page(device_scale_factor=a.scale, viewport={"width": 1200, "height": 400})
        pg.goto("file://" + f.name)
        pg.locator(".win").screenshot(path=a.out, omit_background=True)
        b.close()
    os.unlink(f.name)
    print(f"✓ {a.out}")


if __name__ == "__main__":
    main()
