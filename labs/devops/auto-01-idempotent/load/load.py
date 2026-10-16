"""일정 속도 부하기. 요청마다 새 TCP 연결을 연다(연결을 재사용하지 않는 클라이언트 여럿을 흉내).
환경변수: TARGET(기본 http://web), RATE(초당 빠른 요청, 기본 100), SLOW(동시에 도는 1초짜리 요청 수, 기본 4),
DURATION(초), OUT(결과 CSV 경로). CSV 열: kind,start,end,result  (result = HTTP 코드 또는 예외 이름)"""
import os, time, threading, http.client, csv
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

T = urlparse(os.environ.get("TARGET", "http://web"))
RATE = float(os.environ.get("RATE", "100")); SLOW = int(os.environ.get("SLOW", "4"))
DUR = float(os.environ.get("DURATION", "30")); OUT = os.environ["OUT"]
rows, lock = [], threading.Lock()

def one(kind, path, timeout):
    s = time.time()
    try:
        c = http.client.HTTPConnection(T.hostname, T.port or 80, timeout=timeout)
        c.request("GET", path, headers={"Connection": "close"})
        r = c.getresponse(); r.read(); res = str(r.status); c.close()
    except Exception as e:
        res = type(e).__name__
    with lock:
        rows.append((kind, f"{s:.4f}", f"{time.time():.4f}", res))

t0 = time.time(); stop = t0 + DUR
def slow_loop():
    while time.time() < stop:
        one("slow", "/t/base/slow", 5)

ths = [threading.Thread(target=slow_loop) for _ in range(SLOW)]
for t in ths: t.start()
with ThreadPoolExecutor(64) as ex:
    i = 0
    while True:
        due = t0 + i / RATE
        if due >= stop: break
        d = due - time.time()
        if d > 0: time.sleep(d)
        ex.submit(one, "fast", "/t/base/", 2); i += 1
for t in ths: t.join()
with open(OUT, "w", newline="") as f:
    w = csv.writer(f); w.writerow(["kind", "start", "end", "result"]); w.writerows(sorted(rows, key=lambda r: r[1]))
print(f"wrote {len(rows)} rows to {OUT}", flush=True)
