"""Grafana Explore 화면(또는 아무 URL)을 헤드리스 크롬으로 캡처한다.
사용: python capture.py <출력.png> <Explore 패널 JSON | http로 시작하는 URL> [--wait 초] [--clip 셀렉터]
패널 JSON 은 Grafana Explore URL 의 panes 값과 같은 모양이다. URL 을 주면 그 페이지를 그대로 찍는다
(Grafana 대시보드, Prometheus·Alertmanager 화면 등). Grafana 주소는 GRAFANA_URL 로 바꾼다."""
import argparse, json, os, time, urllib.parse
from playwright.sync_api import sync_playwright

ap = argparse.ArgumentParser()
ap.add_argument("out")
ap.add_argument("pane")
ap.add_argument("--wait", type=float, default=6)
ap.add_argument("--width", type=int, default=1440)
ap.add_argument("--height", type=int, default=900)
ap.add_argument("--clip", help="이 셀렉터의 요소만 잘라 찍는다")
ap.add_argument("--from-text", help="이 글자가 보이는 지점부터 화면 아래 끝까지 잘라 찍는다")
ap.add_argument("--left", type=int, default=0, help="왼쪽에서 잘라 낼 폭(px)")
ap.add_argument("--top", type=int, help="이 높이(px)부터 아래로 잘라 찍는다")
ap.add_argument("--clip-height", type=int, help="--from-text 지점부터 이만큼만 찍는다(px)")
a = ap.parse_args()

if a.pane.startswith("http"):
    url = a.pane
else:
    panes = urllib.parse.quote(json.dumps({"a": json.loads(a.pane)}))
    url = f"{os.environ.get('GRAFANA_URL', 'http://localhost:3000')}/explore?schemaVersion=1&orgId=1&panes={panes}"
with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome", headless=True)
    pg = b.new_page(viewport={"width": a.width, "height": a.height}, device_scale_factor=2)
    pg.goto(url, wait_until="load")
    time.sleep(a.wait)
    if a.top is not None:
        pg.screenshot(path=a.out, clip={"x": a.left, "y": a.top, "width": a.width - a.left,
                                        "height": a.clip_height or a.height - a.top})
    elif a.from_text:
        box = pg.get_by_text(a.from_text, exact=True).first.bounding_box()
        y = max(box["y"] - 12, 0)
        pg.screenshot(path=a.out, clip={"x": a.left, "y": y, "width": a.width - a.left, "height": a.clip_height or a.height - y})
    elif a.clip:
        pg.locator(a.clip).first.screenshot(path=a.out)
    else:
        pg.screenshot(path=a.out)
    b.close()
print(a.out)
