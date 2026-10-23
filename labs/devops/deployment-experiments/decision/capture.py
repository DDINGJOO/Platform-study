#!/usr/bin/env python3
import importlib.util,pathlib,subprocess,sys
from playwright.sync_api import sync_playwright
ROOT=pathlib.Path(__file__).resolve().parent
REPO=ROOT.parents[3]
ASSETS=REPO/'.claude/skills/blog-post-pipeline/assets'
IMAGES=REPO/'posts/CS/DevOps/deployment-experiments/images/lab-03'
spec=importlib.util.spec_from_file_location('termshot',ASSETS/'term-shot.py')
termshot=importlib.util.module_from_spec(spec);spec.loader.exec_module(termshot)
IMAGES.mkdir(parents=True,exist_ok=True)
with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome',headless=True)
    page=browser.new_page(viewport={'width':1650,'height':1180},device_scale_factor=1.5)
    page.goto('http://localhost:28300',wait_until='networkidle')
    page.get_by_text('PASS_FIXED_RULES',exact=True).first.wait_for()
    assert page.locator('tbody tr').count()==5
    visible=page.locator('body').inner_text()
    for text in ['HOLD_SAMPLE','INVALID_SRM','STOP_GUARDRAIL','HOLD_EFFECT','합성 시나리오','자체 분석 보고서']:
        assert text in visible
    assert not termshot.mask_ok(visible,''),'Pre-capture visible text mask check failed'
    (ROOT/'out/report-visible.txt').write_text(visible+'\n')
    page.screenshot(path=str(IMAGES/'decision-report.png'),full_page=True)
    browser.close()
subprocess.run([sys.executable,str(ASSETS/'term-shot.py'),'--from',str(ROOT/'out/results.txt'),'--cmd','python run.py','--title','Fixed-window synthetic A/B decision analysis','--source','decision/out/results.txt','-o',str(IMAGES/'results.png')],check=True)
print('Actual own report over HTTP: 5 analyzed cases, pre-capture mask checks PASS')
