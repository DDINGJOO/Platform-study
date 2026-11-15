#!/usr/bin/env python3
"""Isolated Calico diagnosis cases. Only calico-blog-56 is mutated."""
import datetime as dt
import ipaddress
import json
from pathlib import Path
import shlex
import subprocess
import time

HERE = Path(__file__).resolve().parent
LAB = Path('/Users/dding/orca/workspaces/k8s/tang/lab')
NS = 'calico-blog-56'
records = []
matrix = []

def run(args, label, check=True, stdin=None):
    started = dt.datetime.now().astimezone().isoformat()
    p = subprocess.run([str(LAB), *args], input=stdin, text=True, capture_output=True, timeout=150)
    item = dict(label=label, started=started, ended=dt.datetime.now().astimezone().isoformat(),
                command=shlex.join([str(LAB), *args]), exit=p.returncode,
                stdout=p.stdout, stderr=p.stderr)
    records.append(item)
    (HERE / 'commands.json').write_text(json.dumps(records, ensure_ascii=False, indent=2)+'\n')
    (HERE / 'commands.txt').write_text('\n\n'.join(
        f"[{r['started']}] {r['label']}\n$ {r['command']}\n{r['stdout']}{r['stderr']}\nexit={r['exit']}"
        for r in records)+'\n')
    if check and p.returncode:
        raise RuntimeError(f'{label}: {p.returncode}: {p.stderr}')
    return item

def k(args, label, **kw): return run(['kubectl', '-n', NS, *args], label, **kw)

def pod(name, node, app, image, command=None):
    c = dict(name=name, image=image, imagePullPolicy='Never',
             resources=dict(requests={'cpu':'1m','memory':'12Mi'}, limits={'cpu':'100m','memory':'64Mi'}))
    if command: c['command'] = command
    else: c['readinessProbe'] = {'httpGet': {'path':'/', 'port':80}, 'initialDelaySeconds':1, 'periodSeconds':1}
    return dict(apiVersion='v1',kind='Pod',metadata=dict(name=name, namespace=NS, labels=dict(app=app)),
                spec=dict(nodeName=node, automountServiceAccountToken=False, containers=[c]))

def snapshot(label):
    k(['get','pods','-o','wide'], label+'-pods')
    k(['get','service','web','-o','json'],label+'-service')
    k(['get','endpointslices','-l','kubernetes.io/service-name=web','-o','json'],label+'-endpointslices')
    k(['get','networkpolicies','-o','json'],label+'-policies')

def probe(stage, target, url):
    result = k(['exec','client','--','curl','--noproxy','*','--connect-timeout','2','--max-time','3',
                '-sS','-o','/dev/null','-w','http=%{http_code} remote=%{remote_ip} connect=%{time_connect}\n',url],
               stage+'-'+target, check=False)
    matrix.append(dict(stage=stage,target=target,url=url,exit=result['exit'],
                       stdout=result['stdout'].strip(),stderr=result['stderr'].strip(),started=result['started']))
    (HERE / 'matrix.json').write_text(json.dumps(matrix,ensure_ascii=False,indent=2)+'\n')
    return result

created = False
try:
    present = run(['kubectl','get','namespace',NS,'--ignore-not-found','-o','name'],'namespace-preflight')
    if present['stdout'].strip(): raise RuntimeError('Refusing existing namespace')
    run(['kubectl','get','nodes','-o','wide'],'environment-nodes')
    run(['kubectl','get','ippools.crd.projectcalico.org','-o','json'],'environment-pools')
    run(['kubectl','get','ds','calico-node','-n','kube-system','-o','jsonpath={.spec.template.spec.containers[0].image}'],'environment-calico-image')
    run(['kubectl','create','namespace',NS],'create-namespace'); created = True
    docs = [pod('client','k8s-worker1','client','curlimages/curl:8.11.1',['sh','-c','sleep 3600']),
            pod('local','k8s-worker1','local','nginx:1.25.1-alpine'),
            pod('remote','k8s-worker2','web','nginx:1.25.1-alpine'),
            dict(apiVersion='v1',kind='Service',metadata=dict(name='web',namespace=NS),
                 spec=dict(selector=dict(app='web'),ports=[dict(name='http',port=80,targetPort=80)]))]
    manifest = dict(apiVersion='v1',kind='List',items=docs)
    text = json.dumps(manifest,indent=2)+'\n'; (HERE/'resources.json').write_text(text)
    k(['apply','-f','-'],'apply-resources',stdin=text)
    k(['wait','--for=condition=Ready','pod','--all','--timeout=120s'],'wait-ready')
    pods=json.loads(k(['get','pods','-o','json'],'pods-json')['stdout'])
    ips={p['metadata']['name']:p['status']['podIP'] for p in pods['items']}
    svc=json.loads(k(['get','svc','web','-o','json'],'service-initial')['stdout'])['spec']['clusterIP']
    facts=dict(ips=ips,clusterIP=svc,dns=f'web.{NS}.svc.cluster.local')
    (HERE/'facts.json').write_text(json.dumps(facts,indent=2)+'\n')
    # Both nodes have a running server before injecting faults.
    urls={'local-pod':f"http://{ips['local']}/",'remote-pod':f"http://{ips['remote']}/",
          'cluster-ip':f'http://{svc}/','dns':f'http://web.{NS}.svc.cluster.local/'}
    time.sleep(2)
    snapshot('baseline')
    for target,url in urls.items(): assert probe('baseline',target,url)['exit']==0
    k(['exec','remote','--','sh','-c','netstat -lnt; wget -q -O /dev/null http://127.0.0.1/ && echo localhost_http_ok'], 'remote-listen-localhost')
    # Case 1: only the Service targetPort is wrong.
    patch=json.dumps({'spec':{'ports':[{'name':'http','port':80,'targetPort':8081}]}})
    k(['patch','svc','web','--type=merge','-p',patch],'fault-target-port')
    time.sleep(2); snapshot('wrong-target-port')
    for target,url in urls.items(): probe('wrong-target-port',target,url)
    patch=json.dumps({'spec':{'ports':[{'name':'http','port':80,'targetPort':80}]}})
    k(['patch','svc','web','--type=merge','-p',patch],'restore-target-port')
    time.sleep(2); assert probe('port-restored','cluster-ip',urls['cluster-ip'])['exit']==0
    # Case 2: selector does not select any Pod.
    k(['patch','svc','web','--type=merge','-p',json.dumps({'spec':{'selector':{'app':'does-not-exist'}}})], 'fault-selector')
    time.sleep(2); snapshot('no-endpoint')
    for target,url in urls.items(): probe('no-endpoint',target,url)
    k(['patch','svc','web','--type=merge','-p',json.dumps({'spec':{'selector':{'app':'web'}}})], 'restore-selector')
    time.sleep(2); assert probe('selector-restored','cluster-ip',urls['cluster-ip'])['exit']==0
    # Case 3: ingress denied for the remote server only.
    policy=dict(apiVersion='networking.k8s.io/v1',kind='NetworkPolicy',metadata=dict(name='deny-web',namespace=NS),
                spec=dict(podSelector=dict(matchLabels=dict(app='web')),policyTypes=['Ingress'],ingress=[]))
    policytext=json.dumps(policy,indent=2)+'\n';(HERE/'deny-web.json').write_text(policytext)
    k(['apply','-f','-'],'fault-ingress-deny',stdin=policytext)
    time.sleep(2); snapshot('ingress-denied')
    for target,url in urls.items(): probe('ingress-denied',target,url)
    k(['delete','networkpolicy','deny-web'],'restore-policy')
    time.sleep(2)
    for target,url in urls.items(): assert probe('policy-restored',target,url)['exit']==0
    # Case 4: bad hostname without changing cluster DNS.
    probe('wrong-name','dns',f'http://web-typo.{NS}.svc.cluster.local/')
    assert probe('name-corrected','dns',urls['dns'])['exit']==0
    # Read-only route lookup on the destination host: /32 wins over its /26.
    routeout=run(['ssh','worker2','--','ip','-4','route','show'],'worker2-routes')['stdout']
    remote=ipaddress.ip_address(ips['remote'])
    ownblock=next(line.split()[1] for line in routeout.splitlines() if line.startswith('blackhole ') and remote in ipaddress.ip_network(line.split()[1]))
    empty=next(str(ip) for ip in reversed(list(ipaddress.ip_network(ownblock).hosts()))
               if not any(line.startswith(str(ip)+' ') or line.startswith(str(ip)+'/32 ') for line in routeout.splitlines())
               and str(ip) not in ips.values())
    run(['ssh','worker2','--','ip','-4','route','get',ips['remote']],'route-existing-pod')
    run(['ssh','worker2','--','ip','-4','route','get',empty],'route-no-specific-host',check=False)
    facts.update(ownBlock=ownblock,withoutSpecificHostRoute=empty)
    (HERE/'facts.json').write_text(json.dumps(facts,indent=2)+'\n')
    snapshot('final-restored')
finally:
    if created:
        run(['kubectl','delete','namespace',NS,'--wait=true','--timeout=90s'],'cleanup-namespace',check=False)
        run(['kubectl','get','namespace',NS,'--ignore-not-found','-o','name'],'cleanup-verification')
    run(['kubectl','get','nodes'],'post-nodes')

print(json.dumps(dict(facts=facts,matrix=matrix),ensure_ascii=False,indent=2))
