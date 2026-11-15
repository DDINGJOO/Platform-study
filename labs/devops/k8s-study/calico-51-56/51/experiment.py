#!/usr/bin/env python3
import subprocess, json, datetime, shlex
from pathlib import Path

D = Path(__file__).resolve().parent
LAB = '/Users/dding/orca/workspaces/k8s/tang/lab'
records = []

def run(name, args, stdin=None, check=True):
    at = datetime.datetime.now().astimezone().isoformat()
    p = subprocess.run([LAB] + args, input=stdin, text=True, capture_output=True, timeout=150)
    o = dict(time=at, command=shlex.join([LAB] + args), returncode=p.returncode, stdout=p.stdout, stderr=p.stderr)
    records.append(o)
    (D / (name + '.txt')).write_text('$ ' + o['command'] + '\n' + p.stdout + p.stderr)
    (D / 'commands.json').write_text(json.dumps(records, ensure_ascii=False, indent=2) + '\n')
    if check and p.returncode:
        raise RuntimeError(name + ': ' + p.stderr)
    return p.stdout

def kub(name, *args, **kw):
    return run(name, ['kubectl'] + list(args), **kw)

def ssh(name, *args, **kw):
    return run(name, ['ssh', 'worker1', '--'] + list(args), **kw)

ns = 'calico-blog-51'
pods = []
for name, host, count in [('pair', False, 2), ('host', True, 1)]:
    pods.append({'apiVersion': 'v1', 'kind': 'Pod', 'metadata': {'name': name, 'namespace': ns, 'labels': {'experiment': ns}}, 'spec': {'nodeName': 'k8s-worker1', 'hostNetwork': host, 'automountServiceAccountToken': False, 'terminationGracePeriodSeconds': 1, 'containers': [{'name': 'app' + str(i), 'image': 'busybox:1.36.1', 'imagePullPolicy': 'Never', 'command': ['sleep', '3600'], 'resources': {'requests': {'cpu': '1m', 'memory': '4Mi'}, 'limits': {'cpu': '20m', 'memory': '16Mi'}}} for i in range(count)]}})
manifest = {'apiVersion': 'v1', 'kind': 'List', 'items': [{'apiVersion': 'v1', 'kind': 'Namespace', 'metadata': {'name': ns}}] + pods}
(D / 'resources.json').write_text(json.dumps(manifest, indent=2) + '\n')
try:
    before = json.loads(ssh('01-host-links-before', 'ip', '-j', 'link', 'show'))
    kub('02-create', 'apply', '-f', '-', stdin=json.dumps(manifest))
    kub('03-wait', 'wait', '-n', ns, '--for=condition=Ready', 'pod', '--all', '--timeout=90s')
    po = json.loads(kub('04-pods', 'get', 'pods', '-n', ns, '-o', 'json'))
    summary = [{'name': p['metadata']['name'], 'ip': p['status'].get('podIP'), 'node': p['spec']['nodeName'], 'hostNetwork': p['spec'].get('hostNetwork', False)} for p in po['items']]
    (D / 'pod-summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    runtime = json.loads(ssh('05-sandboxes', 'sudo', 'crictl', 'pods', '--namespace', ns, '-o', 'json'))['items']
    mapping = []
    for p in runtime:
        name, sid = p['metadata']['name'], p['id']
        cmd = 'crictl inspectp ' + shlex.quote(sid) + ' | python3 -c ' + shlex.quote('import json,sys; x=json.load(sys.stdin); print(x["info"]["pid"])')
        pid = int(ssh('06-' + name + '-sandbox-pid', 'sudo', 'sh', '-c', cmd).strip())
        netns = ssh('07-' + name + '-netns', 'sudo', 'readlink', '/proc/' + str(pid) + '/ns/net').strip()
        links = json.loads(ssh('08-' + name + '-links', 'sudo', 'nsenter', '-t', str(pid), '-n', 'ip', '-j', '-d', 'link', 'show'))
        addrs = json.loads(ssh('09-' + name + '-addresses', 'sudo', 'nsenter', '-t', str(pid), '-n', 'ip', '-j', 'addr', 'show'))
        ssh('10-' + name + '-routes', 'sudo', 'nsenter', '-t', str(pid), '-n', 'ip', 'route', 'show')
        ssh('11-' + name + '-neighbours', 'sudo', 'nsenter', '-t', str(pid), '-n', 'ip', 'neigh', 'show')
        containers = json.loads(ssh('12-' + name + '-containers', 'sudo', 'crictl', 'ps', '--pod', sid, '-o', 'json'))['containers']
        cs = []
        for c in containers:
            cmd = 'crictl inspect ' + shlex.quote(c['id']) + ' | python3 -c ' + shlex.quote('import json,sys; x=json.load(sys.stdin); print(x["info"]["pid"])')
            cpid = int(ssh('13-' + name + '-' + c['metadata']['name'] + '-pid', 'sudo', 'sh', '-c', cmd).strip())
            cns = ssh('14-' + name + '-' + c['metadata']['name'] + '-netns', 'sudo', 'readlink', '/proc/' + str(cpid) + '/ns/net').strip()
            cs.append(dict(name=c['metadata']['name'], pid=cpid, netns=cns))
        mapping.append(dict(pod=name, sandboxPid=pid, sandboxNetns=netns, containers=cs, links=links, addresses=addrs))
    hostns = ssh('15-host-netns', 'readlink', '/proc/self/ns/net').strip()
    after = json.loads(ssh('16-host-links-after', 'ip', '-j', '-d', 'link', 'show'))
    pair = next(x for x in mapping if x['pod'] == 'pair')
    eth = next(x for x in pair['links'] if x['ifname'] == 'eth0')
    peer = next(x for x in after if x['ifindex'] == eth['link_index'])
    assert peer['link_index'] == eth['ifindex'], (eth, peer)
    assert all(c['netns'] == pair['sandboxNetns'] for c in pair['containers'])
    host = next(x for x in mapping if x['pod'] == 'host')
    assert host['sandboxNetns'] == hostns
    pip = next(x['ip'] for x in summary if x['name'] == 'pair')
    ssh('17-peer-link', 'ip', '-d', 'link', 'show', 'dev', peer['ifname'])
    ssh('18-peer-statistics', 'sudo', 'ethtool', '-S', peer['ifname'])
    ssh('19-host-route', 'ip', 'route', 'get', pip)
    ssh('20-pod-route-proxyarp', 'sudo', 'sysctl', 'net.ipv4.conf.' + peer['ifname'] + '.proxy_arp', 'net.ipv4.conf.' + peer['ifname'] + '.forwarding')
    ssh('21-reach-pod', 'ping', '-c', '2', '-W', '2', pip)
    ssh('22-neighbours-after', 'sudo', 'nsenter', '-t', str(pair['sandboxPid']), '-n', 'ip', 'neigh', 'show')
    ssh('23-cni-selected-fields', 'sudo', 'python3', '-c', 'import json; x=json.load(open("/etc/cni/net.d/10-calico.conflist")); print(json.dumps({"cniVersion":x["cniVersion"],"plugins":[{"type":p["type"],"ipam":p.get("ipam",{})} for p in x["plugins"]]},indent=2))')
    result = dict(hostNetns=hostns, pods=mapping, peer=peer, podIP=pip, newHostLinks=[x['ifname'] for x in after if x['ifindex'] not in {y['ifindex'] for y in before}])
    (D / 'verified.json').write_text(json.dumps(result, indent=2) + '\n')
finally:
    kub('24-cleanup', 'delete', 'namespace', ns, '--ignore-not-found=true', '--wait=true', '--timeout=90s', check=False)
    kub('25-cleanup-check', 'get', 'namespace', ns, check=False)
    ssh('26-host-links-clean', 'ip', '-j', 'link', 'show')
print(json.dumps(dict(verified=(D / 'verified.json').exists(), records=len(records))))
