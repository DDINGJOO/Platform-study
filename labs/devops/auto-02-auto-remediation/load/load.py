"""초당 RATE 건을 app 에 보내고 결과를 /out/load.csv 에 한 줄씩 남긴다 (시각, 결과)."""
import os, time, http.client
from concurrent.futures import ThreadPoolExecutor
RATE = float(os.environ.get("RATE", "20"))
f = open("/out/load.csv", "a", buffering=1)
def one():
    s = time.time()
    try:
        c = http.client.HTTPConnection("app", 8080, timeout=2)
        c.request("GET", "/order"); r = c.getresponse(); r.read(); res = str(r.status); c.close()
    except Exception as e:
        res = type(e).__name__
    f.write(f"{s:.3f},{res}\n")
t0 = time.time(); i = 0
with ThreadPoolExecutor(32) as ex:
    while True:
        d = t0 + i / RATE - time.time()
        if d > 0: time.sleep(d)
        ex.submit(one); i += 1
