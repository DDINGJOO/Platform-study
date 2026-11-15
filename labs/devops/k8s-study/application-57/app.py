"""One-process, memory-only HTTP app for the Kubernetes deployment capstone."""
import json
import os
import signal
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

START = time.monotonic()
VERSION = os.environ.get('APP_VERSION', 'v1')
READY_AFTER = float(os.environ.get('READY_AFTER_SECONDS', '8'))
LOCK = threading.Lock()
COUNT = 0
STOPPING = False

PAGE = '''<!doctype html><html lang="ko"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>배포 확인 보드</title><style>
body{font:17px/1.65 system-ui,sans-serif;background:#fdfaf3;color:#303e46;margin:0;padding:32px 18px}
main{max-width:780px;margin:auto}h1{font-size:30px}small{color:#66757a}
section{background:white;border:1px solid #d7dfdc;border-radius:16px;padding:20px;margin:18px 0}
dl{display:grid;grid-template-columns:110px 1fr;gap:12px;margin:0}dt{color:#66757a}dd{margin:0;overflow-wrap:anywhere}
button{background:#285c4e;color:white;border:0;border-radius:9px;padding:12px 18px;font-size:16px;cursor:pointer}
pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:13px}#status{color:#285c4e}
</style><main><small>Kubernetes application capstone</small><h1>배포 확인 보드</h1>
<p>지금 요청을 처리한 앱의 버전과 파드를 확인해요. 2초마다 새 HTTP 요청을 보내요.</p>
<section><strong id="status">요청 중</strong><dl id="facts"></dl></section>
<button id="refresh">지금 요청하기</button><section><strong>마지막 응답</strong><pre id="raw"></pre></section>
<small>요청 수는 이 프로세스의 메모리에만 있어요. 프로세스나 파드가 바뀌면 초기화돼요.<br>
이 화면은 학습용 상태 확인 앱이에요. 응답에는 실습 파드의 주소가 포함돼요.</small></main>
<script>
const fields={version:'앱 버전',pod:'파드',node:'노드',pod_ip:'파드 IP',requests:'요청 수',uptime_seconds:'실행 초',request_id:'요청 ID'};
async function refresh(){const id='browser-'+Date.now().toString(36)+'-'+Math.random().toString(36).slice(2);try{const r=await fetch('/api/info',{cache:'no-store',headers:{'X-Request-ID':id},signal:AbortSignal.timeout(3000)});if(!r.ok)throw Error('HTTP '+r.status);const v=await r.json();document.querySelector('#status').textContent='HTTP '+r.status+' · '+new Date().toLocaleTimeString();const dl=document.querySelector('#facts');dl.replaceChildren();for(const [key,title]of Object.entries(fields)){const dt=document.createElement('dt'),dd=document.createElement('dd');dt.textContent=title;dd.textContent=v[key];dl.append(dt,dd)}document.querySelector('#raw').textContent=JSON.stringify(v,null,2)}catch(e){document.querySelector('#status').textContent='요청 실패 · '+e.message}}
document.querySelector('#refresh').onclick=refresh;refresh();setInterval(refresh,2000);
</script></html>'''


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        global COUNT
        path = urlparse(self.path).path
        request_id = self.headers.get('X-Request-ID', '-')[:128]
        ready = not STOPPING and time.monotonic() - START >= READY_AFTER and not os.path.exists('/tmp/not-ready')
        status, kind = 200, 'application/json; charset=utf-8'
        if path == '/healthz':
            body = {'healthy': True}
        elif path == '/readyz':
            status = 200 if ready else 503
            body = {'ready': ready, 'version': VERSION}
        elif path == '/api/info':
            with LOCK:
                COUNT += 1
                count = COUNT
            body = {'version': VERSION, 'pod': os.environ.get('POD_NAME'),
                    'node': os.environ.get('NODE_NAME'), 'pod_ip': os.environ.get('POD_IP'),
                    'requests': count, 'uptime_seconds': round(time.monotonic() - START, 3),
                    'request_id': request_id}
        elif path == '/':
            kind, body = 'text/html; charset=utf-8', PAGE
        else:
            status, body = 404, {'error': 'not found'}
        data = (body if isinstance(body, str) else json.dumps(body)).encode()
        self.send_response(status)
        self.send_header('Content-Type', kind)
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)
        if path in ('/', '/api/info'):
            print(json.dumps({'time': datetime.now(timezone.utc).isoformat(), 'path': path,
                              'status': status, 'version': VERSION, 'request_id': request_id,
                              'peer': self.client_address[0]}), flush=True)

    def log_message(self, fmt, *args):
        pass


server = ThreadingHTTPServer(('0.0.0.0', 8080), Handler)


def stop(signum, frame):
    global STOPPING
    STOPPING = True
    threading.Thread(target=server.shutdown, daemon=True).start()


signal.signal(signal.SIGTERM, stop)
print(json.dumps({'event': 'listening', 'version': VERSION, 'ready_after_seconds': READY_AFTER}), flush=True)
server.serve_forever()
server.server_close()
