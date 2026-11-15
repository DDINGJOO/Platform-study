#!/usr/bin/env python3
"""Bounded IPIP capture experiment; touches only namespace calico-blog-52 and /tmp/cb52-* files."""
from pathlib import Path
import base64, concurrent.futures, datetime, json, re, shlex, subprocess, time

HERE=Path(__file__).resolve().parent
LAB=Path('/Users/dding/orca/workspaces/k8s/tang/lab')
NS='calico-blog-52'
LOG=[]
def run(args, ok=(0,), timeout=45):
    start=datetime.datetime.now().astimezone().isoformat()
    p=subprocess.run([str(LAB),*args],text=True,capture_output=True,timeout=timeout)
    LOG.append(dict(at=start,command=shlex.join([str(LAB),*args]),exit=p.returncode,stdout=p.stdout,stderr=p.stderr))
    if p.returncode not in ok: raise RuntimeError(LOG[-1])
    return p.stdout
def k(*args,**kw):return run(['kubectl',*args],**kw)
def ssh(node,*args,**kw):return run(['ssh',node,'--',*args],**kw)
def save(): (HERE/'commands.json').write_text(json.dumps(LOG,ensure_ascii=False,indent=2)+'\n')

pods=[]
for name,node,image,command in [('client','k8s-worker1','curlimages/curl:8.11.1',['sleep','3600']),('local','k8s-worker1','nginx:1.25.1-alpine',None),('remote','k8s-worker2','nginx:1.25.1-alpine',None)]:
    spec={'nodeName':node,'automountServiceAccountToken':False,'containers':[{'name':name,'image':image,'imagePullPolicy':'Never','resources':{'requests':{'cpu':'5m','memory':'8Mi'},'limits':{'cpu':'100m','memory':'32Mi'}}}]}
    if command:spec['containers'][0]['command']=command
    pods.append({'apiVersion':'v1','kind':'Pod','metadata':{'name':name,'namespace':NS,'labels':{'experiment':'calico52'}},'spec':spec})
manifest={'apiVersion':'v1','kind':'List','items':[{'apiVersion':'v1','kind':'Namespace','metadata':{'name':NS}},*pods]}
(HERE/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
created=False
try:
    k('get','namespace',NS,ok=(0,1))
    assert 'not found' in LOG[-1]['stderr'].lower(), 'Namespace exists: refusing to overwrite another run'
    k('create','-f',str(HERE/'manifest.json'))
    created=True
    k('wait','-n',NS,'--for=condition=Ready','pod','--all','--timeout=90s',timeout=100)
    pdata=json.loads(k('get','pods','-n',NS,'-o','json'))
    ips={p['metadata']['name']:p['status']['podIP'] for p in pdata['items']}
    (HERE/'pods.json').write_text(json.dumps(pdata,indent=2)+'\n')
    routes={}
    for name,node in [('client','worker1'),('local','worker1'),('remote','worker2')]:
        routes[name]=ssh(node,'ip','route','get',ips[name]);
    devs={n:re.search(r'\bdev (\S+)',s).group(1) for n,s in routes.items()}
    sid=ssh('worker1','sudo','crictl','pods','--namespace',NS,'--name','client','-q').strip()
    inspect=json.loads(ssh('worker1','sudo','crictl','inspectp',sid))
    pid=str(inspect['info']['pid'])
    snapshots={'ips':ips,'devices':devs,'client_sandbox_pid':pid,'routes_to_pods':routes,
      'cross_route':ssh('worker1','ip','route','get',ips['remote']),
      'worker1_eth0':ssh('worker1','ip','-4','addr','show','dev','eth0'),
      'worker2_eth0':ssh('worker2','ip','-4','addr','show','dev','eth0'),
      'ippool':k('get','ippools.crd.projectcalico.org','-o','yaml'),
      'offload_worker1':ssh('worker1','sudo','ethtool','-k','eth0'),
      'offload_worker2':ssh('worker2','sudo','ethtool','-k','eth0')}
    (HERE/'environment.json').write_text(json.dumps(snapshots,indent=2)+'\n')
    inner=f'tcp and host {ips["client"]} and (port 45252 or port 45253)'
    outer='ip proto 4 and host 192.168.104.3 and host 192.168.104.4'
    caps=[('client-eth0','worker1','eth0',True,inner),('client-cali','worker1',devs['client'],False,inner),('local-cali','worker1',devs['local'],False,inner),('worker1-tunl0','worker1','tunl0',False,inner),('worker1-eth0','worker1','eth0',False,outer),('worker2-eth0','worker2','eth0',False,outer),('worker2-tunl0','worker2','tunl0',False,inner),('remote-cali','worker2',devs['remote'],False,inner)]
    def capture(cap):
        name,node,iface,netns,flt=cap
        prefix=['sudo','timeout','-s','INT','10']
        if netns:prefix+=['nsenter','-t',pid,'-n']
        return ssh(node,*prefix,'tcpdump','-U','-nn','-s','256','-i',iface,'-w',f'/tmp/cb52-{name}.pcap',flt,ok=(0,124),timeout=20)
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        jobs=[pool.submit(capture,c) for c in caps]
        time.sleep(2)
        for name,port in [('local',45252),('remote',45253)]:
            out=k('exec','-n',NS,'client','--','curl','--noproxy','*','--local-port',str(port),'--connect-timeout','3','--max-time','5','-sS','-o','/dev/null','-w',f'{name}: HTTP %{{http_code}} local=%{{local_ip}}:%{{local_port}} remote=%{{remote_ip}}:%{{remote_port}}\n',f'http://{ips[name]}/')
            (HERE/f'{name}-request.txt').write_text(out)
        for job in jobs:job.result()
    for name,node,iface,netns,flt in caps:
        raw=ssh(node,'sudo','base64','-w','0',f'/tmp/cb52-{name}.pcap')
        (HERE/f'{name}.pcap').write_bytes(base64.b64decode(raw))
        text=ssh(node,'sudo','tcpdump','-nn','-tttt','-vvv','-S','-r',f'/tmp/cb52-{name}.pcap')
        (HERE/f'{name}.txt').write_text(text)
        ssh(node,'sudo','rm','-f',f'/tmp/cb52-{name}.pcap')
    (HERE/'capture-map.json').write_text(json.dumps([dict(name=n,node=no,interface=i,client_netns=ns,filter=f) for n,no,i,ns,f in caps],indent=2)+'\n')
finally:
    if created:
        k('delete','namespace',NS,'--ignore-not-found=true','--wait=true','--timeout=60s',timeout=70)
        k('get','namespace',NS,ok=(1,))
    save()
print(json.dumps({'ips':ips,'devices':devs,'recorded_commands':len(LOG)},indent=2))
