#!/usr/bin/env python3
"""여러 시나리오의 초별 응답(v1, v2, 실패)을 쌓은 막대로 그려 PNG 로 남긴다.
사용: python chart.py <출력.png> <시나리오>[=제목] ...
  예) python chart.py out/timeline.png recreate=Recreate rolling=롤링
Playwright(크롬)가 있으면 PNG 로 찍고, 없으면 out/chart.html 만 만든다."""
import csv, collections, html, os, sys

COL = {'v1': '#4a7fb5', 'v2': '#5a9e6f', 'fail': '#e5533c'}
LABEL = {'deploy-v2': 'v2 배포', 'rollout-done': '롤아웃 완료', 'all-v2': '새 연결 전부 v2', 'all-v1': '새 연결 전부 v1',
         'preview-ready': '미리보기 준비', 'promote': '승격', 'undo': '되돌리기', 'paused-again': '다시 멈춤'}
W, PH, L, R = 900, 150, 60, 20   # 폭, 패널 높이, 왼쪽 여백, 오른쪽 여백


def load(name):
    ev = [l.split(None, 1) for l in open(f'out/{name}.events') if l.strip()]
    t0 = int(ev[0][0])
    events = [((int(t) - t0) / 1000, e.strip()) for t, e in ev]
    per = collections.defaultdict(collections.Counter)
    for r in csv.DictReader(open(f'out/{name}.csv')):
        if r['metric_name'] != 'ver':
            continue
        v = dict(kv.split('=', 1) for kv in r['extra_tags'].split('&') if '=' in kv).get('v', '?')
        per[int((int(r['timestamp']) - t0) // 1000)][v] += 1
    return events, per


def panel(y0, title, events, per, tmax):
    sx = (W - L - R) / tmax
    ymax = 60
    sy = (PH - 40) / ymax
    out = [f'<text x="{L}" y="{y0 + 16}" font-size="15" font-weight="700">{html.escape(title)}</text>']
    base = y0 + PH - 14
    out.append(f'<line x1="{L}" y1="{base}" x2="{W - R}" y2="{base}" stroke="#999"/>')
    for yv in (0, 25, 50):
        y = base - yv * sy
        out.append(f'<text x="{L - 6}" y="{y + 4}" font-size="10" text-anchor="end" fill="#777">{yv}</text>')
        out.append(f'<line x1="{L}" y1="{y}" x2="{W - R}" y2="{y}" stroke="#eee"/>')
    for s in range(0, tmax):
        c = per.get(s)
        if not c:
            continue
        x = L + s * sx
        y = base
        used = 0
        for k in ('v1', 'v2', 'fail'):
            n = min(c[k], ymax - used)   # 몰려 끝난 초는 위를 자른다
            used += n
            h = n * sy
            if h:
                out.append(f'<rect x="{x:.1f}" y="{y - h:.1f}" width="{sx * 0.9:.1f}" height="{h:.1f}" fill="{COL[k]}"/>')
                y -= h
    shown = [(t, e) for t, e in events if e != 'load-start' and not e.startswith('term:')]
    for i, (t, e) in enumerate(shown):
        x = L + t * sx
        ty = y0 + 30 + (i % 3) * 13
        out.append(f'<line x1="{x:.1f}" y1="{ty - 10}" x2="{x:.1f}" y2="{base}" stroke="#333" stroke-dasharray="3 3"/>')
        out.append(f'<text x="{x + 3:.1f}" y="{ty}" font-size="11" fill="#333" paint-order="stroke" stroke="#fff" stroke-width="3">{html.escape(LABEL.get(e, e))} {t:.1f}s</text>')
    return '\n'.join(out)


def main():
    outpng = sys.argv[1]
    specs = [a.split('=', 1) if '=' in a else (a, a) for a in sys.argv[2:]]
    data = [(title, *load(name)) for name, title in specs]
    tmax = max(max(per) for _, _, per in data) + 1
    H = PH * len(data) + 50
    parts = [panel(10 + i * PH, title, ev, per, tmax) for i, (title, ev, per) in enumerate(data)]
    ax = []
    base = 10 + PH * len(data)
    for s in range(0, tmax + 1, 10):
        x = L + s * (W - L - R) / tmax
        ax.append(f'<text x="{x:.1f}" y="{base + 6}" font-size="11" text-anchor="middle" fill="#555">{s}s</text>')
    legend = ''.join(f'<rect x="{W - 230 + i * 70}" y="{base + 18}" width="12" height="12" fill="{COL[k]}"/>'
                     f'<text x="{W - 214 + i * 70}" y="{base + 29}" font-size="12">{k}</text>' for i, k in enumerate(COL))
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" font-family="Apple SD Gothic Neo, sans-serif">'
           f'<rect width="{W}" height="{H}" fill="#fff"/>' + '\n'.join(parts) + ''.join(ax) + legend +
           f'<text x="{L}" y="{base + 29}" font-size="12" fill="#555">초당 응답 수 (k6, 초당 50건)</text></svg>')
    page = f'<!doctype html><meta charset="utf-8"><body style="margin:0">{svg}</body>'
    os.makedirs('out', exist_ok=True)
    open('out/chart.html', 'w', encoding='utf-8').write(page)
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print('playwright 없음: out/chart.html 만 만들었다'); return
    with sync_playwright() as p:
        b = p.chromium.launch(channel='chrome', headless=True)
        pg = b.new_page(viewport={'width': W, 'height': H}, device_scale_factor=2)
        pg.goto('file://' + os.path.abspath('out/chart.html'))
        pg.screenshot(path=outpng, clip={'x': 0, 'y': 0, 'width': W, 'height': H})
        b.close()
    print('wrote', outpng)


main()
