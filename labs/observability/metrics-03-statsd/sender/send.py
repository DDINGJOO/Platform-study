"""StatsD 카운터 한 줄(lab.sent:1|c)을 UDP 패킷 하나에 담아 보낸다. 보낸 수를 직접 센다.
환경변수
  TARGET  받는 쪽 host:port          (기본 statsd:9125)
  RATE    초당 패킷 수, 0 이면 최대 속도 (기본 1000)
  SECONDS 보내는 시간(초)              (기본 30)
  LINE    보낼 한 줄                    (기본 lab.sent:1|c)
  STEPS   "초당패킷:초,초당패킷:초,..." 로 주면 RATE/SECONDS 대신 단계별로 속도를 바꾼다
  UNIX_SOCKET  주면 UDP 대신 이 경로의 유닉스 도메인 데이터그램 소켓으로 보낸다
  NONBLOCK     1 이면 소켓을 논블로킹으로 둔다. 받는 쪽 버퍼가 차면 기다리지 않고 오류(EAGAIN)를 센다
보낸 수는 :8000/metrics 의 lab_sender_packets_total 로 내보내고, 끝나면 로그로도 찍는다.
보내기가 끝나도 프로세스는 HOLD 초(기본 30) 더 살아 있어 Prometheus 가 마지막 값을 긁어 가게 한다."""
import os, socket, threading, time
from http.server import BaseHTTPRequestHandler, HTTPServer

host, port = os.environ.get("TARGET", "statsd:9125").rsplit(":", 1)
rate = int(os.environ.get("RATE", "1000"))  # 단계가 하나일 때
seconds = float(os.environ.get("SECONDS", "30"))
hold = float(os.environ.get("HOLD", "30"))
line = os.environ.get("LINE", "lab.sent:1|c").encode()

sent = 0
errors = 0

class H(BaseHTTPRequestHandler):
    def do_GET(self):
        body = (f"# TYPE lab_sender_packets counter\nlab_sender_packets_total {sent}\n"
                f"# TYPE lab_sender_errors counter\nlab_sender_errors_total {errors}\n").encode()
        self.send_response(200); self.send_header("Content-Type", "text/plain; version=0.0.4")
        self.end_headers(); self.wfile.write(body)
    def log_message(self, *a): pass

threading.Thread(target=HTTPServer(("", 8000), H).serve_forever, daemon=True).start()

if os.environ.get("UNIX_SOCKET"):
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    addr = os.environ["UNIX_SOCKET"]
else:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    addr = (socket.gethostbyname(host), int(port))
if os.environ.get("NONBLOCK") == "1":
    sock.setblocking(False)
steps = [(int(r), float(d)) for r, d in (x.split(":") for x in os.environ["STEPS"].split(","))] \
    if os.environ.get("STEPS") else [(rate, seconds)]

def blast(rate, seconds):
    global sent, errors
    end = time.monotonic() + seconds
    tick = 0.01                      # 10ms 마다 몫만큼 몰아서 보낸다
    owed = 0.0
    while True:
        now = time.monotonic()
        if now >= end:
            return
        if rate == 0:
            n = 1000
        else:
            owed += rate * tick
            n = int(owed)
            owed -= n
        for _ in range(n):
            try:
                sock.sendto(line, addr)
                sent += 1
            except OSError:
                errors += 1
        if rate:
            time.sleep(max(0.0, tick - (time.monotonic() - now)))

start = time.monotonic()
for r, d in steps:
    before, t0 = sent, time.monotonic()
    blast(r, d)
    if len(steps) > 1:
        print(f"step rate={r} sent={sent - before} actual={(sent - before) / (time.monotonic() - t0):,.0f}/s", flush=True)
took = time.monotonic() - start
print(f"sent={sent} errors={errors} seconds={took:.1f} rate={sent/took:,.0f}/s", flush=True)
time.sleep(hold)
