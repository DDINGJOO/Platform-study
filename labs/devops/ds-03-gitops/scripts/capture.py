#!/usr/bin/env python3
"""Argo CD UI 화면을 캡처한다. Playwright 가 설치된 파이썬으로 돌린다.

  python capture.py <out.png> <경로(/applications/...)> [--wait 초] [--clip x,y,w,h] [--height 픽셀]

admin 비밀번호는 클러스터의 argocd-initial-admin-secret 에서 읽는다.
"""
import argparse, base64, json, subprocess, urllib.request
from playwright.sync_api import sync_playwright

BASE = "http://localhost:26080"

ap = argparse.ArgumentParser()
ap.add_argument("out")
ap.add_argument("path")
ap.add_argument("--wait", type=float, default=4)
ap.add_argument("--clip")
ap.add_argument("--height", type=int, default=900)
ap.add_argument("--width", type=int, default=1400)
ap.add_argument("--click", help="열고 나서 누를 버튼 글자 (예: DIFF)")
a = ap.parse_args()

pw = base64.b64decode(subprocess.check_output(
    ["kubectl", "--context", "kind-ds-03", "-n", "argocd", "get", "secret", "argocd-initial-admin-secret",
     "-o", "jsonpath={.data.password}"])).decode()
req = urllib.request.Request(BASE + "/api/v1/session", data=json.dumps({"username": "admin", "password": pw}).encode(),
                             headers={"Content-Type": "application/json"})
token = json.load(urllib.request.urlopen(req))["token"]

with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome", headless=True)   # 설치된 크롬을 쓴다
    ctx = b.new_context(viewport={"width": a.width, "height": a.height}, device_scale_factor=2)
    ctx.add_cookies([{"name": "argocd.token", "value": token, "url": BASE}])
    pg = ctx.new_page()
    pg.goto(BASE + a.path)
    pg.wait_for_timeout(int(a.wait * 1000))
    for label in (a.click.split("|") if a.click else []):   # "Diff|Compact diff" 처럼 차례로 누른다
        pg.get_by_text(label, exact=True).first.click()
        pg.wait_for_timeout(int(a.wait * 1000))
    if a.clip:
        x, y, w, h = map(int, a.clip.split(","))
        pg.screenshot(path=a.out, clip={"x": x, "y": y, "width": w, "height": h})
    else:
        pg.screenshot(path=a.out)
    b.close()
print(a.out)
