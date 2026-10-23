"""Dependency-free local checkout service and durable OTLP/HTTP capture gateway.
The app creates valid OTLP JSON directly to isolate Collector queues from SDK queues.
"""
import json, os, secrets, sqlite3, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from urllib.parse import urlparse, parse_qs
ROLE = os.environ.get('ROLE', 'app')
LOCK = threading.RLock()
STATE = {'mode': 'online', 'refusals': 0, 'ack_lost': set()}
if ROLE == 'backend':
    DB = sqlite3.connect('/data/capture.sqlite', check_same_thread=False)
    DB.execute('PRAGMA journal_mode=WAL')
    DB.execute('PRAGMA synchronous=FULL')
    DB.execute('CREATE TABLE IF NOT EXISTS receipts (run TEXT, trace TEXT, span TEXT, received REAL)')
    DB.commit()

def post(url, payload, timeout=5):
    req = Request(url, json.dumps(payload).encode(), {'Content-Type': 'application/json'})
    try:
        with urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read() or b'{}')
    except HTTPError as e:
        return e.code, json.loads(e.read() or b'{}')

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass
    def reply(self, status, obj):
        raw = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header('Content-Type','application/json')
        self.send_header('Content-Length', str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)
    def do_GET(self):
        if self.path == '/health': return self.reply(200, {'role':ROLE})
        if ROLE == 'backend' and self.path == '/records':
            with LOCK:
                rows = DB.execute('SELECT run, trace, span, received FROM receipts').fetchall()
                return self.reply(200, {'mode':STATE['mode'],'refusals':STATE['refusals'], 'receipts':rows})
        self.reply(404,{})
    def do_POST(self):
        payload = json.loads(self.rfile.read(int(self.headers.get('Content-Length','0'))) or b'{}')
        if ROLE == 'app' and self.path == '/orders':
            run, mode, count = payload['run'], payload['mode'], payload['count']
            if mode not in ('memory','disk') or not 0 < count <= 300: return self.reply(400,{})
            generated, accepted, rejected = [], [], []
            for i in range(count):
                trace, span = secrets.token_hex(16), secrets.token_hex(8)
                start = time.time_ns()
                attrs = [{'key':k, 'value':{'stringValue':v}} for k,v in {'lab.run':run,'lab.mode':mode,'order.id':f'local-{i}'}.items()]
                data = {'resourceSpans':[{'resource':{'attributes':[{'key':'service.name','value':{'stringValue':'checkout-loss-lab'}}]},'scopeSpans':[{'scope':{'name':'local.manual-otlp'},'spans':[{'traceId':trace,'spanId':span,'name':'POST /orders','kind':2,'startTimeUnixNano':str(start),'endTimeUnixNano':str(start+1000000),'attributes':attrs,'status':{'code':1}}]}]}]}
                status, result = post(f'http://{mode}:4318/v1/traces',data)
                row = {'trace':trace,'span':span,'http':status,'response':result}
                generated.append(row)
                partial = result.get('partialSuccess',{}).get('rejectedSpans',0)
                (accepted if status == 200 and not int(partial) else rejected).append(row)
            print(json.dumps({'event':'orders','run':run,'generated':count,'collector_accepted':len(accepted),'rejected':len(rejected)}),flush=True)
            return self.reply(200,{'run':run,'generated':generated,'accepted':accepted,'rejected':rejected})
        if ROLE == 'backend' and self.path == '/mode':
            with LOCK: STATE['mode']=payload['mode']
            return self.reply(200,{'mode':STATE['mode']})
        if ROLE == 'backend' and self.path == '/v1/traces':
            with LOCK:
                if STATE['mode']=='offline':
                    STATE['refusals']+=1
                    return self.reply(503,{'code':14,'message':'local outage injection'})
                ids=[]
                for resource in payload.get('resourceSpans',[]):
                    for scope in resource.get('scopeSpans',[]):
                        for span in scope.get('spans',[]):
                            attrs={a['key']:a['value'].get('stringValue') for a in span.get('attributes',[])}
                            ids.append((attrs['lab.run'],span['traceId'],span['spanId']))
                DB.executemany('INSERT INTO receipts VALUES (?,?,?,?)',[(*row,time.time()) for row in ids])
                DB.commit()
                # Forward the same real spans to Tempo, after the capture commit.
                try:
                    status, result = post('http://tempo:4318/v1/traces',payload)
                except Exception as e:
                    return self.reply(503,{'message':type(e).__name__})
                if status != 200: return self.reply(503,{'message':'Tempo rejected'})
                if STATE['mode']=='lose-ack-once' and ids[0][1] not in STATE['ack_lost']:
                    STATE['ack_lost'].add(ids[0][1])
                    print(json.dumps({'event':'persisted_but_ack_failed','run':ids[0][0]}),flush=True)
                    return self.reply(503,{'code':14,'message':'simulated lost success acknowledgement'})
                return self.reply(200,{})
        self.reply(404,{})

ThreadingHTTPServer(('0.0.0.0',8080),Handler).serve_forever()
