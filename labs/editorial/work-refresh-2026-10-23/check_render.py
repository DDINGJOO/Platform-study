#!/usr/bin/env python3
"""Compare desktop/mobile layout with the immutable pre-edit Work corpus."""
import argparse
import asyncio
import json
import subprocess
from pathlib import Path

from playwright.async_api import TimeoutError as PlaywrightTimeoutError, async_playwright

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
MEASURE = """() => {
  const cut = [...document.querySelectorAll('svg text')].flatMap((t, i) => {
    const b = t.getBBox(), v = t.ownerSVGElement.viewBox.baseVal;
    return b.x < v.x - 1 || b.x + b.width > v.x + v.width + 1 ||
           b.y < v.y - 1 || b.y + b.height > v.y + v.height + 1
      ? [{index:i, text:t.textContent.trim().slice(0,90)}] : [];
  });
  return {overflow: Math.max(0, document.documentElement.scrollWidth - innerWidth),
    clipped_svg_text:cut,
    images:[...document.images].map(i => ({loaded:i.complete && i.naturalWidth > 0})),
    svg_count:document.querySelectorAll('svg').length};
}"""


async def run(baseline, through=None):
    assert not baseline or through is None, 'Baseline must cover the complete corpus'
    source = json.loads((HERE / 'baseline.json').read_text())
    old = {} if baseline else {
        (r['number'], r['width']): r
        for r in json.loads((HERE / 'browser-baseline.json').read_text())['results']}
    queue = asyncio.Queue()
    for row in source['articles']:
        if through is not None and row['number'] > through:
            continue
        src = (subprocess.check_output(['git', 'show', f"{source['commit']}:{row['path']}"], cwd=ROOT).decode()
               if baseline else (ROOT / row['path']).read_text())
        for width in (390, 1280):
            queue.put_nowait((row, src, width))
    total_views = queue.qsize()
    results = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel='chrome', headless=True)
        context = await browser.new_context()

        async def worker():
            page = await context.new_page()
            while not queue.empty():
                row, src, width = queue.get_nowait()
                await page.set_viewport_size({'width': width, 'height': 1000})
                # CDN font/image loads can stall once; retry the same article,
                # keeping the same load/font conditions as the baseline.
                for attempt in range(2):
                    try:
                        await page.set_content(src, wait_until='load', timeout=60000)
                        break
                    except PlaywrightTimeoutError:
                        if attempt:
                            raise
                        print(f'Retry article {row["number"]} at {width}px after asset timeout', flush=True)
                await page.evaluate('document.fonts.ready')
                result = {'number': row['number'], 'path': row['path'], 'width': width,
                          **await page.evaluate(MEASURE)}
                if not baseline:
                    before = old[(row['number'], width)]
                    result['new_overflow'] = result['overflow'] > before['overflow']
                    existing = {r['index'] for r in before['clipped_svg_text']}
                    result['new_clipped_svg_text'] = [r for r in result['clipped_svg_text'] if r['index'] not in existing]
                results.append(result)
                queue.task_done()
                if len(results) % 28 == 0:
                    print(f'Checked {len(results)}/{total_views} views', flush=True)
            await page.close()

        await asyncio.gather(*(worker() for _ in range(4)))
        await context.close()
        await browser.close()
    results.sort(key=lambda r: (r['number'], r['width']))
    errors = [] if baseline else [
        {'number': r['number'], 'width': r['width'], 'overflow': r['new_overflow'],
         'clipped': r['new_clipped_svg_text']} for r in results
        if r['new_overflow'] or r['new_clipped_svg_text']]
    output = {'baseline': baseline, 'views': len(results), 'errors': errors, 'results': results}
    suffix = f'-through-{through:03}' if through is not None else ''
    (HERE / ('browser-baseline.json' if baseline else f'browser-checks{suffix}.json')).write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'views': len(results), 'new_layout_issues': len(errors),
                      'views_with_existing_overflow': sum(r['overflow'] > 0 for r in results)}, ensure_ascii=False))
    return int(bool(errors))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', action='store_true')
    parser.add_argument('--through', type=int)
    args = parser.parse_args()
    raise SystemExit(asyncio.run(run(args.baseline, args.through)))
