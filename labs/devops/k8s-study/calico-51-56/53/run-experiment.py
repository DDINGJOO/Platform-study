#!/usr/bin/env python3
"""Collect Calico MTU and isolated PMTUD evidence; clean only owned resources."""
from pathlib import Path
import datetime, json, shlex, subprocess, sys, time

ROOT = Path(__file__).resolve().parent
LAB = '/Users/dding/orca/workspaces/k8s/tang/lab'
NS = 'calico-blog-53'
records = []

def run(args, *, data=None, name=None, check=True):
    started = datetime.datetime.now().astimezone().isoformat()
    result = subprocess.run([str(x) for x in args], input=data, text=True, capture_output=True)
    record = dict(started=started, command=shlex.join([str(x) for x in args]),
                  exit_code=result.returncode, stdout=result.stdout, stderr=result.stderr)
    records.append(record)
    (ROOT/'commands.json').write_text(json.dumps(records, ensure_ascii=False, indent=2)+'\n')
    if name:
        (ROOT/name).write_text(f'$ {record["command"]}\nstarted={started}\n{result.stdout}{result.stderr}\nexit_code={result.returncode}\n')
    if check and result.returncode:
        raise RuntimeError(f'{record["command"]}: {result.stderr}')
    return result

def k(*args, **kwargs): return run([LAB, 'kubectl', *args], **kwargs)
def ssh(node, *args, **kwargs): return run([LAB, 'ssh', node, '--', *args], **kwargs)

owned = False
try:
    exists = k('get','namespace',NS,check=False)
    if exists.returncode == 0:
        raise RuntimeError(f'{NS} already exists; refusing to alter it')
    k('create','namespace',NS); owned = True
    pods = []
    for suffix, node in [('source','k8s-worker1'),('target','k8s-worker2')]:
        pods.append(dict(apiVersion='v1',kind='Pod',metadata=dict(name=suffix,namespace=NS),
          spec=dict(nodeName=node,terminationGracePeriodSeconds=0,containers=[dict(name='pause',
          image='registry.k8s.io/pause:3.10.2',imagePullPolicy='Never',
          resources=dict(requests=dict(cpu='1m',memory='4Mi'),limits=dict(cpu='20m',memory='16Mi')))])))
    manifest=dict(apiVersion='v1',kind='List',items=pods)
    (ROOT/'pods.json').write_text(json.dumps(manifest,indent=2)+'\n')
    k('apply','-f','-',data=json.dumps(manifest))
    k('wait','--for=condition=Ready','pod','--all','-n',NS,'--timeout=60s')
    state=json.loads(k('get','pods','-n',NS,'-o','json',name='01-pods.txt').stdout)
    byname={p['metadata']['name']:p for p in state['items']}
    cid=byname['source']['status']['containerStatuses'][0]['containerID'].split('://')[1]
    pid=json.loads(ssh('worker1','sudo','crictl','inspect',cid).stdout)['info']['pid']
    target=byname['target']['status']['podIP']
    ssh('worker1','sudo','ip','-d','link','show','eth0',name='02-underlay-mtu.txt')
    ssh('worker1','sudo','ip','-d','link','show','tunl0',name='03-tunnel-mtu.txt')
    ssh('worker1','sudo','nsenter','-t',str(pid),'-n','ip','-d','link','show','eth0',name='04-pod-mtu.txt')
    ssh('worker1','sudo','nsenter','-t',str(pid),'-n','ip','route','get',target,name='05-pod-route.txt')
    for size in [1400,1452,1453]:
        ssh('worker1','sudo','nsenter','-t',str(pid),'-n','ping','-4','-n','-c','2','-W','1','-M','do','-s',str(size),target,
            name=f'06-ping-{size}.txt',check=False)
    script=(ROOT/'isolated-pmtud.sh').read_text()
    ssh('worker1','sudo','bash','-s',data=script,name='07-isolated-pmtud.txt')
    for suffix in ['blocked','allowed']:
        for ext in ['pcap','txt']:
            remote=f'/tmp/cb53-evidence/{suffix}.{ext}'
            if ext == 'pcap':
                r=subprocess.run([LAB,'ssh','worker1','--','sudo','cat',remote],capture_output=True)
                if r.returncode: raise RuntimeError(r.stderr.decode())
                (ROOT/f'{suffix}.pcap').write_bytes(r.stdout)
            else:
                value=ssh('worker1','sudo','cat',remote)
                (ROOT/f'{suffix}-packets.txt').write_text(value.stdout)
    ssh('worker1','sudo','rm','-rf','/tmp/cb53-evidence')
finally:
    if owned:
        k('delete','namespace',NS,'--wait=true','--timeout=60s',name='08-pod-cleanup.txt',check=False)
    k('get','namespace',NS,name='09-namespace-absent.txt',check=False)
    ssh('worker1','sudo','ip','netns','list',name='10-netns-after.txt')
print('Evidence saved:',ROOT)
