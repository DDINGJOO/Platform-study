"""하위 서비스. GET /data 는 FAIL_RATE 비율로 503, 나머지는 DELAY_MS 뒤 200.
GET /stats 는 받은 /data 요청 수(재시도까지 포함)를 돌려준다. POST /reset 은 0 으로."""
import json, os, random, threading, time
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

FAIL = float(os.environ.get("FAIL_RATE", "0.1"))
DELAY = float(os.environ.get("DELAY_MS", "5")) / 1000
lock = threading.Lock()
count = {"data": 0, "fail": 0}


class H(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    # 헤더와 본문을 따로 써서, 켜 두면 Nagle 과 지연 ACK 가 맞물려 연결을 재사용하는 요청이 약 40ms 늦어진다(README 함정 3)
    disable_nagle_algorithm = True

    def log_message(self, *a):
        pass

    def _send(self, code, body):
        b = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        if self.path.startswith("/data"):
            fail = random.random() < FAIL
            with lock:
                count["data"] += 1
                count["fail"] += fail
            if DELAY:
                time.sleep(DELAY)
            return self._send(503, '{"err":"boom"}') if fail else self._send(200, '{"ok":1}')
        if self.path.startswith("/stats"):
            with lock:
                return self._send(200, json.dumps(count))
        self._send(404, "{}")

    def do_POST(self):
        global FAIL
        if self.path.startswith("/reset"):
            with lock:
                count["data"] = count["fail"] = 0
            return self._send(200, "{}")
        if self.path.startswith("/fail"):
            FAIL = float(self.path.split("=")[1])
            return self._send(200, json.dumps({"fail": FAIL}))
        self._send(404, "{}")


ThreadingHTTPServer.daemon_threads = True
ThreadingHTTPServer(("0.0.0.0", 8080), H).serve_forever()
