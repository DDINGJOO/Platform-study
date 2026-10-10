"""대시보드 패널의 exemplar 점 중 가장 위(가장 느린) 점에 마우스를 올려 툴팁을 찍고,
툴팁의 Tempo 링크를 눌러 열린 트레이스 화면을 찍는다.
사용: python exemplar-click.py <대시보드 URL> <툴팁.png> <트레이스.png>"""
import sys, time
from playwright.sync_api import sync_playwright

url, out_tip, out_trace = sys.argv[1:4]
with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome", headless=True)
    ctx = b.new_context(viewport={"width": 1440, "height": 1100}, device_scale_factor=2)
    pg = ctx.new_page()
    pg.goto(url, wait_until="load")
    time.sleep(8)
    markers = pg.locator("[data-testid$=\"Exemplar marker\"]").all()
    top = min(markers, key=lambda m: m.bounding_box()["y"])
    box = top.bounding_box()
    print("markers", len(markers), "top", box)
    top.hover()
    time.sleep(2)
    pg.screenshot(path=out_tip)
    link = pg.get_by_text("Query with Tempo").first
    link.click()
    time.sleep(10)
    pages = ctx.pages
    target = pages[-1]
    target.wait_for_load_state("load")
    time.sleep(6)
    print("url", target.url[:200])
    # 자식 스팬(lab.work) 행을 눌러 속성을 펼친다
    target.get_by_text("lab.work", exact=False).last.click()
    time.sleep(3)
    target.screenshot(path=out_trace, full_page=True)
    b.close()
