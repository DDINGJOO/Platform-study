#!/usr/bin/env python3
"""Capture the actual recovered disk-queue trace from local Grafana Explore.
Requires existing Playwright and a locally installed Chrome; does not install either.
"""
import argparse,json,pathlib,subprocess,sys,urllib.parse
argparse.ArgumentParser(description=__doc__).parse_args()
from playwright.sync_api import sync_playwright
ROOT=pathlib.Path(__file__).resolve().parent
summary=json.loads((ROOT/'out/summary.json').read_text())
trace=next(r['example_trace'] for r in summary['results'] if r['run']=='kill-disk')
pane={'datasource':'tempo','queries':[{'refId':'A','datasource':{'type':'tempo','uid':'tempo'},'queryType':'traceId','query':trace}],'range':{'from':'now-1h','to':'now'}}
url='http://localhost:27120/explore?schemaVersion=1&orgId=1&panes='+urllib.parse.quote(json.dumps({'a':pane}))
out=ROOT.parents[3]/'posts/CS/Observability/otel-practice/images/lab-01/grafana-recovered-trace.png'
with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome',headless=True)
    page=browser.new_page(viewport={'width':1440,'height':1000},device_scale_factor=1.5)
    page.goto(url,wait_until='domcontentloaded')
    page.get_by_text('checkout-loss-lab',exact=False).first.wait_for(timeout=60000)
    page.get_by_text('POST /orders',exact=False).first.wait_for(timeout=30000)
    # Select the real span, opening its attribute table.
    page.get_by_text('POST /orders',exact=False).last.click()
    page.wait_for_timeout(1500)
    (ROOT/'out/grafana-rendered.txt').write_text(page.locator('body').inner_text())
    subprocess.run([sys.executable,str(ROOT.parents[3]/'.claude/skills/blog-post-pipeline/assets/mask-check.py'),str(ROOT/'out/grafana-rendered.txt')],check=True)
    page.screenshot(path=str(out))
    (ROOT/'out/grafana-url.txt').write_text(url+'\n')
    browser.close()
print(out)
