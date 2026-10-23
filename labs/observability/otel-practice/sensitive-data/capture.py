#!/usr/bin/env python3
"""Capture real Grafana panels and validated stdout; scan visible text BEFORE each image."""
import importlib.util, json, pathlib, subprocess, time
from playwright.sync_api import sync_playwright
ROOT=pathlib.Path(__file__).resolve().parent
REPO=ROOT.parents[3]
ASSETS=REPO/'.claude/skills/blog-post-pipeline/assets'
IMAGES=REPO/'posts/CS/Observability/otel-practice/images/lab-04'
spec=importlib.util.spec_from_file_location('termshot',ASSETS/'term-shot.py')
termshot=importlib.util.module_from_spec(spec);spec.loader.exec_module(termshot)
summary=json.loads((ROOT/'out/summary.json').read_text())
run_id=summary['run_id']
dashboard_path=ROOT/'grafana/provisioning/dashboards/privacy.json'
dashboard=json.loads(dashboard_path.read_text())
for panel in dashboard['panels']:
 mode=panel['title'].split(' | ')[0]
 panel['targets'][0]['expr']='{service_name=~"privacy-.*"} |= "mode='+mode+'" |= "'+run_id+'"'
dashboard_path.write_text(json.dumps(dashboard,indent=2)+'\n')
# Grafana's provisioning watcher imports the edited on-disk dashboard.
IMAGES.mkdir(parents=True,exist_ok=True)
with sync_playwright() as p:
 browser=p.chromium.launch(channel='chrome',headless=True)
 page=browser.new_page(viewport={'width':1500,'height':1150},device_scale_factor=1.5)
 page.goto('http://localhost:27400/d/privacy-boundaries?orgId=1&kiosk&from=now-1h&to=now',wait_until='networkidle')
 end=time.monotonic()+50
 while time.monotonic()<end:
  text=page.locator('body').inner_text()
  if text.count('customer=')>=24 and '[redacted]' in text and '[omitted]' in text:break
  page.wait_for_timeout(1000)
 else:raise AssertionError('Grafana did not render all 24 real log records')
 text=page.locator('body').inner_text()
 assert 'No data' not in text and 'An unexpected error' not in text
 hits=termshot.mask_ok(text, '')
 assert not hits, f'Visible Grafana text failed pre-capture mask scan: {hits}'
 (ROOT/'out/grafana-visible.txt').write_text(text+'\n')
 page.screenshot(path=str(IMAGES/'grafana-privacy.png'),full_page=True)
 browser.close()
subprocess.run([str(pathlib.Path(__import__('sys').executable)),str(ASSETS/'term-shot.py'),'--from',str(ROOT/'out/results.txt'),'--cmd','python3 run.py','--title','OTel synthetic privacy lab','--source','sensitive-data/out/results.txt','-o',str(IMAGES/'results.png')],check=True)
print('Grafana screenshot: 24 actual Loki log records, DOM text mask scan PASS')
