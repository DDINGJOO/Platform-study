#!/usr/bin/env python3
"""Capture real Grafana traces from the latest run. Uses the existing Playwright environment."""
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import urllib.parse
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[3]
IMAGES = REPO / 'posts/CS/Observability/otel-practice/images/lab-03'
summary = json.loads((ROOT / 'out/summary.json').read_text())
assert summary['assertions'] == 'PASS'
mask_path = REPO / '.claude/skills/blog-post-pipeline/assets/mask-check.py'
spec = importlib.util.spec_from_file_location('mask', mask_path)
mask = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mask)
def check(text):
    hits = [(name, len(re.findall(pattern, text))) for name, pattern in mask.GENERIC if re.search(pattern, text)]
    assert not hits, f'Mask check blocked capture: {hits}'

IMAGES.mkdir(parents=True, exist_ok=True)
check((ROOT / 'out/results.txt').read_text())
urls = {}
with sync_playwright() as p:
    browser = p.chromium.launch(channel='chrome', headless=True)
    for mode in ['micrometer', 'both']:
        trace_id = summary['modes'][mode][0]['trace_id']
        pane = {'datasource':'tempo','queries':[{'refId':'A','queryType':'traceql','query':trace_id,'limit':20}],
                'range':{'from':'now-24h','to':'now'}}
        url = 'http://localhost:27300/explore?schemaVersion=1&orgId=1&panes=' + urllib.parse.quote(json.dumps({'a':pane}))
        urls[mode] = url
        page = browser.new_page(viewport={'width':1440,'height':1200}, device_scale_factor=2)
        page.goto(url, wait_until='networkidle')
        page.get_by_text('checkout.quote', exact=False).first.wait_for(timeout=60000)
        count = 4 if mode == 'micrometer' else 7
        page.get_by_text(f'{count} spans', exact=True).wait_for(timeout=30000)
        text = page.locator('body').inner_text()
        assert trace_id in text
        assert 'No data' not in text and 'An unexpected error' not in text and 'Failed to fetch' not in text
        check(text)
        (ROOT / f'out/{mode}-grafana-body.txt').write_text(text)
        # Crop browser chrome/sidebar and query controls while keeping trace ID, time, and entire actual timeline.
        title = page.get_by_text(f'{mode}: ', exact=False).filter(has_text='checkout').first
        y = max(0, title.bounding_box()['y'] - 44)
        page.screenshot(path=str(IMAGES / f'{mode}-trace.png'),
                        clip={'x':500,'y':y,'width':930,'height':680})
        page.close()
    browser.close()
(ROOT / 'out/explore-urls.json').write_text(json.dumps(urls, indent=2) + '\n')
# The terminal renderer checks text before opening Chrome. This records saved real output.
import sys
subprocess.run([sys.executable, str(REPO / '.claude/skills/blog-post-pipeline/assets/term-shot.py'),
                '--from', str(ROOT / 'out/results.txt'), '--cmd', 'python3 run.py --no-build',
                '--source', 'out/results.txt', '--title', 'dual-instrumentation: actual verification',
                '-o', str(IMAGES / 'results.png')], cwd=ROOT, check=True)
print('Captured actual Grafana timelines: Micrometer 4 spans, both 7 spans; result output captured.')
