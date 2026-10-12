"""일정한 속도(RATE 건/초)로 주문을 넣는 부하기. 결과는 내지 않는다(지표는 서비스가 낸다)."""
import os, threading, time, urllib.request

URL = os.environ.get("TARGET", "http://order:8080/orders")
RATE = float(os.environ.get("RATE", "20"))


def one():
    try:
        urllib.request.urlopen(urllib.request.Request(URL, method="POST", data=b""), timeout=5).read()
    except Exception:
        pass


print(f"load {RATE}/s -> {URL}", flush=True)
nxt = time.monotonic()
while True:
    threading.Thread(target=one, daemon=True).start()
    nxt += 1 / RATE
    time.sleep(max(0, nxt - time.monotonic()))
