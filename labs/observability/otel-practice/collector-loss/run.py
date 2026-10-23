#!/usr/bin/env python3
"""Run only this Compose project; fresh volumes, ID-set assertions, evidence saved.
WARNING: this intentionally resets only otel-practice-01 lab volumes on each run.
"""
import base64, datetime, json, pathlib, subprocess, time
from urllib.request import Request, urlopen
ROOT=pathlib.Path(__file__).resolve().parent
OUT=ROOT/'out'

def compose(*args):
    subprocess.run(['docker','compose',*args],cwd=ROOT,check=True)
def http(port,path,payload=None):
    data=None if payload is None else json.dumps(payload).encode()
    req=Request(f'http://localhost:{port}{path}',data,{'Content-Type':'application/json'})
    with urlopen(req,timeout=30) as r:
        body=r.read()
        return json.loads(body) if body[:1] in (b'{',b'[') else body.decode()
def poll(fn, timeout=60):
    end=time.monotonic()+timeout
    last=None
    while time.monotonic()<end:
        try:
            result=fn()
            if result: return result
        except Exception as e: last=e
        time.sleep(.25)
    raise AssertionError(f'poll timed out: {last}')
def records(run):
    return [r for r in http(27180,'/records')['receipts'] if r[0]==run]
def ids(rows): return {(r[1],r[2]) for r in rows}
def emitted_ids(rows): return {(r['trace'],r['span']) for r in rows}
def ready():
    for port,path in [(27100,'/health'),(27180,'/health'),(27191,'/'),(27192,'/'),(27110,'/ready'),(27120,'/api/health')]:
        poll(lambda: http(port,path))
def mode(value): http(27180,'/mode',{'mode':value})
def emit(run,which,count):
    result=http(27100,'/orders',{'run':run,'mode':which,'count':count})
    (OUT/f'{run}-generated.json').write_text(json.dumps(result,indent=2))
    return result
def measure(run,emitted):
    rows=records(run); accepted=emitted_ids(emitted['accepted']); stored=ids(rows)
    assert stored <= accepted, (run,'unexpected persisted IDs')
    return {'run':run,'generated':len(emitted['generated']),'collector_accepted':len(accepted),'rejected':len(emitted['rejected']),'capture_unique_persisted':len(stored),'duplicate_receipts':len(rows)-len(stored),'accepted_missing':len(accepted-stored),'example_trace':rows[0][1] if rows else None}

def main():
    OUT.mkdir(exist_ok=True)
    if any(OUT.iterdir()):
        archive=ROOT/'history'/datetime.datetime.now().strftime('%Y%m%dT%H%M%S')
        archive.parent.mkdir(exist_ok=True); OUT.rename(archive); OUT.mkdir()
    compose('down','--volumes','--remove-orphans')
    compose('up','-d')
    ready(); rows=[]
    baseline=emit('baseline','memory',10)
    poll(lambda:len(ids(records('baseline')))==10)
    rows.append(measure('baseline',baseline)); assert rows[-1]['capture_unique_persisted']==10
    # Outage only, no Collector crash: both queue types retry and recover.
    mode('offline'); before=http(27180,'/records')['refusals']
    pending={w:emit(f'outage-{w}',w,20) for w in ('memory','disk')}
    poll(lambda:http(27180,'/records')['refusals']>before)
    assert not records('outage-memory') and not records('outage-disk')
    started=time.monotonic();mode('online')
    for w,e in pending.items():
        poll(lambda w=w:len(ids(records(f'outage-{w}')))==20)
        row=measure(f'outage-{w}',e);row['recovery_seconds']=round(time.monotonic()-started,3);rows.append(row)
        assert row['collector_accepted']==20 and row['accepted_missing']==0
    # Queue admission acknowledged while downstream is offline, then SIGKILL.
    mode('offline'); before=http(27180,'/records')['refusals']
    pending={w:emit(f'kill-{w}',w,20) for w in ('memory','disk')}
    poll(lambda:http(27180,'/records')['refusals']>before)
    assert not records('kill-memory') and not records('kill-disk')
    compose('kill','-s','SIGKILL','memory','disk')
    compose('up','-d','memory','disk'); ready()
    # The memory queue is gone: later same-pipeline sentinel proves the new process exports.
    started=time.monotonic();mode('online')
    sentinel=emit('after-restart-sentinel','memory',1)
    poll(lambda:len(ids(records('after-restart-sentinel')))==1)
    poll(lambda:len(ids(records('kill-disk')))==20)
    for w,e in pending.items():
        row=measure(f'kill-{w}',e);row['recovery_observation_seconds']=round(time.monotonic()-started,3);rows.append(row)
        assert row['collector_accepted']==20
        assert row['capture_unique_persisted']==(20 if w=='disk' else 0)
    # Deliberately overflow disk queue, without process loss. Rejected IDs never retried by app.
    mode('offline');overflow=emit('overflow-disk','disk',140)
    assert len(overflow['rejected'])>0 and len(overflow['accepted'])>0
    mode('online');poll(lambda:len(ids(records('overflow-disk')))==len(overflow['accepted']))
    rows.append(measure('overflow-disk',overflow));assert rows[-1]['accepted_missing']==0
    # A commit can precede an unsuccessful response: exporter retry repeats an identical ID.
    mode('lose-ack-once');ack=emit('lost-ack','disk',3)
    poll(lambda:len(records('lost-ack'))==6)
    rows.append(measure('lost-ack',ack));assert rows[-1]['duplicate_receipts']==3
    mode('online')
    tempo_confirmed=[]
    for row in rows:
        expected=ids(records(row['run']))
        for trace,span in expected:
            def check_trace(trace=trace,span=span):
                doc=http(27110,f'/api/traces/{trace}')
                found={(base64.b64decode(s['traceId']).hex(),base64.b64decode(s['spanId']).hex())
                       for batch in doc.get('batches',[]) for scope in batch.get('scopeSpans',[])
                       for s in scope.get('spans',[])}
                return (trace,span) in found
            poll(check_trace)
            tempo_confirmed.append({'run':row['run'],'trace':trace,'span':span})
        row['tempo_unique_spans_queried']=len(expected)
    (OUT/'tempo-confirmed.json').write_text(json.dumps(tempo_confirmed,indent=2))
    evidence={'executed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'versions':{'collector':'0.162.0','tempo':'2.10.8','grafana':'13.2.3','python_image':'3.12-slim'},'results':rows,'notes':['capture_unique_persisted measures SQLite committed IDs, not Tempo disaster durability','Each OTLP request has exactly one span; no SDK queue or batch processor','SIGKILL restarts preserve disk volume; host or disk failure not tested','Recovery seconds are observations, not a performance benchmark']}
    (OUT/'summary.json').write_text(json.dumps(evidence,indent=2))
    (OUT/'capture-receipts.json').write_text(json.dumps(http(27180,'/records'),indent=2))
    lines=[f"Collector queue experiment | {evidence['executed_at']}",'Collector 0.162.0 | Tempo 2.10.8 | Grafana 13.2.3','Each OTLP request = 1 span. Stored = SQLite committed unique IDs.','scenario                 generated accepted rejected stored duplicates missing']
    for r in rows: lines.append(f"{r['run']:24} {r['generated']:9} {r['collector_accepted']:8} {r['rejected']:8} {r['capture_unique_persisted']:6} {r['duplicate_receipts']:10} {r['accepted_missing']:7}")
    lines+=['ASSERTIONS: PASS','Collector receipt does not prove backend durability.','Disk queue protects this restart, not disk loss or queue overflow.','Lost success acknowledgement can cause duplicate delivery.','Grafana http://localhost:27120 | Tempo http://localhost:27110']
    text='\n'.join(lines)+'\n';(OUT/'results.txt').write_text(text);print(text)
    with (OUT/'compose.log').open('w') as f:subprocess.run(['docker','compose','logs','--no-color'],cwd=ROOT,stdout=f,check=True)
if __name__=='__main__': main()
