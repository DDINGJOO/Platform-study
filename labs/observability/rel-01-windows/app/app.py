"""신뢰성 설계 실습용 앱. 파이썬 표준 라이브러리만 쓴다.

서비스 여러 개를 한 프로세스가 흉내 낸다. 서비스마다 에러율과 지연 분포를 따로 준다.

  GET  /api/<svc>        설정된 확률로 500, 설정된 분포만큼 잠든 뒤 200
  GET  /health           항상 200 (의존성을 보지 않는 생존 확인)
  GET  /metrics          Prometheus 텍스트 형식
  POST /admin/config     {"svc": {...}} 로 서비스 설정을 바꾼다
  POST /admin/outage     {"svc": "x", "seconds": 60} 동안 그 서비스가 503
  그 밖의 경로             404

설정 예 (환경변수 APP_CONFIG, JSON)
  {"checkout": {"error_rate": 0.002,
                "latency": {"dist": "lognormal", "median_ms": 40, "sigma": 0.5}}}
  지연 분포: lognormal | bimodal(p_slow, fast:{median_ms,sigma}, slow:{median_ms,sigma}) | none
"""
import json
import math
import os
import random
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BUCKETS = [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
LOCK = threading.Lock()
CONFIG = json.loads(os.environ.get("APP_CONFIG", "{}"))
OUTAGE = {}          # svc -> 끝나는 시각(monotonic)
COUNTS = {}          # (route, client, code) -> n
HIST = {}            # svc -> [버킷별 누적, sum, count]
RND = random.Random()


def client_class(ua):
    ua = (ua or "").lower()
    if any(k in ua for k in ("bot", "crawler", "spider")):
        return "bot"
    if any(k in ua for k in ("probe", "health")):
        return "probe"
    return "user"


def sample_latency(spec):
    if not spec or spec.get("dist", "none") == "none":
        return 0.0
    if spec["dist"] == "lognormal":
        return RND.lognormvariate(math.log(spec["median_ms"]), spec["sigma"]) / 1000
    if spec["dist"] == "bimodal":
        part = spec["slow"] if RND.random() < spec["p_slow"] else spec["fast"]
        return RND.lognormvariate(math.log(part["median_ms"]), part["sigma"]) / 1000
    raise ValueError(spec)


def count(route, client, code):
    with LOCK:
        k = (route, client, str(code))
        COUNTS[k] = COUNTS.get(k, 0) + 1


def observe(svc, seconds):
    with LOCK:
        h = HIST.setdefault(svc, [[0] * len(BUCKETS), 0.0, 0])
        for i, b in enumerate(BUCKETS):
            if seconds <= b:
                h[0][i] += 1
        h[1] += seconds
        h[2] += 1


def metrics_text():
    out = ["# TYPE lab_http_requests_total counter"]
    with LOCK:
        for (route, client, code), n in sorted(COUNTS.items()):
            out.append(f'lab_http_requests_total{{route="{route}",client="{client}",code="{code}"}} {n}')
        out.append("# TYPE lab_http_request_duration_seconds histogram")
        for svc, (b, s, c) in sorted(HIST.items()):
            for le, n in zip(BUCKETS, b):
                out.append(f'lab_http_request_duration_seconds_bucket{{svc="{svc}",le="{le}"}} {n}')
            out.append(f'lab_http_request_duration_seconds_bucket{{svc="{svc}",le="+Inf"}} {c}')
            out.append(f'lab_http_request_duration_seconds_sum{{svc="{svc}"}} {s}')
            out.append(f'lab_http_request_duration_seconds_count{{svc="{svc}"}} {c}')
    return "\n".join(out) + "\n"


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass

    def reply(self, code, body=b"", ctype="text/plain"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?")[0]
        client = client_class(self.headers.get("User-Agent"))
        if path == "/metrics":
            return self.reply(200, metrics_text().encode(), "text/plain; version=0.0.4")
        if path == "/health":
            count("/health", client, 200)
            return self.reply(200, b"ok")
        if path.startswith("/api/") and path[5:] in CONFIG:
            svc = path[5:]
            cfg = CONFIG[svc]
            start = time.monotonic()
            if OUTAGE.get(svc, 0) > start:
                code = 503
            else:
                time.sleep(sample_latency(cfg.get("latency")))
                code = 500 if RND.random() < cfg.get("error_rate", 0) else 200
            observe(svc, time.monotonic() - start)
            count(f"/api/{svc}", client, code)
            return self.reply(code, b"ok" if code == 200 else b"fail")
        count("unmatched", client, 404)
        return self.reply(404, b"not found")

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(n) or b"{}")
        if self.path == "/admin/config":
            CONFIG.update(body)
            return self.reply(200, json.dumps(CONFIG).encode(), "application/json")
        if self.path == "/admin/outage":
            OUTAGE[body["svc"]] = time.monotonic() + float(body["seconds"])
            return self.reply(200, b"outage set")
        return self.reply(404, b"not found")


def zero_init():
    # 아직 한 번도 안 난 에러의 시계열도 0 으로 미리 만든다.
    # 없으면 첫 에러가 났을 때 시계열이 그제야 생겨서 rate() 가 그 첫 건을 못 센다.
    for svc in CONFIG:
        for code in (200, 500, 503):
            COUNTS.setdefault((f"/api/{svc}", "user", str(code)), 0)


if __name__ == "__main__":
    zero_init()
    srv = ThreadingHTTPServer(("0.0.0.0", 8080), Handler)
    srv.daemon_threads = True
    srv.request_queue_size = 512
    print("listening :8080 config=", json.dumps(CONFIG), flush=True)
    srv.serve_forever()
