#!/usr/bin/env python3
"""글 안의 인라인 SVG를 PNG로 뽑는다 (티스토리가 SVG를 걷어낼 때 대비용)."""
import re, os, subprocess, sys, shutil

SRC = sys.argv[1]
OUTDIR = sys.argv[2]
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
BG = "#fdfaf3"

os.makedirs(OUTDIR, exist_ok=True)
html = open(SRC, encoding="utf-8").read()
svgs = re.findall(r"<svg.*?</svg>", html, flags=re.S)
print(f"SVG {len(svgs)}개 발견")

tmp = os.path.join(OUTDIR, "_tmp")
os.makedirs(tmp, exist_ok=True)

for i, svg in enumerate(svgs, 1):
    m = re.search(r'viewBox="0 0 (\d+) (\d+)"', svg)
    w, h = (int(m.group(1)), int(m.group(2))) if m else (700, 300)
    page = f"""<!doctype html><html><head><meta charset="utf-8">
<style>
@font-face {{ font-family:'Nanum Pen Script'; src: local('Nanum Pen Script'), local('나눔손글씨 펜'); }}
html,body {{ margin:0; padding:0; background:{BG}; }}
svg {{ display:block; width:{w}px; height:{h}px; }}
</style></head><body>{svg}</body></html>"""
    ph = os.path.join(tmp, f"fig{i}.html")
    open(ph, "w", encoding="utf-8").write(page)
    out = os.path.abspath(os.path.join(OUTDIR, f"fig{i}.png"))
    subprocess.run([
        CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
        "--force-device-scale-factor=2",
        f"--window-size={w},{h}",
        f"--screenshot={out}", f"file://{os.path.abspath(ph)}",
    ], capture_output=True, timeout=90)
    size = os.path.getsize(out) if os.path.exists(out) else 0
    print(f"  fig{i}.png  {w}x{h} @2x  ->  {size//1024}KB")

shutil.rmtree(tmp, ignore_errors=True)
print("완료:", OUTDIR)
