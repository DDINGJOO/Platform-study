"""장애 대응 실습-2 의 작은 서비스. 표준 라이브러리만 쓴다.

ROLE=order     : POST/GET /orders 를 받으면 재고 서비스(INVENTORY_URL)에 재고를 묻는다.
                 재고 호출이 타임아웃(UPSTREAM_TIMEOUT 초)에 걸리면 503 으로 실패시킨다.
                 urllib 의 timeout 은 요청 전체가 아니라 소켓 동작(연결, 읽기) 하나하나에 걸린다.
                 POST /admin/fallback?on=1 이면 재고 확인을 건너뛰고 주문을 '확인 보류'로 받는다(완화 수단).
ROLE=inventory : GET /stock/<sku> 에 바로 답한다.
둘 다 /metrics 에 Prometheus 텍스트 형식으로 지표를 낸다.
"""
import os, threading, time, urllib.request, urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROLE = os.environ.get("ROLE", "order")
INVENTORY_URL = os.environ.get("INVENTORY_URL", "http://toxiproxy:28666")
TIMEOUT = float(os.environ.get("UPSTREAM_TIMEOUT", "1.0"))
BUCKETS = [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 0.75, 1.0, 1.5, 2.5, 5.0]

lock = threading.Lock()
state = {"fallback": False}
counters = {}      # (name, labels-tuple) -> value
hists = {}         # (name, labels-tuple) -> [bucket counts..., sum, count]


def inc(name, **labels):
    k = (name, tuple(sorted(labels.items())))
    with lock:
        counters[k] = counters.get(k, 0) + 1


def observe(name, v, **labels):
    k = (name, tuple(sorted(labels.items())))
    with lock:
        h = hists.setdefault(k, [0] * len(BUCKETS) + [0.0, 0])
        for i, b in enumerate(BUCKETS):
            if v <= b:
                h[i] += 1
        h[-2] += v
        h[-1] += 1


def fmt(labels, extra=None):
    items = list(labels) + ([extra] if extra else [])
    return "{" + ",".join(f'{k}="{v}"' for k, v in items) + "}" if items else ""


def render():
    out = []
    with lock:
        for (name, labels), v in sorted(counters.items()):
            out.append(f"{name}{fmt(labels)} {v}")
        for (name, labels), h in sorted(hists.items()):
            for i, b in enumerate(BUCKETS):
                out.append(f"{name}_bucket{fmt(labels, ('le', b))} {h[i]}")
            out.append(f"{name}_bucket{fmt(labels, ('le', '+Inf'))} {h[-1]}")
            out.append(f"{name}_sum{fmt(labels)} {h[-2]}")
            out.append(f"{name}_count{fmt(labels)} {h[-1]}")
        out.append(f"order_fallback_enabled {1 if state['fallback'] else 0}")
    return "\n".join(out) + "\n"


class H(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.0"

    def reply(self, code, body):
        b = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        if self.path == "/metrics":
            return self.reply(200, render())
        if ROLE == "inventory" and self.path.startswith("/stock/"):
            t0 = time.monotonic()
            self.reply(200, "7")
            observe("http_server_duration_seconds", time.monotonic() - t0, service="inventory")
            inc("http_server_requests_total", service="inventory", code="200")
            return
        if ROLE == "order" and self.path.startswith("/orders"):
            return self.order()
        self.reply(404, "no")

    do_POST = do_GET

    def order(self):
        t0 = time.monotonic()
        code = 200
        if state["fallback"]:
            body = "accepted (stock check deferred)"
            inc("order_deferred_total", service="order")
        else:
            u0 = time.monotonic()
            outcome = "ok"
            try:
                with urllib.request.urlopen(f"{INVENTORY_URL}/stock/A-100", timeout=TIMEOUT) as r:
                    r.read()
                body = "accepted"
            except Exception as e:  # 타임아웃, 연결 거부, 리셋
                outcome = "timeout" if "timed out" in str(e) else "error"
                code, body = 503, f"inventory unavailable: {outcome}"
            observe("upstream_duration_seconds", time.monotonic() - u0, service="order", upstream="inventory")
            inc("upstream_requests_total", service="order", upstream="inventory", outcome=outcome)
        self.reply(code, body)
        observe("http_server_duration_seconds", time.monotonic() - t0, service="order")
        inc("http_server_requests_total", service="order", code=str(code))

    def log_message(self, *a):
        pass


class Admin(H):
    def do_POST(self):
        if ROLE == "order" and self.path.startswith("/admin/fallback"):
            state["fallback"] = "on=1" in self.path
            return self.reply(200, f"fallback={state['fallback']}\n")
        return H.do_GET(self)


print(f"{ROLE} on :8080 timeout={TIMEOUT}s upstream={INVENTORY_URL}", flush=True)
ThreadingHTTPServer(("", 8080), Admin).serve_forever()
