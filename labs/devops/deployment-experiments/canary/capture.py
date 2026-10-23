#!/usr/bin/env python3
"""Capture live official Deck reports, actual Grafana data, saved verified output."""
import argparse
import datetime
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.parse
from urllib.request import urlopen

ROOT = pathlib.Path(__file__).resolve().parent
REPO = ROOT.parents[3]
IMAGES = REPO / 'posts/CS/DevOps/deployment-experiments/images/lab-01'
ASSETS = REPO / '.claude/skills/blog-post-pipeline/assets'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    from playwright.sync_api import sync_playwright
    summary = json.loads((ROOT / 'out/summary.json').read_text())
    subprocess.run([sys.executable, str(ROOT / 'verify.py')], check=True)
    IMAGES.mkdir(parents=True, exist_ok=True)
    previous = list(IMAGES.glob('*.png'))
    if previous:
        archive = ROOT / 'history/captures' / datetime.datetime.now().strftime('%Y%m%dT%H%M%S')
        archive.mkdir(parents=True)
        for path in previous:
            shutil.copy2(path, archive / path.name)
        shutil.copy2(ROOT / 'out/summary.json', archive / 'summary.json')
    # Deck renders query step 2s as this exact recurring decimal in minutes.
    # Reviewed against raw DOM; this is not an account/organization ID.
    capture_allow = (REPO / '.mask-allow').read_text() + '\n03333333333333333 # Deck query step 2s expressed as 0.03333333333333333 mins\n'
    def check_text(name, text):
        path = ROOT / 'out' / name
        path.write_text(text)
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt') as allow_file:
            allow_file.write(capture_allow)
            allow_file.flush()
            subprocess.run([sys.executable, str(ASSETS / 'mask-check.py'), str(path), '--allow', allow_file.name], check=True, cwd=REPO)
    with sync_playwright() as p:
        browser = p.chromium.launch(channel='chrome')
        page = browser.new_page(viewport={'width': 1500, 'height': 950}, device_scale_factor=1.5)
        for row in summary['cases']:
            responses = []
            def record(response):
                if '/v2/canaries/canary/' in response.url:
                    responses.append({'url': response.url, 'status': response.status})
            page.on('response', record)
            page.goto(row['deck_url'], wait_until='domcontentloaded')
            deadline = time.monotonic() + 90
            expected = row['judge']['score']['classification']
            while time.monotonic() < deadline:
                text = page.locator('body').inner_text()
                if 'mean-request-latency-ms' in text and expected.lower() in text.lower():
                    break
                page.wait_for_timeout(500)
            else:
                raise AssertionError(text)
            assert any(r['status'] == 200 and row['run_id'] in r['url'] for r in responses), responses
            check_text(f"{row['scenario']}-deck-dom.txt", text)
            (ROOT / 'out' / f"{row['scenario']}-browser-responses.json").write_text(json.dumps(responses, indent=2))
            page.screenshot(path=str(IMAGES / f"deck-{row['scenario']}.png"), full_page=True)
            page.remove_listener('response', record)
        def epoch(s):
            return datetime.datetime.fromisoformat(s.replace('Z', '+00:00')).timestamp()
        first, last = summary['cases'][0], summary['cases'][-1]
        start = int((epoch(first['measurement_start']) - 60) * 1000)
        end = int((epoch(last['measurement_end']) + 8) * 1000)
        url = f'http://localhost:28105/d/fresh-baseline/fresh-baseline?from={start}&to={end}&kiosk'
        panel_responses = []
        def grafana_response(response):
            if '/api/ds/query' in response.url and response.status == 200:
                panel_responses.append(response.json())
        page.on('response', grafana_response)
        page.goto(url, wait_until='networkidle')
        page.get_by_text('Actual process age').first.wait_for(timeout=90000)
        page.wait_for_timeout(2000)
        text = page.locator('body').inner_text()
        assert 'No data' not in text and 'Datasource not found' not in text, text
        assert panel_responses and any(result.get('frames') for response in panel_responses for result in response.get('results', {}).values()), panel_responses
        check_text('grafana-dom.txt', text)
        (ROOT / 'out/grafana-browser-responses.json').write_text(json.dumps(panel_responses, indent=2))
        (ROOT / 'out/grafana-capture-url.txt').write_text(url + '\n')
        page.screenshot(path=str(IMAGES / 'grafana-rollout.png'), full_page=True)
        browser.close()
    check_text('results.txt', (ROOT / 'out/results.txt').read_text())
    subprocess.run([sys.executable, str(ASSETS / 'term-shot.py'), '--from', str(ROOT / 'out/results.txt'), '--cmd', 'python3 verify.py', '--cwd', str(ROOT), '--source', 'out/results.txt', '-o', str(IMAGES / 'judge-checks.png')], check=True)
    print('Captured two actual Deck judge reports, actual Grafana rollout, and verified output.')

if __name__ == '__main__':
    main()
