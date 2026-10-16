"""열린 루프(open-loop) 부하 생성기. 표준 라이브러리만 쓴다.

서비스마다 초당 요청 수를 따로 주고, 도착 간격은 지수분포(포아송 도착)로 뽑는다.
응답을 기다리지 않고 정해진 시각에 다음 요청을 보내므로, 서버가 느려져도 보내는 양이 줄지 않는다.
요청 하나마다 CSV 한 줄을 남긴다(10초마다 덧붙이므로 줄 순서는 시각순이 아닐 수 있다): 보낼 예정 시각, 서비스, 상태 코드, 지연(ms, 예정 시각 기준)

  python loadgen.py --target http://app:8080 --duration 1800 --out /out/run.csv r1:1 r10:10 r100:100
"""
import argparse
import csv
import http.client
import random
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

ap = argparse.ArgumentParser()
ap.add_argument("--target", default="http://app:8080")
ap.add_argument("--duration", type=float, default=600)
ap.add_argument("--out", required=True)
ap.add_argument("--seed", type=int, default=1)
ap.add_argument("--ua", default="lab-user/1.0")
ap.add_argument("plans", nargs="+", help="svc:rps")
args = ap.parse_args()

u = urlparse(args.target)
local = threading.local()
lock = threading.Lock()
rows = []
t0_wall = time.time()
t0 = time.monotonic()


def conn():
    c = getattr(local, "c", None)
    if c is None:
        c = http.client.HTTPConnection(u.hostname, u.port, timeout=10)
        local.c = c
    return c


def fire(svc, due):
    code = -1
    try:
        c = conn()
        c.request("GET", f"/api/{svc}", headers={"User-Agent": args.ua})
        r = c.getresponse()
        r.read()
        code = r.status
    except Exception:
        local.c = None
    end = time.monotonic()
    with lock:
        rows.append((round(t0_wall + due, 4), svc, code, round((end - t0 - due) * 1000, 2)))


def schedule(pool, svc, rps, seed):
    rnd = random.Random(seed)
    due = rnd.expovariate(rps)
    while due < args.duration:
        wait = due - (time.monotonic() - t0)
        if wait > 0:
            time.sleep(wait)
        pool.submit(fire, svc, due)
        due += rnd.expovariate(rps)


out = open(args.out, "w", newline="")
writer = csv.writer(out)
writer.writerow(["ts", "svc", "code", "latency_ms"])
stop = threading.Event()


def flush_loop():
    # 실행이 중간에 끊겨도 그때까지의 기록이 남도록 10초마다 파일에 덧붙인다
    while not stop.wait(10):
        flush()


def flush():
    with lock:
        batch = rows[:]
        rows.clear()
    writer.writerows(batch)
    out.flush()


fl = threading.Thread(target=flush_loop, daemon=True)
fl.start()
with ThreadPoolExecutor(max_workers=400) as pool:
    ths = []
    for i, p in enumerate(args.plans):
        svc, rps = p.split(":")
        th = threading.Thread(target=schedule, args=(pool, svc, float(rps), args.seed * 100 + i))
        th.start()
        ths.append(th)
    for th in ths:
        th.join()

stop.set()
flush()
out.close()
n = sum(1 for _ in open(args.out)) - 1
print(f"wrote {n} rows to {args.out}", flush=True)
