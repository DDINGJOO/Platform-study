"""누수가 있는 서비스. /state/leak 파일이 있으면 시작 후 GRACE_S 초가 지나면서 실패가 늘어난다
(GRACE_S 뒤 RAMP_S 초 동안 0% → 100%). 재시작하면 경과 시간이 0으로 돌아가 한동안 멀쩡하다.
원인(파일)은 볼륨에 있어서 재시작으로는 사라지지 않는다.
/metrics: app_requests_total{result="ok|error"}, app_start_time_seconds
/admin/restart: 응답 뒤 프로세스를 끝낸다(Docker restart: always 가 다시 띄운다)"""
import os, random, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

GRACE, RAMP = float(os.environ.get("GRACE_S", "45")), float(os.environ.get("RAMP_S", "15"))
START = time.time(); ok = err = 0; lock = threading.Lock()

def fail_prob():
    if not os.path.exists("/state/leak"):
        return 0.0
    up = time.time() - START
    return min(1.0, max(0.0, (up - GRACE) / RAMP))

class H(BaseHTTPRequestHandler):
    def _send(self, code, body):
        b = body.encode(); self.send_response(code)
        # Prometheus 3 은 Content-Type 이 비어 있는 스크레이프를 거부한다(fallback_scrape_protocol 이 없으면)
        self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        global ok, err
        if self.path == "/metrics":
            with lock:
                self._send(200, f'app_requests_total{{result="ok"}} {ok}\napp_requests_total{{result="error"}} {err}\n'
                                f"app_start_time_seconds {START}\n")
            return
        bad = random.random() < fail_prob()
        with lock:
            if bad: err += 1
            else: ok += 1
        self._send(500 if bad else 200, "error\n" if bad else "ok\n")
    def do_POST(self):
        if self.path == "/admin/restart":
            self._send(202, "restarting\n")
            threading.Timer(0.2, lambda: os._exit(1)).start()
        else:
            self._send(404, "no\n")
    def log_message(self, *a):
        pass

print(f"start leak={os.path.exists('/state/leak')}", flush=True)
ThreadingHTTPServer(("", 8080), H).serve_forever()
