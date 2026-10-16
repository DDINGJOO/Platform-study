"""복제본 하나. HAProxy 뒤에 여러 개 띄운다.

GET  /work          공유 Redis 에서 설정 키 `mode` 를 읽는다.
                    mode == "bad" 이면 500(공유 설정이 모든 복제본을 같이 망가뜨리는 공통 원인)
                    Redis 에 못 붙어도 500(공유 저장소 장애)
GET  /health        얕은 앱 검사. 상태가 up 또는 gray 면 200
GET  /health/deep   Redis 까지 확인하는 깊은 검사
POST /admin/state?s=up|down|gray|hang
       up   정상
       down 프로세스와 포트는 살아 있지만 /work 와 /health 가 모두 503 (앱만 죽은 상태)
       gray /work 는 500, /health 는 200 (헬스 체크가 못 보는 고장)
       hang /work 와 /health 가 응답 없이 30초 멈춘다
GET  /stats         받은 요청 수와 상태별 응답 수
표준 라이브러리만 쓴다.
"""
import json, os, socket, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

NAME = os.environ.get("NAME", "replica")
REDIS = os.environ.get("REDIS", "redis:6379")
STATE = {"s": "up"}
LOCK = threading.Lock()
C = {"work": 0, "health": 0, "codes": {}}
TL = threading.local()


def redis_get(key):
    """RESP 인라인 명령으로 GET. 스레드마다 연결 하나를 재사용한다. 실패하면 예외."""
    s = getattr(TL, "sock", None)
    if s is None:
        host, port = REDIS.split(":")
        s = socket.create_connection((host, int(port)), timeout=0.5)
        TL.sock = s; TL.buf = b""
    try:
        s.sendall(f"GET {key}\r\n".encode())
        data = TL.buf
        while b"\r\n" not in data:
            chunk = s.recv(4096)
            if not chunk:
                raise OSError("closed")
            data += chunk
        head, rest = data.split(b"\r\n", 1)
        if head == b"$-1":
            TL.buf = rest; return None
        if not head.startswith(b"$"):
            raise OSError(head)
        n = int(head[1:])
        while len(rest) < n + 2:
            chunk = s.recv(4096)
            if not chunk:
                raise OSError("closed")
            rest += chunk
        TL.buf = rest[n + 2:]
        return rest[:n].decode()
    except Exception:
        try: s.close()
        except Exception: pass
        TL.sock = None
        raise


def count(code):
    with LOCK:
        C["codes"][code] = C["codes"].get(code, 0) + 1


class H(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    # 헤더와 본문이 따로 나가면 Nagle 과 지연 ACK 가 겹쳐 요청마다 약 40ms 가 붙었다(리눅스 컨테이너에서만)
    disable_nagle_algorithm = True

    def log_message(self, *a):
        pass

    def send(self, code, body=b"", ctype="text/plain"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        p = urlparse(self.path).path
        st = STATE["s"]
        if p == "/work":
            with LOCK: C["work"] += 1
            if st == "hang":
                time.sleep(30)
            if st == "down":
                count(503); return self.send(503, b"down")
            if st == "gray":
                count(500); return self.send(500, b"gray")
            try:
                mode = redis_get("mode")
            except Exception:
                count(500); return self.send(500, b"redis unavailable")
            if mode == "bad":
                count(500); return self.send(500, b"bad shared config")
            count(200); return self.send(200, NAME.encode())
        if p in ("/health", "/health/deep"):
            with LOCK: C["health"] += 1
            if st == "hang":
                time.sleep(30)
            if st == "down":
                return self.send(503, b"down")
            if p == "/health/deep":
                try:
                    redis_get("mode")
                except Exception:
                    return self.send(503, b"redis unavailable")
            return self.send(200, b"up")
        if p == "/stats":
            with LOCK:
                body = json.dumps({"name": NAME, "state": st, **C}).encode()
            return self.send(200, body, "application/json")
        self.send(404)

    def do_POST(self):
        u = urlparse(self.path)
        n = int(self.headers.get("Content-Length") or 0)
        if n: self.rfile.read(n)
        if u.path == "/admin/state":
            s = parse_qs(u.query).get("s", ["up"])[0]
            STATE["s"] = s
            return self.send(200, s.encode())
        if u.path == "/admin/reset":
            with LOCK:
                C["work"] = 0; C["health"] = 0; C["codes"] = {}
            return self.send(200, b"reset")
        self.send(404)


class Server(ThreadingHTTPServer):
    daemon_threads = True
    request_queue_size = 256


if __name__ == "__main__":
    Server(("0.0.0.0", int(os.environ.get("PORT", "8080"))), H).serve_forever()
