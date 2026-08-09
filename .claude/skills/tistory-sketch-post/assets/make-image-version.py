#!/usr/bin/env python3
"""단일 파일 글에서 그림을 뽑아 이미지 분리 버전을 만든다.

notion/: **단일 파일 버전.** 인라인 SVG 라 파일 하나에 그림까지 다 들어 있다.
         통째로 복사해 한 번에 옮기는 용도. 이쪽이 원본이다.
blog/  : **이미지 분리 버전.** SVG 를 2배 해상도 PNG 로 뽑아 images/<글번호>/ 에
         두고 <img> 로 참조한다. 그림을 따로 올려야 하는 곳에 쓴다.

    python3 make-image-version.py <원본루트> <출력루트>

원본은 건드리지 않는다. 출력 쪽은 매번 새로 만든다.
"""
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
BG = "#fdfaf3"
FIG_RE = re.compile(r'<div class="obsv-fig">\s*(<svg.*?</svg>)\s*</div>', re.S)


def render(svg: str, out: Path, tmp: Path) -> None:
    m = re.search(r'viewBox="0 0 (\d+) (\d+)"', svg)
    w, h = (int(m.group(1)), int(m.group(2))) if m else (700, 300)
    page = (
        f'<!doctype html><html><head><meta charset="utf-8"><style>'
        f"html,body{{margin:0;padding:0;background:{BG};}}"
        f"svg{{display:block;width:{w}px;height:{h}px;}}</style></head>"
        f"<body>{svg}</body></html>"
    )
    ph = tmp / "p.html"
    ph.write_text(page, encoding="utf-8")
    subprocess.run(
        [CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
         "--force-device-scale-factor=2", f"--window-size={w},{h}",
         f"--screenshot={out.resolve()}", f"file://{ph.resolve()}"],
        capture_output=True, timeout=90,
    )


def main() -> None:
    src_root, dst_root = Path(sys.argv[1]), Path(sys.argv[2])
    if dst_root.exists():
        shutil.rmtree(dst_root)
    tmp = dst_root / "_tmp"
    tmp.mkdir(parents=True)

    total_posts = total_figs = 0
    for html in sorted(src_root.rglob("*.html")):
        rel = html.relative_to(src_root)
        # 글 번호를 이미지 폴더 이름으로 쓴다 (한글 경로를 이미지 src 에 넣지 않기 위해)
        num = re.match(r"(\d+)", rel.name)
        slug = num.group(1) if num else rel.stem[:8]
        imgdir = dst_root / rel.parent / "images" / slug
        imgdir.mkdir(parents=True, exist_ok=True)

        text = html.read_text(encoding="utf-8")
        n = [0]

        def repl(m: re.Match) -> str:
            n[0] += 1
            png = imgdir / f"fig{n[0]}.png"
            render(m.group(1), png, tmp)
            return (f'<div class="obsv-fig">'
                    f'<img src="images/{slug}/fig{n[0]}.png" alt="그림 {n[0]}" '
                    f'style="width:100%;max-width:700px;height:auto;"></div>')

        out = FIG_RE.sub(repl, text)
        (dst_root / rel).write_text(out, encoding="utf-8")
        total_posts += 1
        total_figs += n[0]
        print(f"  {rel}  그림 {n[0]}개")

        if n[0] == 0:
            imgdir.rmdir()

    shutil.rmtree(tmp, ignore_errors=True)
    print(f"\n글 {total_posts}편 / 그림 {total_figs}장 -> {dst_root}")


if __name__ == "__main__":
    main()
