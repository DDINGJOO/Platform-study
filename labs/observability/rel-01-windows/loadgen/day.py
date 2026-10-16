"""하루를 압축해서 흘린다. 실제 1초 = 압축된 1분, 하루 = 1440초(24분).

트래픽 셋을 동시에 보낸다.
  user  : curve.py 의 하루 곡선을 따른다(피크 초당 --peak 건). 5xx 를 받으면 0.2초 뒤 한 번 재시도한다
  bot   : 초당 --bot-rps 건으로 일정. 40%는 진짜 API, 30%는 /robots.txt, 30%는 없는 경로
  probe : 헬스 체커 --probes 대가 각자 초당 1번 /health
장애는 --outage-at(압축 시각, 시) 부터 --outage-min(압축 분) 동안 /api/checkout 이 503 을 낸다.
요청 하나마다 CSV 한 줄: 보낸 시각, 압축 분, 종류, 경로, 시도 번호, 상태 코드

  python day.py --out /out/day-night.csv --outage-at 1 --outage-min 60
"""
import argparse
import csv
import http.client
import json
import random
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

from curve import ratio

ap = argparse.ArgumentParser()
ap.add_argument("--target", default="http://app:8080")
ap.add_argument("--out", required=True)
ap.add_argument("--peak", type=float, default=40.0)
ap.add_argument("--bot-rps", type=float, default=2.0)
ap.add_argument("--probes", type=int, default=3)
ap.add_argument("--outage-at", type=float, default=None, help="압축 시각(시)")
ap.add_argument("--outage-min", type=float, default=0, help="압축 분 = 실제 초")
ap.add_argument("--seed", type=int, default=1)
ap.add_argument("--day-seconds", type=float, default=1440)
args = ap.parse_args()

u = urlparse(args.target)
local = threading.local()
lock = threading.Lock()
rows = []
T0 = time.monotonic()
SCALE = args.day_seconds / 1440.0   # 압축 1분이 실제 몇 초인가 (기본 1)


def now_min():
    return (time.monotonic() - T0) / SCALE


def get(path, ua):
    try:
        c = getattr(local, "c", None)
        if c is None:
            c = local.c = http.client.HTTPConnection(u.hostname, u.port, timeout=10)
        c.request("GET", path, headers={"User-Agent": ua})
        r = c.getresponse()
        r.read()
        return r.status
    except Exception:
        local.c = None
        return -1


def record(kind, path, attempt, code, minute):
    with lock:
        rows.append((round(time.time(), 3), round(minute, 3), kind, path, attempt, code))


def user_req():
    m = now_min()
    code = get("/api/checkout", "lab-user/1.0")
    record("user", "/api/checkout", 1, code, m)
    if code >= 500 or code < 0:
        time.sleep(0.2 * SCALE)
        m2 = now_min()
        record("user", "/api/checkout", 2, get("/api/checkout", "lab-user/1.0"), m2)


def bot_req(rnd):
    x = rnd.random()
    path = "/api/checkout" if x < 0.4 else "/robots.txt" if x < 0.7 else f"/old/page-{rnd.randrange(1000)}"
    m = now_min()
    record("bot", path, 1, get(path, "lab-crawler-bot/1.0"), m)


def probe_req():
    m = now_min()
    record("probe", "/health", 1, get("/health", "lab-health-probe/1.0"), m)


def poisson_loop(pool, rate_fn, task, seed):
    rnd = random.Random(seed)
    while True:
        m = now_min()
        if m >= 1440:
            return
        lam = max(rate_fn(m), 1e-6)            # 초당(실제) 요청 수
        gap = rnd.expovariate(lam)
        time.sleep(gap)
        if now_min() >= 1440:
            return
        pool.submit(task)


def probe_loop(pool, offset):
    k = 0
    while True:
        due = offset + k * SCALE              # 압축 1분마다 한 번 = 실제 1초마다
        wait = due - (time.monotonic() - T0)
        if wait > 0:
            time.sleep(wait)
        if now_min() >= 1440:
            return
        pool.submit(probe_req)
        k += 1


def outage():
    if args.outage_at is None:
        return
    start = args.outage_at * 60
    time.sleep(max(0, start * SCALE - (time.monotonic() - T0)))
    body = json.dumps({"svc": "checkout", "seconds": args.outage_min * SCALE}).encode()
    c = http.client.HTTPConnection(u.hostname, u.port, timeout=10)
    c.request("POST", "/admin/outage", body=body, headers={"Content-Type": "application/json"})
    c.getresponse().read()
    print(f"outage set at compressed minute {now_min():.2f} for {args.outage_min} min", flush=True)


out = open(args.out, "w", newline="")
writer = csv.writer(out)
writer.writerow(["ts", "minute", "kind", "path", "attempt", "code"])
stop = threading.Event()


def flush():
    # 실행이 중간에 끊겨도 그때까지의 기록이 남도록 10초마다 파일에 덧붙인다(줄 순서는 시각순이 아닐 수 있다)
    with lock:
        batch = rows[:]
        rows.clear()
    writer.writerows(batch)
    out.flush()


def flush_loop():
    while not stop.wait(10):
        flush()


threading.Thread(target=flush_loop, daemon=True).start()
rnd_bot = random.Random(args.seed + 7)
with ThreadPoolExecutor(max_workers=300) as pool:
    ths = [threading.Thread(target=poisson_loop, args=(pool, lambda m: args.peak * ratio(m / 60) / SCALE, user_req, args.seed)),
           threading.Thread(target=poisson_loop, args=(pool, lambda m: args.bot_rps / SCALE, lambda: bot_req(rnd_bot), args.seed + 1)),
           threading.Thread(target=outage)]
    ths += [threading.Thread(target=probe_loop, args=(pool, i * SCALE / max(1, args.probes))) for i in range(args.probes)]
    for th in ths:
        th.start()
    for th in ths:
        th.join()

stop.set()
flush()
out.close()
n = sum(1 for _ in open(args.out)) - 1
print(f"wrote {n} rows to {args.out}", flush=True)
