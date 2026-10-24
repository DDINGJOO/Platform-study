#!/usr/bin/env python3
"""Protect evidence while editing the Work corpus; validate before and after edits."""
import argparse
import collections
import hashlib
import html
import importlib.util
import json
import re
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BASELINE = HERE / 'baseline.json'


def sha(value):
    return hashlib.sha256(value.encode()).hexdigest()


def blocks(src, pattern):
    return re.findall(pattern, src, re.S)


def without_series(src):
    return re.sub(r'<div class="obsv-series">.*?\n</div>', '', src, flags=re.S)


def protected(src):
    # A comment can describe a literal <style> tag; it is not a CSS element.
    css_src = re.sub(r'<!--.*?-->', '', src, flags=re.S)
    return {
        'css': blocks(css_src, r'<style\b[^>]*>.*?</style>'),
        'code_blocks': blocks(src, r'<div class="obsv-code">.*?</div>|<pre\b[^>]*>.*?</pre>'),
        'inline_code': blocks(src, r'<code\b[^>]*>.*?</code>'),
        'images': blocks(src, r'<img\b[^>]*>'),
        'svg_geometry': [re.sub(r'>[^<]*<', '><', s) for s in blocks(src, r'<svg\b.*?</svg>')],
        'href_outside_series': re.findall(r'\bhref=[\"\']([^\"\']+)[\"\']', without_series(src)),
    }


def metrics(src):
    src = re.sub(r'<style\b.*?</style>|<svg\b.*?</svg>|<div class="obsv-code">.*?</div>', '', without_series(src), flags=re.S)
    text = html.unescape(re.sub(r'<[^>]+>|<!--.*?-->', '', src, flags=re.S))
    return {'text_chars': len(re.sub(r'\s+', '', text)), 'marks': src.count('class="obsv-mark"'),
            'numbers': dict(collections.Counter(re.findall(r'(?<!\w)\d+(?:[.,]\d+)*(?:%|초|개|건|분|일|배)?', text)))}


def load_checker():
    spec = importlib.util.spec_from_file_location('html_checker', ROOT / '.codex/skills/tistory-sketch-post/scripts/validate_html.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def init():
    assert not BASELINE.exists(), 'Baseline already exists; do not replace after editing'
    checker = load_checker()
    manifest = json.loads((ROOT / 'tistory-manifest.json').read_text())
    series = json.loads((ROOT / 'tistory-series.json').read_text())
    paths = sorted((ROOT / 'posts/Work').rglob('*.html'), key=lambda p: (0 if '/IaC/iac-log/' in p.as_posix() else 1 if '/IaC/' in p.as_posix() else 2, p.as_posix()))
    rows = []
    for number, path in enumerate(paths, 1):
        rel = path.relative_to(ROOT).as_posix()
        src = path.read_text()
        assert rel in manifest
        original = subprocess.check_output(['git', 'show', f'HEAD:{rel}'], cwd=ROOT).decode()
        assert original == src, 'Article changed before baseline'
        rows.append({'number': number, 'path': rel, 'id': str(manifest[rel]['id']), 'title': manifest[rel]['title'],
                     'common_tags': series[Path(rel).parent.as_posix()].get('tags', []),
                     'sha256': sha(src), 'protected': {k: [sha(v) for v in vals] for k, vals in protected(src).items()},
                     'existing_structure_errors': list(checker.validate_html(src)), 'metrics': metrics(src)})
    BASELINE.write_text(json.dumps({'commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(), 'articles': rows}, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'baseline_articles': len(rows), 'existing_structure_errors': sum(len(r['existing_structure_errors']) for r in rows)}))


def validate(only=None):
    baseline = json.loads(BASELINE.read_text())
    checker = load_checker()
    rows = []
    for old in baseline['articles']:
        if only and old['number'] != only:
            continue
        path = ROOT / old['path']
        src = path.read_text()
        now = {k: [sha(v) for v in vals] for k, vals in protected(src).items()}
        expected = dict(old['protected'])
        # Keep the immutable baseline intact, and derive the corrected CSS
        # expectation from its fixed Git commit rather than edited articles.
        original = subprocess.check_output(['git', 'show', f"{baseline['commit']}:{old['path']}"], cwd=ROOT).decode()
        expected['css'] = [sha(v) for v in protected(original)['css']]
        errors = [f'Evidence changed: {k}' for k in expected if now[k] != expected[k]]
        errors += [e for e in checker.validate_html(src) if e not in old['existing_structure_errors']]
        lead = re.search(r'<!--\s*lead:\s*(.*?)-->', src, re.S)
        tags = re.search(r'<!--\s*tags:\s*(.*?)-->', src, re.S)
        changed = sha(src) != old['sha256']
        if changed:
            if not lead or not 80 <= len(lead.group(1).strip()) <= 150:
                errors.append('Lead outside 80..150')
            specific = [s.strip() for s in tags.group(1).split(',') if s.strip()] if tags else []
            if not specific:
                errors.append('Specific tags missing')
            if len(set(old['common_tags'] + specific)) > 10:
                errors.append('More than ten merged tags')
        rows.append({'number': old['number'], 'path': old['path'], 'changed': changed, 'errors': errors,
                     'before': old['metrics'], 'after': metrics(src), 'sha256': sha(src)})
    result = {'articles': len(rows), 'changed': sum(r['changed'] for r in rows), 'pass': all(not r['errors'] for r in rows), 'results': rows}
    if not only:
        (HERE / 'checks.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'articles': len(rows), 'changed': result['changed'], 'pass': result['pass'], 'errors': [{'number': r['number'], 'errors': r['errors']} for r in rows if r['errors']]}, ensure_ascii=False))
    return 0 if result['pass'] else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--init', action='store_true')
    parser.add_argument('--only', type=int)
    args = parser.parse_args()
    if args.init:
        init()
    else:
        raise SystemExit(validate(args.only))
