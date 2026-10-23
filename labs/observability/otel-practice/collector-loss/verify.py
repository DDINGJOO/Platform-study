#!/usr/bin/env python3
"""Read-only evidence recheck against the running capture gateway and Tempo."""
import base64,json,pathlib
from urllib.request import urlopen
ROOT=pathlib.Path(__file__).resolve().parent
summary=json.loads((ROOT/'out/summary.json').read_text())
def get(port,path):
    with urlopen(f'http://localhost:{port}{path}',timeout=10) as r:return json.load(r)
receipts=get(27180,'/records')['receipts']
confirmed=0
for row in summary['results']:
    run=row['run']
    generated=json.loads((ROOT/f'out/{run}-generated.json').read_text())
    expected={(r['trace'],r['span']) for r in generated['accepted']}
    rejected={(r['trace'],r['span']) for r in generated['rejected']}
    received=[r for r in receipts if r[0]==run]
    stored={(r[1],r[2]) for r in received}
    assert stored <= expected and not stored & rejected
    assert len(expected)==row['collector_accepted']
    assert len(stored)==row['capture_unique_persisted']
    assert len(received)-len(stored)==row['duplicate_receipts']
    assert len(expected-stored)==row['accepted_missing']
    for trace,span in stored:
        doc=get(27110,f'/api/traces/{trace}')
        found={(base64.b64decode(s['traceId']).hex(),base64.b64decode(s['spanId']).hex()) for b in doc.get('batches',[]) for scope in b.get('scopeSpans',[]) for s in scope.get('spans',[])}
        assert (trace,span) in found
        confirmed+=1
print(f"PASS: {len(summary['results'])} scenarios, {confirmed} distinct spans re-queried from Tempo")
print('Original summary and generated evidence were not modified.')
