#!/usr/bin/env python3
"""Isolated NetworkPolicy experiment; creates/deletes only calico-blog-54."""
import base64,datetime,json,pathlib,subprocess,time,shlex
D=pathlib.Path(__file__).resolve().parent
LAB='/Users/dding/orca/workspaces/k8s/tang/lab';NS='calico-blog-54'
records=[];results=[];keep=None;cap=None

def run(args,label,stdin=None,check=True,timeout=60):
 t=datetime.datetime.now().astimezone().isoformat();p=subprocess.run([LAB]+args,input=stdin,text=True,capture_output=True,timeout=timeout)
 records.append(dict(time=t,label=label,command=shlex.join([LAB]+args),stdin=stdin,exit=p.returncode,stdout=p.stdout,stderr=p.stderr))
 (D/'commands.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
 if check and p.returncode:raise RuntimeError(f'{label}: {p.stderr}')
 return p.stdout

def k(args,label,**kw):return run(['kubectl','-n',NS]+args,label,**kw)
def apply(obj,label):
 (D/(label+'.json')).write_text(json.dumps(obj,indent=2)+'\n')
 return k(['apply','-f','-'],label,stdin=json.dumps(obj))
def pol(name,selector,types,**kw):return {'apiVersion':'networking.k8s.io/v1','kind':'NetworkPolicy','metadata':{'name':name,'namespace':NS},'spec':{'podSelector':{'matchLabels':selector},'policyTypes':types,**kw}}
def probe(label,client,ip,expect):
 out=k(['exec',client,'--','wget','-q','-T','2','-O','-',f'http://{ip}/'],label,check=False)
 rc=records[-1]['exit'];results.append({'phase':label,'client':client,'target':ip,'exit':rc,'expected_success':expect,'observed_success':rc==0})
 assert (rc==0)==expect,(label,rc,records[-1]['stderr'])
 return out

def dns(label,pid,proto,expect):
 code='''import socket,struct,json,time
host="server-svc.calico-blog-54.svc.cluster.local"
q=struct.pack("!HHHHHH",21554,256,1,0,0,0)+b"".join(bytes([len(x)])+x.encode() for x in host.split("."))+b"\\0"+struct.pack("!HH",1,1)
s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM if PROTO=="udp" else socket.SOCK_STREAM);s.settimeout(2)
try:
 if PROTO=="udp": s.sendto(q,("10.96.0.10",53));r=s.recv(4096)
 else:
  s.connect(("10.96.0.10",53));s.sendall(struct.pack("!H",len(q))+q);r=s.recv(4096)[2:]
 print(json.dumps({"protocol":PROTO,"rcode":r[3]&15,"answers":struct.unpack("!H",r[6:8])[0],"result":"reply"}))
except Exception as e:
 print(json.dumps({"protocol":PROTO,"result":type(e).__name__}));raise SystemExit(2)
'''.replace('PROTO',repr(proto))
 out=run(['ssh','worker1','--','sudo','nsenter','-t',str(pid),'-n','python3','-c',code],label,check=False)
 rc=records[-1]['exit'];results.append({'phase':label,'protocol':proto,'exit':rc,'expected_success':expect,'observed_success':rc==0})
 assert (rc==0)==expect,(label,rc,out)

try:
 existing=run(['kubectl','get','namespace',NS], 'namespace-precheck',check=False)
 if records[-1]['exit']==0:raise RuntimeError('namespace already exists; refusing ownership')
 run(['kubectl','create','namespace',NS],'create-namespace')
 pods=[]
 for name,node,role in [('client-a','k8s-worker1','a'),('client-b','k8s-worker1','b'),('server','k8s-worker2','server')]:
  c={'name':name,'image':'nginx:1.25.1-alpine' if role=='server' else 'busybox:1.36.1','imagePullPolicy':'Never','resources':{'requests':{'cpu':'5m','memory':'8Mi'},'limits':{'cpu':'100m','memory':'64Mi'}}}
  if role!='server':c['command']=['sh','-c','sleep 900']
  pods.append({'apiVersion':'v1','kind':'Pod','metadata':{'name':name,'namespace':NS,'labels':{'role':role}},'spec':{'nodeName':node,'containers':[c]}})
 apply({'apiVersion':'v1','kind':'List','items':pods},'pods')
 k(['wait','--for=condition=Ready','pod','--all','--timeout=100s'],'pods-ready',timeout=115)
 state=json.loads(k(['get','pods','-o','json'],'placement'));by={p['metadata']['name']:p for p in state['items']};sip=by['server']['status']['podIP'];cip=by['client-a']['status']['podIP']
 cid=by['client-a']['status']['containerStatuses'][0]['containerID'].split('://')[1]
 inspect=json.loads(run(['ssh','worker1','--','sudo','crictl','inspect',cid],'client-runtime'));pid=inspect['info']['pid']
 apply({'apiVersion':'v1','kind':'Service','metadata':{'name':'server-svc','namespace':NS},'spec':{'selector':{'role':'server'},'ports':[{'port':80}]}},'service')
 probe('baseline-a','client-a',sip,True);probe('baseline-b','client-b',sip,True)
 dns('baseline-dns-udp',pid,'udp',True);dns('baseline-dns-tcp',pid,'tcp',True)
 keepcode='''import http.client,json,time
c=http.client.HTTPConnection(SERVER,80,timeout=3)
for i in range(12):
 try:
  c.request("GET","/");r=c.getresponse();r.read();print(json.dumps({"i":i,"time":time.time(),"status":r.status,"local":c.sock.getsockname(),"remote":c.sock.getpeername()}),flush=True)
 except Exception as e:print(json.dumps({"i":i,"error":str(e)}),flush=True);break
 time.sleep(0.6)
'''.replace('SERVER',repr(sip))
 capcmd=[LAB,'ssh','worker1','--','sudo','timeout','12','tcpdump','-i','any','-nn','-U','-w','/tmp/cb54-keepalive.pcap',f'host {cip} and host {sip} and tcp port 80']
 cap=subprocess.Popen(capcmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
 time.sleep(.5)
 keepcmd=[LAB,'ssh','worker1','--','sudo','nsenter','-t',str(pid),'-n','python3','-u','-c',keepcode]
 keep=subprocess.Popen(keepcmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
 first=keep.stdout.readline();assert '"status": 200' in first,first
 apply(pol('deny-server-ingress',{'role':'server'},['Ingress'],ingress=[]),'deny-server-ingress');time.sleep(1)
 probe('deny-new-a','client-a',sip,False);probe('deny-new-b','client-b',sip,False)
 kout,kerr=keep.communicate(timeout=20);(D/'keepalive.jsonl').write_text(first+kout);(D/'keepalive-stderr.txt').write_text(kerr)
 assert keep.returncode==0 and len((first+kout).splitlines())==12 and all(json.loads(x).get('status')==200 for x in (first+kout).splitlines())
 records.append({'label':'persistent-http-connection','command':shlex.join(keepcmd),'exit':keep.returncode,'stdout':first+kout,'stderr':kerr})
 cout,cerr=cap.communicate(timeout=15);(D/'capture-stderr.txt').write_text(cerr)
 raw=run(['ssh','worker1','--','sudo','base64','-w0','/tmp/cb54-keepalive.pcap'],'read-pcap');(D/'keepalive.pcap').write_bytes(base64.b64decode(raw))
 run(['ssh','worker1','--','sudo','rm','-f','/tmp/cb54-keepalive.pcap'],'remove-node-pcap')
 allow=lambda role:pol('allow-'+role,{'role':'server'},['Ingress'],ingress=[{'from':[{'podSelector':{'matchLabels':{'role':role}}}],'ports':[{'protocol':'TCP','port':80}]}])
 apply(allow('a'),'allow-a');time.sleep(1);probe('allow-a-success','client-a',sip,True);probe('allow-a-b-still-denied','client-b',sip,False)
 apply(allow('b'),'allow-b');time.sleep(1);probe('allow-b-additive','client-b',sip,True)
 apply(pol('deny-a-egress',{'role':'a'},['Egress'],egress=[]),'deny-a-egress');time.sleep(1);probe('ingress-allowed-egress-denied','client-a',sip,False)
 apply(pol('a-to-server',{'role':'a'},['Egress'],egress=[{'to':[{'podSelector':{'matchLabels':{'role':'server'}}}],'ports':[{'protocol':'TCP','port':80}]}]),'a-to-server');time.sleep(1)
 probe('both-directions-allowed','client-a',sip,True);dns('egress-no-dns-udp',pid,'udp',False);dns('egress-no-dns-tcp',pid,'tcp',False)
 dnsto=[{'namespaceSelector':{'matchLabels':{'kubernetes.io/metadata.name':'kube-system'}},'podSelector':{'matchLabels':{'k8s-app':'kube-dns'}}}]
 apply(pol('a-dns-udp',{'role':'a'},['Egress'],egress=[{'to':dnsto,'ports':[{'protocol':'UDP','port':53}]}]),'a-dns-udp');time.sleep(1)
 dns('allow-dns-udp',pid,'udp',True);dns('only-udp-tcp-denied',pid,'tcp',False)
 apply(pol('a-dns-tcp',{'role':'a'},['Egress'],egress=[{'to':dnsto,'ports':[{'protocol':'TCP','port':53}]}]),'a-dns-tcp');time.sleep(1)
 dns('allow-dns-tcp',pid,'tcp',True);probe('hostname-http-success','client-a','server-svc.calico-blog-54.svc.cluster.local',True)
 k(['get','networkpolicy','-o','yaml'],'final-policies')
 run(['ssh','worker1','--','sudo','iptables-save','-c'],'worker1-rules')
 run(['ssh','worker2','--','sudo','iptables-save','-c'],'worker2-rules')
 run(['kubectl','get','felixconfiguration','default','-o','json'],'felix-config')
 run(['ssh','worker1','--','sudo','tcpdump','-nn','-r','/dev/stdin'], 'pcap-placeholder',check=False,timeout=2) if False else None
 (D/'results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(results,ensure_ascii=False,indent=2))
finally:
 if keep and keep.poll() is None:keep.terminate();keep.wait(timeout=5)
 if cap and cap.poll() is None:cap.terminate();cap.wait(timeout=5)
 # Namespace was created by this run unless precheck failed before create.
 if any(x['label']=='create-namespace' and x['exit']==0 for x in records):
  run(['kubectl','delete','namespace',NS,'--wait=true','--timeout=90s'],'cleanup',timeout=100,check=False)
  run(['kubectl','get','namespace',NS],'cleanup-check',check=False)
 (D/'commands.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
