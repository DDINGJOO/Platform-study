#!/usr/bin/env python3
"""Isolated namespace + temporary node HTTP listener; no NAT/config changes."""
from pathlib import Path
import datetime
import json
import shlex
import subprocess
import time

BASE = Path(__file__).resolve().parent
LAB = '/Users/dding/orca/workspaces/k8s/tang/lab'
NS = 'calico-blog-55'
PORT = 18555
records = []
processes = []
created = False

def call(args, name, stdin=None, check=True):
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    result = subprocess.run([LAB, *args], input=stdin, text=True, capture_output=True, timeout=90)
    records.append({'time': started, 'command': shlex.join([LAB, *args]), 'exit_code': result.returncode,
                    'stdout': result.stdout, 'stderr': result.stderr})
    (BASE / (name + '.txt')).write_text('$ ' + shlex.join([LAB, *args]) + '\n' + result.stdout + result.stderr)
    (BASE / 'commands.json').write_text(json.dumps(records, ensure_ascii=False, indent=2))
    if check and result.returncode:
        raise RuntimeError(name + ': ' + result.stderr)
    return result

def background(args, filename):
    out = open(BASE / filename, 'wb')
    err = open(BASE / (filename + '.stderr.txt'), 'wb')
    p = subprocess.Popen([LAB, *args], stdout=out, stderr=err)
    processes.append((p, out, err, args))
    return p

def pod(name, host=False):
    return {'apiVersion': 'v1', 'kind': 'Pod', 'metadata': {'name': name, 'namespace': NS},
            'spec': {'nodeName': 'k8s-worker1', 'hostNetwork': host,
                     'automountServiceAccountToken': False, 'restartPolicy': 'Never',
                     'containers': [{'name': 'curl', 'image': 'curlimages/curl:8.11.1',
                         'imagePullPolicy': 'Never', 'command': ['sh', '-c', 'sleep 300'],
                         'resources': {'requests': {'cpu': '1m', 'memory': '4Mi'},
                                       'limits': {'cpu': '50m', 'memory': '24Mi'}}}]}}

try:
    pre = call(['kubectl', 'get', 'namespace', NS, '--ignore-not-found', '-o', 'name'], '00-preflight')
    if pre.stdout.strip():
        raise RuntimeError('Experiment namespace already exists; refusing to reuse')
    call(['kubectl', 'create', 'namespace', NS], '01-namespace')
    created = True
    manifest = {'apiVersion': 'v1', 'kind': 'List', 'items': [pod('pod-client'), pod('host-client', True)]}
    (BASE / 'pods.json').write_text(json.dumps(manifest, indent=2))
    call(['kubectl', 'apply', '-f', '-'], '02-pods', json.dumps(manifest))
    call(['kubectl', '-n', NS, 'wait', '--for=condition=Ready', 'pod', '--all', '--timeout=60s'], '03-ready')
    pods = json.loads(call(['kubectl', '-n', NS, 'get', 'pods', '-o', 'json'], '04-pods').stdout)
    pod_ip = next(x['status']['podIP'] for x in pods['items'] if x['metadata']['name'] == 'pod-client')
    route = call(['ssh', 'worker1', '--', 'ip', 'route', 'get', pod_ip], '05-pod-route').stdout
    cali = route.split('dev ')[1].split()[0]
    call(['kubectl', 'get', 'ippool', '-o', 'yaml'], '06-pool')
    call(['ssh', 'worker1', '--', 'sudo', 'iptables', '-t', 'nat', '-nvL', 'cali-nat-outgoing', '--line-numbers'], '07-nat-before')
    call(['ssh', 'worker1', '--', 'sudo', 'sh', '-c', 'iptables-save -t nat | grep -E "cali-(nat-outgoing|POSTROUTING)|POSTROUTING.*cali"'], '08-nat-rules')
    call(['ssh', 'worker1', '--', 'ip', 'route', 'get', '192.168.104.4'], '09-route')
    server = '''import http.server,json,datetime
class Handler(http.server.BaseHTTPRequestHandler):
 def do_GET(self):
  result={"time":datetime.datetime.now(datetime.timezone.utc).isoformat(),"client_ip":self.client_address[0],"client_port":self.client_address[1],"server_ip":self.server.server_address[0],"path":self.path}
  print(json.dumps(result),flush=True)
  body=(json.dumps(result)+"\\n").encode();self.send_response(200);self.send_header("Content-Length",str(len(body)));self.end_headers();self.wfile.write(body)
 def log_message(self,*args):pass
print("LISTEN 192.168.104.4:18555",flush=True)
http.server.HTTPServer(("192.168.104.4",18555),Handler).serve_forever()
'''
    (BASE / 'receiver.py').write_text(server)
    background(['ssh', 'worker2', '--', 'timeout', '25', 'python3', '-u', '-c', server], 'receiver.txt')
    for node, iface, name in [('worker1', cali, 'cali'), ('worker1', 'eth0', 'sender-eth0'), ('worker2', 'eth0', 'receiver-eth0')]:
        background(['ssh', node, '--', 'sudo', 'timeout', '16', 'tcpdump', '-U', '-n', '-i', iface, '-s', '0', '-w', '-',
                    'tcp and host 192.168.104.4 and port 18555'], name + '.pcap')
    time.sleep(2)
    call(['kubectl', '-n', NS, 'exec', 'pod-client', '--', 'curl', '--noproxy', '*', '--max-time', '5',
          '--local-port', '45555', '-sS', 'http://192.168.104.4:18555/pod'], '10-pod-request')
    call(['kubectl', '-n', NS, 'exec', 'host-client', '--', 'curl', '--noproxy', '*', '--max-time', '5',
          '--local-port', '45556', '-sS', 'http://192.168.104.4:18555/hostNetwork'], '11-host-request')
    call(['ssh', 'worker1', '--', 'curl', '--noproxy', '*', '--max-time', '5', '--local-port', '45557', '-sS',
          'http://192.168.104.4:18555/node'], '12-node-request')
    ct = (BASE / 'conntrack-read.py').read_text()
    call(['ssh', 'worker1', '--', 'sudo', 'python3', '-c', ct, str(PORT)], '13-conntrack')
    call(['ssh', 'worker1', '--', 'sudo', 'iptables', '-t', 'nat', '-nvL', 'cali-nat-outgoing', '--line-numbers'], '14-nat-after')
    for p, out, err, args in processes:
        p.wait(timeout=30)
        out.close();err.close()
    (BASE / 'background-results.json').write_text(json.dumps([{'command': shlex.join([LAB, *args]), 'exit_code': p.returncode} for p,_,_,args in processes],indent=2))
    for stem in ['cali', 'sender-eth0', 'receiver-eth0']:
        result = subprocess.run(['tcpdump', '-nn', '-tttt', '-r', str(BASE / (stem + '.pcap'))], text=True,capture_output=True)
        (BASE / (stem + '.txt')).write_text(result.stdout + result.stderr)
    (BASE / 'result.json').write_text(json.dumps({'pod_ip':pod_ip,'cali':cali,'receiver':'192.168.104.4:18555'},indent=2))
finally:
    for p,out,err,args in processes:
        if p.poll() is None:
            try:p.wait(timeout=30)
            except subprocess.TimeoutExpired:p.terminate();p.wait(timeout=5)
        out.close();err.close()
    if created:
        call(['kubectl', 'delete', 'namespace', NS, '--wait=true', '--timeout=60s'], '90-cleanup', check=False)
        call(['kubectl', 'get', 'namespace', NS, '--ignore-not-found', '-o', 'name'], '91-cleanup-check', check=False)
        call(['ssh', 'worker2', '--', 'ss', '-lnt', 'sport', '=', ':18555'], '92-listener-check', check=False)
