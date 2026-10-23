#!/usr/bin/env python3
"""Validate the four updated posts while preserving historical presentation."""
import argparse
import hashlib
import importlib.util
import json
import re
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BASE = '4719a097d08cfc471415a226f872cc3e1b65f549'
POSTS = ROOT / 'posts/open-source-contribute'

def targets():
    return [*sorted((POSTS / 'spring-cloud-config').glob('*.html')),
            *sorted((POSTS / 'spinnaker').glob('02_*.html')),
            *sorted((POSTS / 'debezium').glob('02_*.html'))]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser', action='store_true')
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location('html_check', ROOT / '.codex/skills/tistory-sketch-post/scripts/validate_html.py')
    checker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(checker)
    paths = targets()
    assert len(paths) == 4
    rows = []
    for path in paths:
        rel = path.relative_to(ROOT).as_posix()
        src = path.read_text()
        before = subprocess.check_output(['git', 'show', f'{BASE}:{rel}'], cwd=ROOT, text=True)
        errors = list(checker.validate_html(src))
        for pattern in [r'<style>.*?</style>', r'<svg\b.*?</svg>', r'<div class="obsv-series">.*?\n</div>']:
            if re.findall(pattern, before, re.S) != re.findall(pattern, src, re.S):
                errors.append('Historical CSS/SVG/series box changed')
        lead = re.search(r'<!--\s*lead:\s*(.*?)-->', src, re.S)
        if not lead or not 80 <= len(lead.group(1).strip()) <= 150:
            errors.append('Lead outside 80..150 characters')
        rows.append({'path': rel, 'errors': errors, 'sha256': hashlib.sha256(src.encode()).hexdigest()})
    unchanged = [p for p in POSTS.rglob('*.html') if p not in paths]
    for path in unchanged:
        old = subprocess.check_output(['git', 'show', f'{BASE}:{path.relative_to(ROOT).as_posix()}'], cwd=ROOT)
        assert old == path.read_bytes(), 'Unrelated article changed'
    result = {'static': rows, 'unchanged_articles_preserved': len(unchanged)}
    if args.browser:
        from playwright.sync_api import sync_playwright
        result['browser'] = []
        with sync_playwright() as pw:
            browser = pw.chromium.launch(channel='chrome', headless=True)
            for path in paths:
                for width in [1100, 390]:
                    page = browser.new_page(viewport={'width': width, 'height': 844})
                    page.goto(path.as_uri(), wait_until='load')
                    page.evaluate('document.fonts.ready')
                    state = page.evaluate("""()=>({width:innerWidth,documentWidth:document.documentElement.scrollWidth,svg:document.querySelectorAll('svg').length,brokenImages:[...document.images].filter(i=>!i.complete||!i.naturalWidth).length})""")
                    result['browser'].append({'path': path.relative_to(ROOT).as_posix(), **state, 'pass': state['documentWidth'] <= width and state['brokenImages'] == 0})
                    page.close()
            browser.close()
    result['pass'] = all(not r['errors'] for r in rows) and all(r['pass'] for r in result.get('browser', []))
    (HERE / 'checks.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'articles': len(rows), 'unchanged_preserved': len(unchanged), 'browser_views': len(result.get('browser', [])), 'pass': result['pass'], 'errors': [e for row in rows for e in row['errors']]}, ensure_ascii=False))
    return 0 if result['pass'] else 1

if __name__ == '__main__':
    raise SystemExit(main())
