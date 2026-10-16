"""한 홉짜리 HTTP 서비스. 같은 이미지를 여러 개 띄워 체인이나 병렬 묶음을 만든다.

GET  /work    자기 실패를 먼저 판정하고(503), 살아 있으면 다음 홉을 부른다(실패하면 502)
GET  /stats   받은 요청 수, 자기 실패 수, 다음 홉 호출 수와 실패 수
POST /config  실행 중에 설정을 바꾼다 (fail_rate, mode, slot_ms, retries, pick)
POST /reset   카운터를 0으로
GET  /health  항상 200

다음 홉은 NEXT 환경변수(쉼표로 여러 개). 여러 개면 pick 설정에 따라
  first    : 첫 번째만 부른다
  failover : 무작위 순서로 하나씩 부르다가 성공하면 멈춘다(병렬 구성)
실패 판정 mode
  random  : 요청마다 독립적으로 fail_rate 확률로 실패
  slotted : 시간을 slot_ms 단위로 자르고, 슬롯마다 fail_rate 확률로 그 슬롯 전체가 실패
            (홉 이름과 슬롯 번호의 해시로 정하므로 홉끼리는 독립, 같은 슬롯 안의 재시도는 또 실패)
표준 라이브러리만 쓴다.
"""
import hashlib, http.client, json, os, random, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

NAME = os.environ.get("HOP_NAME", "hop")
NEXT = [u for u in os.environ.get("NEXT", "").split(",") if u]
CFG = {
    "fail_rate": float(os.environ.get("FAIL_RATE", "0")),
    "mode": os.environ.get("FAIL_MODE", "random"),
    "slot_ms": int(os.environ.get("SLOT_MS", "100")),
    "retries": int(os.environ.get("RETRIES", "0")),
    "pick": os.environ.get("PICK", "first"),
    "seed": os.environ.get("SEED", "1"),
}
LOCK = threading.Lock()
C = {"received": 0, "own_fail": 0, "down_calls": 0, "down_fail": 0, "ok": 0, "fail": 0, "reconnect": 0}
TL = threading.local()


def bump(k, n=1):
    with LOCK:
        C[k] += n


def own_failure():
    fr = CFG["fail_rate"]
    if fr <= 0:
        return False
    if CFG["mode"] == "slotted":
        slot = int(time.time() * 1000) // CFG["slot_ms"]
        h = hashlib.blake2b(f"{CFG['seed']}:{NAME}:{slot}".encode(), digest_size=8).digest()
        return int.from_bytes(h, "big") / 2**64 < fr
    return random.random() < fr


def call(url):
    """다음 홉을 한 번 부른다. 연결은 스레드마다 대상별로 재사용한다."""
    conns = getattr(TL, "conns", None)
    if conns is None:
        conns = TL.conns = {}
    u = urlparse(url)
    for attempt in (1, 2):   # 끊긴 keep-alive 연결이면 한 번 새로 연다(재시도로 세지 않는다)
        c = conns.get(url)
        if c is None:
            c = conns[url] = http.client.HTTPConnection(u.hostname, u.port, timeout=5)
        try:
            c.request("GET", u.path or "/work")
            r = c.getresponse(); r.read()
            return r.status
        except (http.client.HTTPException, OSError):
            c.close(); conns.pop(url, None)
            bump("reconnect")   # 0이 아니면 숨은 재전송이 있었다는 뜻이니 결과를 의심한다
            if attempt == 2:
                return 599
    return 599


def downstream_ok():
    targets = list(NEXT)
    if CFG["pick"] == "failover":
        random.shuffle(targets)
    else:
        targets = targets[:1]
    for t in targets:
        for _ in range(1 + CFG["retries"]):
            bump("down_calls")
            if call(t) == 200:
                return True
            bump("down_fail")
    return False


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
        p = urlparse(self.path)
        if p.path == "/work":
            bump("received")
            if own_failure():
                bump("own_fail"); bump("fail")
                return self.send(503, b"own failure")
            if NEXT and not downstream_ok():
                bump("fail")
                return self.send(502, b"downstream failure")
            bump("ok")
            return self.send(200, b"ok")
        if p.path == "/stats":
            with LOCK:
                body = json.dumps({"name": NAME, **C, "cfg": CFG}).encode()
            return self.send(200, body, "application/json")
        if p.path == "/health":
            return self.send(200, b"up")
        self.send(404)

    def do_POST(self):
        p = urlparse(self.path)
        n = int(self.headers.get("Content-Length") or 0)
        if n:
            self.rfile.read(n)
        if p.path == "/reset":
            with LOCK:
                for k in C:
                    C[k] = 0
            return self.send(200, b"reset")
        if p.path == "/config":
            q = {k: v[0] for k, v in parse_qs(p.query).items()}
            for k, v in q.items():
                if k in ("fail_rate",):
                    CFG[k] = float(v)
                elif k in ("slot_ms", "retries"):
                    CFG[k] = int(v)
                elif k in CFG:
                    CFG[k] = v
            return self.send(200, json.dumps(CFG).encode(), "application/json")
        self.send(404)


class Server(ThreadingHTTPServer):
    daemon_threads = True
    request_queue_size = 256


if __name__ == "__main__":
    Server(("0.0.0.0", int(os.environ.get("PORT", "8080"))), H).serve_forever()
