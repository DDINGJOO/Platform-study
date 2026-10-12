"""카오스 실습용 작은 서비스 셋. 표준 라이브러리만 쓴다. ROLE 환경변수로 역할을 고른다.

ROLE=stock    GET /stock   재고를 읽는 척한다(BASE_MS 평균의 로그정규 지연)
ROLE=front    GET /order   stock 을 한 번 부르고 결과를 돌려준다. stock 이 실패하면 503
ROLE=loadgen  일정한 속도(RATE)로 front 에 요청을 보내고, 사용자 쪽에서 본 결과를 센다

공통
  GET /metrics   프로메테우스 텍스트 형식 지표
  GET /healthz   포트가 열려 있으면 200 (readinessProbe 용)
  STARTUP_S      프로세스가 뜬 뒤 이 초만큼 요청을 못 받는다(포트를 늦게 연다).
                 설정 파일 읽기, 캐시 예열처럼 실제 서비스가 기동에 쓰는 시간을 흉내 낸다

front 의 stock 호출
  STOCK_URL          기본 http://stock/stock
  STOCK_TIMEOUT_S    한 번 호출의 타임아웃(초)
  RETRIES            실패했을 때 다시 부르는 횟수(0 이면 재시도 없음)
  매 호출마다 새 TCP 연결을 연다(urllib 기본). 그래서 쿠버네티스 Service 가 호출마다 파드를 새로 고른다

loadgen
  TARGET     기본 http://front/order
  RATE       초당 요청 수. 응답을 기다리지 않고 정해진 시각마다 보낸다(열린 모델)
  TIMEOUT_S  사용자가 기다리는 최대 시간
"""
import os
import random
import socket
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROLE = os.environ.get("ROLE", "stock")
BASE_MS = float(os.environ.get("BASE_MS", "15"))
STARTUP_S = float(os.environ.get("STARTUP_S", "0"))
STOCK_URL = os.environ.get("STOCK_URL", "http://stock/stock")
STOCK_TIMEOUT_S = float(os.environ.get("STOCK_TIMEOUT_S", "1.0"))
RETRIES = int(os.environ.get("RETRIES", "0"))
TARGET = os.environ.get("TARGET", "http://front/order")
RATE = float(os.environ.get("RATE", "40"))
TIMEOUT_S = float(os.environ.get("TIMEOUT_S", "2.0"))
POD = os.environ.get("HOSTNAME", "?")

# 5ms 간격으로 300ms 까지, 그 뒤는 성기게. p99 < 250ms 같은 가설을 버킷 경계로 판정하려고 촘촘히 둔다
BUCKETS = [round(0.005 * i, 3) for i in range(1, 61)] + [0.4, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 5.0]
lock = threading.Lock()
counters = {}   # (name, labels) -> 값
hists = {}      # (name, labels) -> [버킷 누적, sum, count]


def inc(name, labels="", v=1):
    with lock:
        counters[(name, labels)] = counters.get((name, labels), 0) + v


def observe(name, labels, seconds):
    with lock:
        h = hists.setdefault((name, labels), [[0] * len(BUCKETS), 0.0, 0])
        for i, le in enumerate(BUCKETS):
            if seconds <= le:
                h[0][i] += 1
        h[1] += seconds
        h[2] += 1


def render():
    out = []
    with lock:
        for (name, labels), v in sorted(counters.items()):
            out.append(f"{name}{{{labels}}} {v}")
        for (name, labels), (b, s, c) in sorted(hists.items()):
            sep = "," if labels else ""
            for le, n in zip(BUCKETS, b):
                out.append(f'{name}_bucket{{{labels}{sep}le="{le:g}"}} {n}')
            out.append(f'{name}_bucket{{{labels}{sep}le="+Inf"}} {c}')
            out.append(f"{name}_sum{{{labels}}} {s}")
            out.append(f"{name}_count{{{labels}}} {c}")
    return "\n".join(out) + "\n"


def classify(exc):
    """요청 실패를 사람이 읽을 수 있는 종류로 나눈다"""
    if isinstance(exc, urllib.error.HTTPError):
        return f"http_{exc.code}"
    reason = getattr(exc, "reason", exc)
    if isinstance(reason, (socket.timeout, TimeoutError)) or "timed out" in str(reason):
        return "timeout"
    if isinstance(reason, ConnectionRefusedError):
        return "conn_refused"
    if isinstance(reason, ConnectionResetError):
        return "conn_reset"
    if isinstance(reason, OSError) and getattr(reason, "errno", None) in (113, 101):
        return "no_route"
    return "conn_other"


def call_stock():
    """stock 을 부른다. 실패하면 RETRIES 만큼 다시. (성공 여부, 마지막 실패 종류)"""
    last = ""
    for attempt in range(RETRIES + 1):
        t0 = time.perf_counter()
        try:
            with urllib.request.urlopen(STOCK_URL, timeout=STOCK_TIMEOUT_S) as r:
                r.read()
            observe("front_stock_call_seconds", 'outcome="ok"', time.perf_counter() - t0)
            inc("front_stock_calls_total", f'outcome="ok",attempt="{attempt}"')
            return True, ""
        except Exception as e:  # noqa: BLE001 실패 종류를 세려고 전부 받는다
            last = classify(e)
            observe("front_stock_call_seconds", 'outcome="fail"', time.perf_counter() - t0)
            inc("front_stock_calls_total", f'outcome="{last}",attempt="{attempt}"')
    return False, last


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.0"   # 응답마다 연결을 닫는다. 연결 재사용으로 파드가 고정되지 않게

    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="text/plain"):
        b = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        if self.path.startswith("/metrics"):
            return self._send(200, render(), "text/plain; version=0.0.4")
        if self.path.startswith("/healthz"):
            return self._send(200, "ok")
        t0 = time.perf_counter()
        if ROLE == "stock" and self.path.startswith("/stock"):
            time.sleep(BASE_MS * random.lognormvariate(0, 0.25) / 1000)
            code, body = 200, f"stock ok {POD}\n"
        elif ROLE == "front" and self.path.startswith("/order"):
            ok, why = call_stock()
            code, body = (200, f"order ok {POD}\n") if ok else (503, f"stock failed: {why}\n")
        else:
            return self._send(404, "not found")
        observe("app_request_seconds", f'code="{code}"', time.perf_counter() - t0)
        inc("app_requests_total", f'code="{code}"')
        self._send(code, body)


def loadgen():
    """열린 모델 부하: 응답이 늦어도 다음 요청은 제시각에 나간다. 시스템이 느려져도 부하가 줄지 않는다"""
    interval = 1.0 / RATE

    def one():
        t0 = time.perf_counter()
        try:
            with urllib.request.urlopen(TARGET, timeout=TIMEOUT_S) as r:
                r.read()
            outcome = "ok"
        except Exception as e:  # noqa: BLE001
            outcome = classify(e)
        dt = time.perf_counter() - t0
        inc("loadgen_requests_total", f'outcome="{outcome}"')
        observe("loadgen_request_seconds", "", dt)

    nxt = time.perf_counter()
    while True:
        threading.Thread(target=one, daemon=True).start()
        nxt += interval
        time.sleep(max(0.0, nxt - time.perf_counter()))


if __name__ == "__main__":
    if STARTUP_S > 0:
        time.sleep(STARTUP_S)     # 포트를 늦게 연다. 그동안 들어온 연결은 거절된다
    if ROLE == "loadgen":
        threading.Thread(target=loadgen, daemon=True).start()
    ThreadingHTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
