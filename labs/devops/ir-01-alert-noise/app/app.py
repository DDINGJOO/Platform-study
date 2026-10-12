"""경고 폭풍 실습용 앱. 표준 라이브러리만 쓴다.

ROLE=db  : 하위 의존성. /query 에 5ms 뒤 응답한다. 장애는 `docker compose pause db` 로 낸다
           (프로세스가 멈추면 연결은 맺어져도 응답이 오지 않는다).
ROLE=app : 서비스 하나의 인스턴스. 초당 RATE 건씩 db 의 /query 를 부르고(타임아웃 1초),
           결과와 걸린 시간을 Prometheus 텍스트 형식으로 /metrics 에 낸다.
           2초마다 db 의 /health 를 따로 불러 app_dependency_up 게이지를 갱신한다.
"""
import os, threading, time, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROLE = os.environ.get("ROLE", "app")
SERVICE = os.environ.get("SERVICE", "db")
DB_URL = os.environ.get("DB_URL", "http://db:8080")
RATE = float(os.environ.get("RATE", "10"))
TIMEOUT = float(os.environ.get("TIMEOUT", "1.0"))
BUCKETS = [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5]

lock = threading.Lock()
counts = {"ok": 0, "error": 0}
hist = [0] * (len(BUCKETS) + 1)   # 마지막 칸은 +Inf
hsum = 0.0
dep_up = 1


def observe(result, seconds):
    global hsum
    with lock:
        counts[result] += 1
        hsum += seconds
        for i, le in enumerate(BUCKETS):
            if seconds <= le:
                hist[i] += 1
        hist[-1] += 1


def call_db():
    t = time.monotonic()
    try:
        with urllib.request.urlopen(DB_URL + "/query", timeout=TIMEOUT) as r:
            r.read()
        observe("ok", time.monotonic() - t)
    except Exception:
        observe("error", time.monotonic() - t)


def traffic_loop():
    gap = 1.0 / RATE
    nxt = time.monotonic()
    while True:
        threading.Thread(target=call_db, daemon=True).start()
        nxt += gap
        time.sleep(max(0.0, nxt - time.monotonic()))


def health_loop():
    global dep_up
    while True:
        try:
            with urllib.request.urlopen(DB_URL + "/health", timeout=TIMEOUT) as r:
                r.read()
            dep_up = 1
        except Exception:
            dep_up = 0
        time.sleep(2)


def metrics_text():
    out = []
    if ROLE == "app":
        with lock:
            out.append("# TYPE app_requests_total counter")
            for k, v in counts.items():
                out.append(f'app_requests_total{{result="{k}"}} {v}')
            out.append("# TYPE app_request_duration_seconds histogram")
            for le, c in zip(BUCKETS, hist):
                out.append(f'app_request_duration_seconds_bucket{{le="{le}"}} {c}')
            out.append(f'app_request_duration_seconds_bucket{{le="+Inf"}} {hist[-1]}')
            out.append(f"app_request_duration_seconds_sum {hsum}")
            out.append(f"app_request_duration_seconds_count {hist[-1]}")
        out.append("# TYPE app_dependency_up gauge")
        out.append(f'app_dependency_up{{dependency="db"}} {dep_up}')
    out.append("# TYPE lab_role_info gauge")
    out.append(f'lab_role_info{{role="{ROLE}"}} 1')
    return "\n".join(out) + "\n"


class H(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/metrics":
            body = metrics_text().encode()
            ctype = "text/plain; version=0.0.4"
        elif self.path in ("/query", "/health"):
            if ROLE == "db" and self.path == "/query":
                time.sleep(0.005)
            body, ctype = b"ok\n", "text/plain"
        else:
            self.send_response(404); self.end_headers(); return
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    if ROLE == "app":
        threading.Thread(target=traffic_loop, daemon=True).start()
        threading.Thread(target=health_loop, daemon=True).start()
    print(f"{ROLE} {SERVICE} on :8080", flush=True)
    ThreadingHTTPServer(("", 8080), H).serve_forever()
