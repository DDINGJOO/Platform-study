#!/usr/bin/env python3
"""Read live visibility before editing, then verify every saved Work article."""
import argparse
import importlib.util
import json
import re
import subprocess
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
spec = importlib.util.spec_from_file_location('uploader', ROOT / '.claude/skills/tistory-sketch-post/assets/tistory-upload.py')
u = importlib.util.module_from_spec(spec)
spec.loader.exec_module(u)


class Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.skip = 0
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in ('svg', 'style', 'script'):
            self.skip += 1

    def handle_endtag(self, tag):
        if tag in ('svg', 'style', 'script'):
            self.skip -= 1

    def handle_data(self, value):
        if not self.skip:
            self.parts.append(value)


def normalize(text):
    return re.sub(r'\s+', '', text)


def main(baseline, through=None):
    assert not baseline or through is None, 'Baseline must cover the complete corpus'
    source = json.loads((HERE / 'baseline.json').read_text())
    selected = [r for r in source['articles'] if through is None or r['number'] <= through]
    before_file = HERE / 'publication-baseline.json'
    assert not baseline or not before_file.exists(), 'Do not replace the live visibility baseline'
    previous = {} if baseline else {r['number']: r for r in json.loads(before_file.read_text())['results']}
    manifest = u.load_json(u.MANIFEST, {})
    original = json.loads(subprocess.check_output(['git', 'show', f"{source['commit']}:tistory-manifest.json"], cwd=ROOT))
    series, files = u.load_json(u.SERIES, {}), u.post_files()
    keys = {r['path'] for r in source['articles']}
    assert set(original) == set(manifest)
    assert all(manifest[k] == v for k, v in original.items() if k not in keys)
    results = []
    lock = u.hold_lock(True)
    with sync_playwright() as pw:
        ctx = u.open_ctx(pw)
        page = ctx.new_page()
        page.on('dialog', u.on_dialog)
        u.ensure_login(page)
        for row in selected:
            path = ROOT / row['path']
            entry = manifest[row['path']]
            assert str(entry['id']) == row['id'] == str(original[row['path']]['id'])
            if baseline:
                visibility = u.current_visibility(page, row['id'])
                assert visibility, f"Cannot read visibility: {row['id']}"
                result = {'number': row['number'], 'path': row['path'], 'id': row['id'], 'visibility': visibility}
            else:
                visibility = previous[row['number']]['visibility']
                assert entry['visibility'] == visibility
                rendered = u.render(path, path.read_text(), manifest, files)
                tags = u.tags_of(path, series, rendered)
                ok, detail = u.verify(page, row['id'], rendered, visibility, tags)
                assert ok, f"/{row['id']}: {detail}"
                text = Text()
                text.feed(rendered)
                got = page.evaluate("""() => {
                  const c = document.querySelector('.contents_style').cloneNode(true);
                  c.querySelectorAll('svg,style,script').forEach(e => e.remove());
                  return c.textContent;
                }""")
                assert normalize(got) == normalize(''.join(text.parts)), f"Body text differs: /{row['id']}"
                titles = page.evaluate("""() => [...document.querySelectorAll('h1,h2,meta[property="og:title"]')]
                    .map(e => e.content || e.innerText.trim())""")
                title_match = entry['title'] in titles
                if not title_match:
                    page.goto(f"{u.BLOG}/manage/newpost/{row['id']}?type=post&returnURL=ENTRY")
                    title_match = page.locator('#post-title-inp').input_value() == entry['title']
                assert title_match, f"Title differs: /{row['id']}"
                assert u.sha(rendered) == entry['sha256']
                result = {'number': row['number'], 'path': row['path'], 'id': row['id'],
                          'url': f"{u.BLOG}/{row['id']}", 'visibility': visibility,
                          'title': entry['title'], 'tags': tags, 'body_text_exact': True,
                          'render_sha256': u.sha(rendered), 'verified': True}
            results.append(result)
            if len(results) % 14 == 0:
                print(f'Read {len(results)}/{len(selected)} posts', flush=True)
        u.keep_state(ctx)
        ctx.close()
    result = {'baseline': baseline, 'articles': len(results), 'existing_ids_preserved': True,
              'unchanged_other_manifest_entries': len(original) - len(keys),
              'checked_at': datetime.now(timezone.utc).isoformat(timespec='seconds'), 'results': results}
    suffix = f'-through-{through:03}' if through is not None else ''
    (before_file if baseline else HERE / f'publication{suffix}.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'articles': len(results), 'baseline': baseline, 'verified': True}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', action='store_true')
    parser.add_argument('--through', type=int)
    args = parser.parse_args()
    main(args.baseline, args.through)
