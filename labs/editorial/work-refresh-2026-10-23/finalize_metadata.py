#!/usr/bin/env python3
"""Integrate writer titles and compact navigation after all 112 writers finish."""
import argparse
import html
import json
import re
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def main(through=None):
    articles = json.loads((HERE / 'baseline.json').read_text())['articles']
    if through is not None:
        articles = [r for r in articles if r['number'] <= through]
    series_path = ROOT / 'tistory-series.json'
    series = json.loads(series_path.read_text())
    grouped = defaultdict(list)
    titles = []
    for row in articles:
        report = json.loads((HERE / 'writers' / f"{row['number']:03}.json").read_text())
        assert report['number'] == row['number'] and report['path'] == row['path']
        subject = report['suggested_subject'].strip()
        assert subject and '\n' not in subject and not re.match(r'^\d+편', subject)
        path = Path(row['path'])
        stem = re.sub(r'^\d+[a-z]?_', '', path.stem)
        episode = re.match(r'^(\d+)편\s*-\s*', stem).group(1)
        conf = series[path.parent.as_posix()]
        full = f"{conf['prefix']} {episode}편 - {subject}"
        conf.setdefault('titles', {})[stem] = full
        grouped[path.parent].append({**row, 'subject': subject, 'episode': episode})
        titles.append({'number': row['number'], 'path': row['path'], 'id': row['id'],
                       'before': row['title'], 'after': full})
    # Preflight every source before writing shared metadata or article navigation.
    replacements = []
    for rows in grouped.values():
        rows.sort(key=lambda r: int(r['episode']))
        for i, row in enumerate(rows):
            path = ROOT / row['path']
            src = path.read_text()
            match = re.search(r'<div class="obsv-series">.*?\n</div>', src, re.S)
            assert match, row['path']
            head = re.search(r'<div class="obsv-st">.*?</div>', match.group(0), re.S)
            assert head, row['path']
            lines = ['<div class="obsv-series">', '  ' + head.group(0)]
            for other in rows[max(0, i - 2):i + 1]:
                label = html.escape(f"{other['episode']}편. {other['subject']}")
                if other['number'] == row['number']:
                    lines.append(f'  <b>{label}</b> &larr; 지금 이 글')
                else:
                    lines.append(f'  <a href="https://dding-shark.tistory.com/{other["id"]}" style="color:inherit">{label}</a><br>')
            lines.append('</div>')
            replacements.append((path, src[:match.start()] + '\n'.join(lines) + src[match.end():]))
    series_path.write_text(json.dumps(series, ensure_ascii=False, indent=2) + '\n')
    for path, src in replacements:
        path.write_text(src)
    title_path = HERE / 'titles.json'
    previous = json.loads(title_path.read_text()) if title_path.exists() else []
    merged = {r['number']: r for r in previous}
    merged.update({r['number']: r for r in titles})
    title_path.write_text(json.dumps(sorted(merged.values(), key=lambda r: r['number']), ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'articles': len(articles), 'series': len(grouped),
                      'titles_changed': sum(r['before'] != r['after'] for r in titles)}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--through', type=int, help='Integrate completed articles up to this baseline number')
    main(parser.parse_args().through)
