#!/usr/bin/env python3
"""Run the isolated application capstone; keep the final healthy application."""
import concurrent.futures
import argparse
import json
import subprocess
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--lab-root', type=Path, default=Path.cwd(), help='k8s-playground checkout containing lab and .lab')
ROOT = parser.parse_args().lab_root.resolve()
OUT = HERE / ('evidence-' + datetime.now().strftime('%Y%m%d-%H%M%S'))
OUT.mkdir()
K = [str(ROOT / '.lab/bin/kubectl'), '--kubeconfig', str(ROOT / '.lab/kubeconfig')]
NS = 'app-capstone'
URL = 'http://192.168.64.3:30057'
PHASE = 'initial'
STOP = threading.Event()
LOCK = threading.Lock()


def now():
    return datetime.now(timezone.utc).isoformat()


def command(args, name=None, check=True, timeout=180):
    r = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    entry = {'time': now(), 'argv': args, 'returncode': r.returncode,
             'stdout': r.stdout, 'stderr': r.stderr}
    if name:
        (OUT / (name + '.json')).write_text(json.dumps(entry, ensure_ascii=False, indent=2))
    if check and r.returncode:
        raise RuntimeError(entry)
    return r.stdout


def k(*args, **kw):
    return command(K + ['-n', NS] + list(args), **kw)


def objects():
    return json.loads(k('get', 'pods,rs,deploy,endpointslices,svc', '-o', 'json'))


def compact(data):
    result = []
    for o in data['items']:
        m, s, st = o['metadata'], o.get('spec', {}), o.get('status', {})
        item = {'kind': o['kind'], 'name': m['name'], 'uid': m['uid'],
                'owners': m.get('ownerReferences', []), 'deleted': m.get('deletionTimestamp')}
        if o['kind'] == 'Pod':
            item.update(node=s.get('nodeName'), ip=st.get('podIP'), phase=st.get('phase'),
                        conditions=st.get('conditions', []), containers=st.get('containerStatuses', []),
                        version=next((e.get('value') for e in s['containers'][0].get('env', []) if e['name']=='APP_VERSION'), None))
        elif o['kind'] == 'EndpointSlice':
            item.update(endpoints=o.get('endpoints'), ports=o.get('ports'))
        elif o['kind'] == 'Service':
            item.update(clusterIP=s.get('clusterIP'), ports=s.get('ports'))
        else:
            item.update(replicas=s.get('replicas'), status=st)
        result.append(item)
    return {'time': now(), 'phase': PHASE, 'objects': result}


def poll():
    with (OUT / 'timeline.jsonl').open('w') as f:
        while not STOP.is_set():
            try:
                row = compact(objects())
                f.write(json.dumps(row) + '\n'); f.flush()
            except Exception as e:
                f.write(json.dumps({'time': now(), 'phase': PHASE, 'error': str(e)}) + '\n'); f.flush()
            STOP.wait(.4)


def ready_pod():
    for o in objects()['items']:
        if o['kind']=='Pod' and o['metadata']['labels'].get('app')=='deploy-board' and not o['metadata'].get('deletionTimestamp'):
            return o
    return None


def ready_state(pod):
    return any(c['type']=='Ready' and c['status']=='True' for c in pod.get('status',{}).get('conditions',[]))


def until(fn, seconds=120):
    end=time.monotonic()+seconds
    while time.monotonic()<end:
        v=fn()
        if v: return v
        time.sleep(.25)
    raise TimeoutError('condition did not become true')


def sample(label, action, seconds):
    global PHASE
    PHASE=label
    rows=[]
    def loop():
        start=time.monotonic()
        while time.monotonic()-start<seconds:
            rid=f'{label}-{len(rows):04d}'
            t=time.monotonic()
            r=subprocess.run(['curl','-sS','--connect-timeout','1','--max-time','2','-H',f'X-Request-ID: {rid}',URL+'/api/info','-w','\n%{http_code}'],capture_output=True,text=True)
            try: body,status=r.stdout.rsplit('\n',1);body=json.loads(body)
            except (ValueError,json.JSONDecodeError): body,status=r.stdout,'000'
            rows.append({'time':now(),'id':rid,'returncode':r.returncode,'http':status,'elapsed_seconds':round(time.monotonic()-t,4),'body':body,'stderr':r.stderr})
            time.sleep(.25)
    with concurrent.futures.ThreadPoolExecutor() as pool:
        future=pool.submit(loop)
        time.sleep(1)
        action()
        future.result()
    (OUT/(label+'-requests.json')).write_text(json.dumps(rows,indent=2))
    return {'samples':len(rows),'http200':sum(r['returncode']==0 and r['http']=='200' for r in rows),
            'versions':{v:sum(isinstance(r['body'],dict) and r['body'].get('version')==v for r in rows) for v in ('v1','v2')},
            'errors':[r for r in rows if r['returncode'] or r['http']!='200']}


print(str(OUT),flush=True)
assert not json.loads(command(K+['get','namespace',NS,'--ignore-not-found','-o','json']) or '{}'), 'namespace already exists; refusing to overwrite'
command(K+['apply','-f',str(HERE/'application-v1.json')], '01-apply')
thread=threading.Thread(target=poll);thread.start()
try:
    p=until(lambda:(p if p and p.get('status',{}).get('phase')=='Running' and not ready_state(p) else None) if (p:=ready_pod()) else None)
    (OUT/'02-running-not-ready.json').write_text(json.dumps(p,indent=2))
    ip=p['status']['podIP']; node=p['spec']['nodeName']
    other='worker2' if node!='k8s-worker2' else 'worker1'
    # Running can precede bind/listen; wait for the HTTP listener, not phase alone.
    until(lambda:'HTTP 503' in command([str(ROOT/'lab'),'ssh',other,'--','curl','-sS','--max-time','2','-w','\nHTTP %{http_code}\n',f'http://{ip}:8080/readyz'],check=False),seconds=7)
    for path in ('readyz','api/info'):
        command([str(ROOT/'lab'),'ssh',other,'--','curl','-sS','--max-time','3','-w','\nHTTP %{http_code}\n',f'http://{ip}:8080/{path}'],'03-early-direct-'+path.replace('/','-'))
    command(['curl','-sS','--connect-timeout','1','--max-time','2','-w','\nHTTP %{http_code}\n',URL+'/api/info'],'04-early-nodeport',check=False)
    k('rollout','status','deployment/deploy-board','--timeout=120s',name='05-initial-ready')
    p=ready_pod(); name=p['metadata']['name']
    (OUT/'06-initial-state.json').write_text(json.dumps(objects(),indent=2))
    k('get','events','-o','json',name='07-events')
    # A client on another node verifies DNS and the actual ClusterIP path.
    client={'apiVersion':'v1','kind':'Pod','metadata':{'name':'request-client','namespace':NS},'spec':{'nodeSelector':{'kubernetes.io/hostname':'k8s-'+other},'restartPolicy':'Never','containers':[{'name':'client','image':'busybox:1.36.1','command':['sh','-c','sleep 600']} ]}}
    (HERE/'client.json').write_text(json.dumps(client,indent=2))
    k('apply','-f',str(HERE/'client.json'),name='08-client-create')
    k('wait','--for=condition=Ready','pod/request-client','--timeout=120s')
    k('exec','request-client','--','nslookup','deploy-board.app-capstone.svc.cluster.local',name='09-dns')
    k('exec','request-client','--','wget','-qO-','--header','X-Request-ID: internal-first-57','http://deploy-board/api/info',name='10-internal-http')
    k('logs',name,name='11-app-logs')
    # Readiness failure keeps a running process but withdraws its ready endpoint.
    PHASE='readiness-failure'
    k('exec',name,'--','touch','/tmp/not-ready',name='12-readiness-off')
    until(lambda:not ready_state(ready_pod()))
    time.sleep(2)
    (OUT/'13-unready-state.json').write_text(json.dumps(objects(),indent=2))
    command([str(ROOT/'lab'),'ssh',other,'--','curl','-sS','--max-time','3','-w','\nHTTP %{http_code}\n',f'http://{ip}:8080/api/info'],'14-unready-direct')
    command(['curl','-sS','--connect-timeout','1','--max-time','2','-w','\nHTTP %{http_code}\n',URL+'/api/info'],'15-unready-nodeport',check=False)
    k('exec',name,'--','rm','/tmp/not-ready',name='16-readiness-restore')
    until(lambda:ready_state(ready_pod()))
    time.sleep(2)
    command(['curl','-sS','--max-time','3',URL+'/api/info'],'17-ready-again')
    # Capture CRI and Linux networking only for the app, not other workloads.
    k('get','pod',name,'-o','json',name='18-pod-details')
    command([str(ROOT/'lab'),'ssh',node.removeprefix('k8s-'),'--','sudo','crictl','pods','--name',name,'-o','json'],'19-cri-sandbox')
    command([str(ROOT/'lab'),'ssh',node.removeprefix('k8s-'),'--','ip','route','get',ip],'20-host-route')
    rollout=sample('rollout',lambda:k('set','env','deployment/deploy-board','APP_VERSION=v2',name='21-release-v2'),35)
    k('rollout','status','deployment/deploy-board','--timeout=120s',name='22-rollout-ready')
    (OUT/'23-after-rollout.json').write_text(json.dumps(objects(),indent=2))
    before=ready_pod()
    replace=sample('replacement',lambda:k('delete','pod',before['metadata']['name'],'--wait=false',name='24-delete-app-pod'),35)
    until(lambda:ready_state(ready_pod()) if ready_pod() else False)
    after=ready_pod()
    (OUT/'25-after-replacement.json').write_text(json.dumps(objects(),indent=2))
    k('exec','request-client','--','wget','-qO-','--header','X-Request-ID: internal-final-57','http://deploy-board/api/info',name='26-final-internal-http')
    k('logs',after['metadata']['name'],name='27-final-app-logs')
    k('delete','pod','request-client','--wait=true',name='28-client-cleanup')
    k('get','deploy,rs,pods,svc,endpointslices','-o','wide',name='29-final-resources')
    command(['curl','-sS','--max-time','3','-H','X-Request-ID: final-check-57',URL+'/api/info'],'30-final-external-http')
    summary={'url':URL,'rollout':rollout,'replacement':replace,'before_delete':{'name':before['metadata']['name'],'uid':before['metadata']['uid'],'ip':before['status']['podIP']},'after_delete':{'name':after['metadata']['name'],'uid':after['metadata']['uid'],'ip':after['status']['podIP']},'completed':now()}
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2))
    print(json.dumps({**summary,'replacement':{k:v for k,v in replace.items() if k!='errors'}},indent=2),flush=True)
finally:
    STOP.set();thread.join()
