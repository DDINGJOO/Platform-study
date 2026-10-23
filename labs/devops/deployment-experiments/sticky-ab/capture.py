#!/usr/bin/env python3
"""Capture the actual provisioned Grafana dashboard and saved integration output."""
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import sys
import time
import urllib.request
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[3]
IMAGES = REPO / 'posts/CS/DevOps/deployment-experiments/images/lab-02'
summary = json.loads((ROOT / 'out/summary.json').read_text())
for _ in range(90):
    try:
        with urllib.request.urlopen('http://127.0.0.1:28200/api/health', timeout=3) as response:
            assert response.status == 200
        with urllib.request.urlopen('http://127.0.0.1:28280/summary', timeout=3) as response:
            live = json.load(response)
        assert live['experiment_id'] == summary['experiment_id'] and live['variants'] == summary['variants'], 'Live experiment differs from saved summary'
        break
    except (OSError, AssertionError):
        time.sleep(1)
else:
    raise AssertionError('Grafana unavailable or live data differs from saved evidence')
IMAGES.mkdir(parents=True, exist_ok=True)
previous = list(IMAGES.glob('*.png'))
if previous:
    archive = ROOT / 'history/captures' / datetime.now(timezone.utc).strftime('%Y-%m-%dT%H-%M-%S.%fZ')
    archive.mkdir(parents=True)
    for path in previous:
        shutil.copy2(path, archive / path.name)
    shutil.copy2(ROOT / 'out/summary.json', archive / 'active-summary.json')
with sync_playwright() as p:
    browser = p.chromium.launch(channel='chrome')
    page = browser.new_page(viewport={'width': 1500, 'height': 650}, device_scale_factor=1.5)
    page.goto('http://127.0.0.1:28200/d/sticky-ab/sticky-ab?orgId=1&from=now-15m&to=now&kiosk', wait_until='networkidle')
    page.get_by_text('Distinct users · assignment').first.wait_for(timeout=90000)
    for variant, values in summary['variants'].items():
        page.get_by_text(str(values['exposure_users']), exact=True).first.wait_for(timeout=60000)
    body = page.locator('body').inner_text()
    assert 'No data' not in body and 'Datasource not found' not in body, body
    (ROOT / 'out/grafana-dom.txt').write_text(body)
    page.screenshot(path=str(IMAGES / 'grafana-users.png'), full_page=True)
    browser.close()
subprocess.run([sys.executable, str(REPO / '.claude/skills/blog-post-pipeline/assets/term-shot.py'), '--from', str(ROOT / 'out/results.txt'), '--cmd', 'python3 run.py', '--cwd', str(ROOT), '--source', 'out/results.txt', '-o', str(IMAGES / 'http-sqlite-checks.png')], check=True)
print('Saved real Grafana screenshot and rendered saved HTTP integration output.')
