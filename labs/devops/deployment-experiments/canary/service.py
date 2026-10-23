"""Real local HTTP workload with an in-process cache and explicit injected delays.
Delay is a synthetic I/O simulation, not an external datastore or production trace.
"""
import json,os,threading,time
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlparse,parse_qs
ROLE=os.environ['ROLE'];VERSION=os.environ['VERSION']
REGRESSION_MS=float(os.environ.get('REGRESSION_MS','0'))
START=time.time();CACHE=set();LOCK=threading.Lock()
COUNT=0;TOTAL=0.;MISSES=0
class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def reply(self,body,content='application/json'):
        data=body.encode() if isinstance(body,str) else json.dumps(body).encode()
        self.send_response(200);self.send_header('Content-Type',content);self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
    def do_GET(self):
        global COUNT,TOTAL,MISSES
        p=urlparse(self.path)
        if p.path=='/health':return self.reply({'ready':True})
        if p.path=='/state':
            with LOCK:return self.reply({'role':ROLE,'version':VERSION,'regression_ms':REGRESSION_MS,'started_epoch':START,'uptime_seconds':time.time()-START,'cache_items':len(CACHE),'requests':COUNT,'cache_misses':MISSES})
        if p.path=='/work':
            key=int(parse_qs(p.query).get('key',['0'])[0])%128
            began=time.perf_counter()
            with LOCK:miss=key not in CACHE
            # Simulate higher I/O cost when the real in-memory cache has no entry.
            time.sleep((10+key%5+REGRESSION_MS+(65 if miss else 0))/1000)
            elapsed=time.perf_counter()-began
            with LOCK:
                CACHE.add(key);COUNT+=1;TOTAL+=elapsed;MISSES+=int(miss)
            return self.reply({'role':ROLE,'version':VERSION,'cache_miss':miss,'duration_ms':round(elapsed*1000,3)})
        if p.path=='/metrics':
            labels=f'role="{ROLE}",version="{VERSION}"'
            with LOCK:
                text=f'''# TYPE orders_duration_seconds_sum counter
orders_duration_seconds_sum{{{labels}}} {TOTAL}
# TYPE orders_duration_seconds_count counter
orders_duration_seconds_count{{{labels}}} {COUNT}
# TYPE orders_cache_misses_total counter
orders_cache_misses_total{{{labels}}} {MISSES}
# TYPE process_uptime_seconds gauge
process_uptime_seconds{{{labels}}} {time.time()-START}
# TYPE cache_entries gauge
cache_entries{{{labels}}} {len(CACHE)}
'''
            return self.reply(text,'text/plain; version=0.0.4')
        self.send_error(404)
ThreadingHTTPServer(('0.0.0.0',8080),Handler).serve_forever()
