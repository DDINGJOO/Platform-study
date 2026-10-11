"""카나리 실습용 작은 HTTP 서비스. 표준 라이브러리만 쓴다.

GET /work     일을 하는 척한다(지연을 sleep 으로 만든다). 일부는 500 으로 실패한다
GET /metrics  프로메테우스 텍스트 형식 지표

환경변수로 버전의 성질을 정한다.
  VERSION        지표 라벨에 붙는 버전 이름
  BASE_MS        평균 지연(ms). 실제 지연은 로그정규 분포로 흔든다
  EXTRA_MS       이 버전이 더 느린 만큼(ms). 나쁜 버전에서 쓴다
  ERROR_RATE     500 으로 실패시키는 비율(0~1)
  WARMUP_MS      막 뜬 프로세스가 더 느린 만큼(ms). uptime 에 따라 지수로 줄어든다
  WARMUP_TAU_S   그 감소의 시간 상수(초). WARMUP_MS * exp(-uptime/TAU)
                 JIT 컴파일, 캐시, 커넥션 풀처럼 프로세스가 데워지는 효과를 흉내 낸 것이다
"""
import math
import os
import random
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

VERSION = os.environ.get("VERSION", "v1")
BASE_MS = float(os.environ.get("BASE_MS", "20"))
EXTRA_MS = float(os.environ.get("EXTRA_MS", "0"))
ERROR_RATE = float(os.environ.get("ERROR_RATE", "0"))
WARMUP_MS = float(os.environ.get("WARMUP_MS", "0"))
WARMUP_TAU_S = float(os.environ.get("WARMUP_TAU_S", "120"))
START = time.time()

BUCKETS = [0.005 * i for i in range(1, 41)] + [0.25, 0.3, 0.4, 0.5, 1.0, 2.5]  # 5ms 간격, 200ms 까지
lock = threading.Lock()
counts = {}          # code -> 요청 수
hist = {}            # code -> [버킷별 누적 수]
sums = {}            # code -> 지연 합(초)


def observe(code, seconds):
    with lock:
        counts[code] = counts.get(code, 0) + 1
        sums[code] = sums.get(code, 0.0) + seconds
        h = hist.setdefault(code, [0] * len(BUCKETS))
        for i, le in enumerate(BUCKETS):
            if seconds <= le:
                h[i] += 1


def render():
    lab = f'version="{VERSION}"'
    out = ["# TYPE demo_requests_total counter"]
    with lock:
        for code, n in counts.items():
            out.append(f'demo_requests_total{{{lab},code="{code}"}} {n}')
        out.append("# TYPE demo_request_seconds histogram")
        for code, h in hist.items():
            for le, n in zip(BUCKETS, h):
                out.append(f'demo_request_seconds_bucket{{{lab},code="{code}",le="{le:g}"}} {n}')
            out.append(f'demo_request_seconds_bucket{{{lab},code="{code}",le="+Inf"}} {counts[code]}')
            out.append(f'demo_request_seconds_sum{{{lab},code="{code}"}} {sums[code]}')
            out.append(f'demo_request_seconds_count{{{lab},code="{code}"}} {counts[code]}')
    out.append("# TYPE demo_uptime_seconds gauge")
    out.append(f"demo_uptime_seconds{{{lab}}} {time.time() - START:.1f}")
    return "\n".join(out) + "\n"


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

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
        if self.path.startswith("/work"):
            t0 = time.perf_counter()
            uptime = time.time() - START
            ms = BASE_MS * random.lognormvariate(0, 0.25) + EXTRA_MS
            ms += WARMUP_MS * math.exp(-uptime / WARMUP_TAU_S)
            time.sleep(ms / 1000)
            code = 500 if random.random() < ERROR_RATE else 200
            observe(str(code), time.perf_counter() - t0)
            return self._send(code, f"{VERSION} {code}\n")
        self._send(404, "not found")


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
