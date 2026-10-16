"""서비스마다 일정한 속도(열린 부하)로 GET /work 를 보내고 요청마다 한 줄씩 CSV 로 남긴다.
사용: python3 loadgen.py out/run.csv svc1=37001 svc2=37002 ... [--rate 20] [--timeout 5]
SIGTERM/SIGINT 를 받으면 멈춘다. 열 : t(유닉스 초), svc, status(0 = 연결 실패/타임아웃), policy, attempts, starter, ms, err
"""
import argparse, csv, queue, signal, sys, threading, time, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor

ap = argparse.ArgumentParser()
ap.add_argument("out")
ap.add_argument("targets", nargs="+")
ap.add_argument("--rate", type=float, default=20.0)
ap.add_argument("--timeout", type=float, default=5.0)
a = ap.parse_args()

stop = threading.Event()
signal.signal(signal.SIGTERM, lambda *_: stop.set())
signal.signal(signal.SIGINT, lambda *_: stop.set())
rows = queue.Queue()
pool = ThreadPoolExecutor(max_workers=200)


def hit(svc, url):
    t0 = time.time()
    status, pol, att, st, err = 0, "", "", "", ""
    try:
        with urllib.request.urlopen(url, timeout=a.timeout) as r:
            status = r.status
            h = r.headers
            r.read()
    except urllib.error.HTTPError as e:
        status, h = e.code, e.headers
    except Exception as e:  # 연결 거부, 리셋, 타임아웃
        h, err = None, type(e).__name__ + ":" + str(e)[:60]
    if h is not None:
        pol, att, st = h.get("X-Policy", ""), h.get("X-Attempts", ""), h.get("X-Starter", "")
    rows.put((f"{t0:.3f}", svc, status, pol, att, st, int((time.time() - t0) * 1000), err))


def schedule(svc, port):
    url = f"http://127.0.0.1:{port}/work"
    gap = 1.0 / a.rate
    nxt = time.time()
    while not stop.is_set():
        pool.submit(hit, svc, url)
        nxt += gap
        d = nxt - time.time()
        if d > 0:
            time.sleep(d)


def writer():
    with open(a.out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["t", "svc", "status", "policy", "attempts", "starter", "ms", "err"])
        while not (stop.is_set() and rows.empty()):
            try:
                w.writerow(rows.get(timeout=0.5))
            except queue.Empty:
                pass


wt = threading.Thread(target=writer)
wt.start()
ts = [threading.Thread(target=schedule, args=t.split("=")) for t in a.targets]
for t in ts:
    t.start()
for t in ts:
    t.join()
pool.shutdown(wait=True)
stop.set()
wt.join()
print("loadgen done", a.out, file=sys.stderr)
