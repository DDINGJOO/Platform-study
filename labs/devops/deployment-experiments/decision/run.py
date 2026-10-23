#!/usr/bin/env python3
import argparse,datetime,gzip,hashlib,http.server,io,json,pathlib,platform,shutil,unittest
from functools import partial
from analysis import analyze
from generate import build_fixture
from report import render,pct,pp,pvalue
ROOT=pathlib.Path(__file__).resolve().parent
OUT=ROOT/'out'
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--serve',action='store_true');args=ap.parse_args()
    if OUT.exists() and any(OUT.iterdir()):
        archive=ROOT/'history'/datetime.datetime.now().strftime('%Y-%m-%dT%H-%M-%S')
        archive.parent.mkdir(exist_ok=True);shutil.move(OUT,archive)
        print('Previous evidence archived at '+str(archive.relative_to(ROOT)),flush=True)
    OUT.mkdir(exist_ok=True);(OUT/'events').mkdir()
    suite=unittest.defaultTestLoader.discover(str(ROOT),'test_*.py')
    stream=io.StringIO();test_result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    (OUT/'tests.txt').write_text(stream.getvalue())
    assert test_result.wasSuccessful(),stream.getvalue()
    plan=json.loads((ROOT/'plan.json').read_text());fixtures=json.loads((ROOT/'fixtures.json').read_text())
    summary={'executed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'),'python':platform.python_version(),'synthetic_only':True,'test_count':test_result.testsRun,'plan':plan,'scenarios':{}}
    for spec in fixtures:
        payload=build_fixture(spec,plan)
        raw=json.dumps(payload,separators=(',',':')).encode()
        (OUT/'events'/f'{spec["name"]}.json.gz').write_bytes(gzip.compress(raw,mtime=0))
        result=analyze(payload,plan)
        assert result['decision']==spec['expected_decision'],result
        result['source_sha256']=hashlib.sha256(raw).hexdigest()
        result['source_events']=f'events/{spec["name"]}.json.gz'
        summary['scenarios'][spec['name']]=result
    (OUT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    lines=['Fixed-window synthetic A/B decision lab: PASS',f'Executed: {summary["executed_at"]} | Python {summary["python"]}',f'Meaningful regression tests: {summary["test_count"]} PASS','Plan: 50:50, minimum 2000 users/group, one analysis after fixed window','Denominator: unique exposed users; numerator: unique eligible converters','','scenario        A users B users  A rate  B rate   delta    Newcombe95 [pp]       SRM p      decision']
    for name,r in summary['scenarios'].items():
        a,b=r['groups']['A'],r['groups']['B'];lo,hi=r['difference95_newcombe']
        lines.append(f'{name:<15} {a["exposed_users"]:>7} {b["exposed_users"]:>7} {pct(a["conversion_rate"]):>7} {pct(b["conversion_rate"]):>7} {pp(r["difference"]):>9} [{lo*100:+6.2f}, {hi*100:+6.2f}] {pvalue(r["srm"]["p_value"]):>10} {r["decision"]}')
    lines+=['','Each fixture: 20 event retries, 20 repeated exposures, 10 repeated conversions,','10 repeated request records and 4 temporally ineligible conversions excluded.','Guardrail-bad: B error 5.00%, p95 447ms; A error 0.50%, p95 147ms.','PASS_FIXED_RULES is a synthetic rule test, not product-lift evidence.']
    (OUT/'results.txt').write_text('\n'.join(lines)+'\n');render(summary,OUT/'index.html')
    print('\n'.join(lines),flush=True)
    if args.serve:
        print('Own saved analysis report: http://localhost:28300',flush=True)
        http.server.ThreadingHTTPServer(('0.0.0.0',8000),partial(http.server.SimpleHTTPRequestHandler,directory=str(OUT))).serve_forever()
if __name__=='__main__':main()
