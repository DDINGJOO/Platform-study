#!/usr/bin/env python3
"""Run only this Compose project, assert every synthetic data path, preserve exact evidence."""
import datetime, json, pathlib, shutil, subprocess, time, urllib.parse, urllib.request, uuid
ROOT=pathlib.Path(__file__).resolve().parent
OUT=ROOT/'out'
MODES=['raw','narrow','scrubbed','minimized']
MARKER='PRIVATE_CUSTOMER_ALPHA'
def compose(*args):
 return subprocess.run(['docker','compose','-f',str(ROOT/'compose.yaml'),*args],check=True,capture_output=True,text=True).stdout
def get(url,headers=None):
 req=urllib.request.Request(url,headers=headers or {})
 return urllib.request.urlopen(req,timeout=6).read()
def poll(fn, label, timeout=120):
 end=time.monotonic()+timeout
 last=None
 while time.monotonic()<end:
  try:
   result=fn()
   if result: return result
  except Exception as exc: last=repr(exc)
  time.sleep(.5)
 raise AssertionError(f'timeout: {label}: {last}')
def objects(path):
 if not path.exists():return []
 result=[]
 for line in path.read_text().splitlines():
  try:result.append(json.loads(line))
  except json.JSONDecodeError:pass # Retry while a file exporter write is in progress.
 return result
def records(mode,signal):
 filemode='scrubbed' if mode=='minimized' else mode
 key=('resourceSpans','scopeSpans','spans') if signal=='traces' else ('resourceLogs','scopeLogs','logRecords')
 result=[]
 for obj in objects(OUT/f'{filemode}-{signal}.jsonl'):
  for res in obj.get(key[0],[]):
   attrs={a['key']:a['value'].get('stringValue') for a in res['resource'].get('attributes',[])}
   if attrs.get('lab.mode')!=mode:continue
   for scope in res.get(key[1],[]):result.extend(scope.get(key[2],[]))
 return result
def attrs(record):return {a['key']:a['value'] for a in record.get('attributes',[])}
def count_marker(items):return sum(MARKER in json.dumps(item) for item in items)
def main():
 compose('down','--remove-orphans') # Name pinned in Compose: cannot touch any other project.
 if OUT.exists() and any(OUT.iterdir()):
  archive=ROOT/'out-history'/datetime.datetime.now().strftime('%Y-%m-%dT%H-%M-%S')
  archive.parent.mkdir(exist_ok=True);shutil.move(OUT,archive)
  print(f'Previous evidence archived at {archive.relative_to(ROOT)}',flush=True)
 OUT.mkdir(exist_ok=True)
 run_id='run-'+uuid.uuid4().hex[:6]
 dashboard_path=ROOT/'grafana/provisioning/dashboards/privacy.json'
 dashboard=json.loads(dashboard_path.read_text())
 for panel in dashboard['panels']:
  mode=panel['title'].split(' | ')[0]
  panel['targets'][0]['expr']='{service_name=~"privacy-.*"} |= "mode='+mode+'" |= "'+run_id+'"'
 dashboard_path.write_text(json.dumps(dashboard,indent=2)+'\n')
 compose('up','-d','--build')
 poll(lambda:get('http://localhost:27480/health'), 'front readiness')
 poll(lambda:get('http://localhost:27420/ready').strip()==b'ready', 'Tempo readiness')
 poll(lambda:get('http://localhost:27410/ready'), 'Loki readiness')
 poll(lambda:get('http://localhost:27400/api/health'), 'Grafana readiness')
 (OUT/'python-packages.txt').write_text(compose('exec','-T','front','python','-m','pip','freeze'))
 responses={}
 for mode in MODES:
  responses[mode]=[json.loads(get(f'http://localhost:27480/demo?mode={mode}&run={run_id}',{'baggage':f'private.customer={MARKER},tier=gold'})) for _ in range(3)]
 (OUT/'http-responses.json').write_text(json.dumps(responses,indent=2)+'\n')
 summary={'executed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'run_id':run_id,'versions':{'python':'3.12','otel_python':'1.39.1','collector':'0.162.0','tempo':'2.10.8','loki':'3.7.8','grafana':'13.2.3'},'modes':{}}
 tempo={}
 for mode in MODES:
  poll(lambda:len(records(mode,'traces'))==9 and len(records(mode,'logs'))==6,f'{mode} file export')
  spans=records(mode,'traces');logs=records(mode,'logs')
  assert len({s['spanId'] for s in spans})==9
  events=[e for s in spans for e in s.get('events',[])]
  assert len(events)==3
  traceids={s['traceId'] for s in spans}
  assert len(traceids)==3
  assert all(log['traceId'] in traceids for log in logs)
  # Tempo returns the legacy `batches` JSON field; fetch by observed SDK trace ID, not a guessed query.
  traces=[]
  for response in responses[mode]:
   tid=response['trace_id']
   data=poll(lambda:json.loads(get(f'http://localhost:27420/api/traces/{tid}',{'Accept':'application/json'})),f'Tempo {mode}')
   def tempo_spans(obj):
    return [sp for batch in obj.get('batches',obj.get('resourceSpans',[])) for scope in batch.get('scopeSpans',batch.get('instrumentationLibrarySpans',[])) for sp in scope.get('spans',[])]
   data=poll(lambda: (lambda obj: obj if len(tempo_spans(obj))==3 else None)(json.loads(get(f'http://localhost:27420/api/traces/{tid}',{'Accept':'application/json'}))),f'Tempo full trace {mode}')
   traces.append(data)
  tempo[mode]=traces
  query='{service_name=~"privacy-.*"} |= "'+run_id+'" |= "mode='+mode+'"'
  url='http://localhost:27410/loki/api/v1/query_range?'+urllib.parse.urlencode({'query':query,'limit':1000,'since':'1h'})
  lokidata=poll(lambda:(lambda d:d if sum(len(stream['values']) for stream in d['data']['result'])==6 else None)(json.loads(get(url))),f'Loki {mode}')
  (OUT/f'loki-{mode}.json').write_text(json.dumps(lokidata,indent=2)+'\n')
  expected_raw=mode=='raw'; expected_leak=mode in ['raw','narrow']
  values={'requests':3,'spans':len(spans),'events':len(events),'logs':len(logs),'tempo_spans':sum(len(tempo_spans(t)) for t in traces),'attribute_marker_spans':count_marker([attrs(s) for s in spans]),'event_marker_events':count_marker(events),'status_marker_spans':count_marker([s.get('status',{}) for s in spans]),'log_body_marker_logs':count_marker([l.get('body') for l in logs]),'loki_marker_logs':sum(MARKER in value[1] for stream in lokidata['data']['result'] for value in stream['values']),'downstream_private_baggage_requests':sum(r['received_private_baggage']==MARKER for r in responses[mode]),'downstream_tier_requests':sum(r['received_tier']=='gold' for r in responses[mode])}
  assert values['attribute_marker_spans']==(6 if expected_raw else 0),values
  assert values['event_marker_events']==(3 if expected_leak else 0),values
  assert values['status_marker_spans']==(3 if expected_leak else 0),values
  assert values['log_body_marker_logs']==(6 if expected_leak else 0),values
  assert values['loki_marker_logs']==(6 if expected_leak else 0),values
  assert values['downstream_private_baggage_requests']==(0 if mode=='minimized' else 3),values
  assert values['downstream_tier_requests']==3
  if not expected_leak:
   assert MARKER not in json.dumps(traces)
   assert MARKER not in json.dumps(logs)
   assert MARKER not in json.dumps(lokidata)
  summary['modes'][mode]=values
 (OUT/'tempo-traces.json').write_text(json.dumps(tempo,indent=2)+'\n')
 console=compose('logs','--no-color','--no-log-prefix','front','downstream')
 (OUT/'source-console.txt').write_text(console)
 for mode in MODES:
  count=sum(MARKER in line and f'mode={mode} ' in line for line in console.splitlines())
  summary['modes'][mode]['source_console_marker_logs']=count
  assert count==(0 if mode=='minimized' else 6)
 (OUT/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
 lines=['Synthetic-only privacy lab: PASS',f'Executed: {summary["executed_at"]}',f'Run: {run_id}','Versions: Python SDK 1.39.1 | Collector 0.162.0 | Tempo 2.10.8 | Loki 3.7.8','Each mode: 3 HTTP requests, 9 unique spans, 3 events, 6 correlated logs','Tempo: 3 full traces and 9 spans / mode; Loki: 6 logs / mode','','Marker-bearing records (not byte counts):','mode       attr  event  status  log  Loki  baggage  source-console']
 for mode,v in summary['modes'].items():
  lines.append(f'{mode:<10} {v["attribute_marker_spans"]:>4} {v["event_marker_events"]:>6} {v["status_marker_spans"]:>7} {v["log_body_marker_logs"]:>4} {v["loki_marker_logs"]:>5} {v["downstream_private_baggage_requests"]:>8} {v["source_console_marker_logs"]:>15}')
 lines+=['','Collector scrubbing does not change source console or HTTP baggage.','Producer minimization keeps approved tier=gold on all 3 downstream requests.','All assertions passed. Not a universal PII detector or historical erasure test.']
 (OUT/'results.txt').write_text('\n'.join(lines)+'\n')
 print('\n'.join(lines),flush=True)
if __name__=='__main__':main()
