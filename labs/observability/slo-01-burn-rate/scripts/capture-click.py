"""페이지를 열고 글자를 눌러 펼친 다음 찍는다(Prometheus·Alertmanager 화면용).
사용: python capture-click.py <출력.png> <URL> [--click 글자 ...] [--nth N] [--height H] [--width W] [--left L] [--top T] [--clip-height C]
--click 은 여러 번 줄 수 있고, 같은 글자가 여럿이면 --nth 번째(0부터)부터 끝까지 전부 누른다."""
import argparse, time
from playwright.sync_api import sync_playwright

ap = argparse.ArgumentParser()
ap.add_argument("out"); ap.add_argument("url")
ap.add_argument("--click", action="append", default=[])
ap.add_argument("--css", action="append", default=[], help="이 CSS 셀렉터에 맞는 요소를 전부 누른다")
ap.add_argument("--wait", type=float, default=4)
ap.add_argument("--width", type=int, default=1440); ap.add_argument("--height", type=int, default=900)
ap.add_argument("--left", type=int, default=0); ap.add_argument("--top", type=int, default=0)
ap.add_argument("--clip-height", type=int)
a = ap.parse_args()
with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome", headless=True)
    pg = b.new_page(viewport={"width": a.width, "height": a.height}, device_scale_factor=2)
    pg.goto(a.url, wait_until="load"); time.sleep(a.wait)
    for t in a.click:
        for el in pg.get_by_text(t, exact=True).all():
            el.click(); time.sleep(0.8)
    for c in a.css:
        for el in pg.locator(c).all():
            el.click(); time.sleep(0.8)
    time.sleep(1.5)
    pg.screenshot(path=a.out, full_page=True, clip={"x": a.left, "y": a.top, "width": a.width - a.left,
                                     "height": a.clip_height or a.height - a.top})
    b.close()
print(a.out)
