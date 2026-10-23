#!/usr/bin/env python3
"""Capture an actual Tempo trace in Grafana; requires the existing uploader Playwright venv."""
import json
import subprocess
import sys
from pathlib import Path
import urllib.parse
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
IMAGES = ROOT.parents[3] / "posts/CS/Observability/otel-practice/images/lab-02"
IMAGES.mkdir(parents=True, exist_ok=True)
records = json.loads((ROOT / "out/requests.json").read_text())
r = next(r for r in records if r["lab.mode"] == "tail" and r["lab.kind"] == "slow")
pane = {"a": {"datasource": "tempo", "queries": [{"refId": "A", "datasource": {"type": "tempo", "uid": "tempo"}, "queryType": "traceql", "query": r["trace_id"]}], "range": {"from": "now-1h", "to": "now"}}}
url = "http://127.0.0.1:27200/explore?schemaVersion=1&orgId=1&panes="+urllib.parse.quote(json.dumps(pane))
(ROOT / "out/grafana-url.txt").write_text(url+"\n")
with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome", headless=True)
    page = browser.new_page(viewport={"width":1440,"height":1000}, device_scale_factor=1.5)
    page.goto(url, wait_until="domcontentloaded")
    page.get_by_text("inventory.lookup", exact=False).first.wait_for(timeout=60000)
    page.wait_for_timeout(2000)
    text = page.locator("body").inner_text()
    assert "checkout-tail" in text and "inventory.lookup" in text, text[-2000:]
    assert "Trace not found" not in text and "No data" not in text, text[-2000:]
    (ROOT / "out/grafana-visible.txt").write_text(text)
    subprocess.run([sys.executable, str(ROOT.parents[3] / ".claude/skills/blog-post-pipeline/assets/mask-check.py"), str(ROOT / "out/grafana-visible.txt")], check=True)
    page.screenshot(path=str(IMAGES / "grafana-slow-trace.png"), full_page=False)
    browser.close()
print(url)
print(IMAGES / "grafana-slow-trace.png")
