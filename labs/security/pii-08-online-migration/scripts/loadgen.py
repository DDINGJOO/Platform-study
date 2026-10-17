#!/usr/bin/env python3
"""부하 생성기. 배포가 진행되는 동안 쉬지 않고 요청을 보내고, 요청마다 결과를 판정한다.

  ok        200 이고 돌려받은 값이 기대값과 같다
  fail      5xx 또는 연결 오류 (사용자가 오류 화면을 본다)
  mismatch  200 인데 값이 틀렸다 (사용자가 암호문이나 남의 값을 본다)

풀(state/pool)은 "port:version:pid" 줄 목록이다. 롤링 배포 스크립트가 이 파일을 바꾸면 0.2초 안에 따라간다.
기대값은 시작 시점(전부 평문) 덤프를 쓰고, 값을 바꾸는 요청은 그 id 를 맡은 작업자만 보낸다.
"""
import argparse, collections, csv, http.client, json, os, random, threading, time, urllib.parse

ap = argparse.ArgumentParser()
ap.add_argument("--state", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--expected", required=True)
ap.add_argument("--workers", type=int, default=8)
ap.add_argument("--rps-per-worker", type=float, default=40)
a = ap.parse_args()

N_WRITER_IDS = 800
expected = {}
with open(a.expected, encoding="utf-8") as f:
    for line in f:
        r = json.loads(line)
        expected[r["id"]] = r["rrn"]
MAX_ID = max(expected)

pool = []
pool_lock = threading.Lock()
phase = ["?"]
T0 = time.monotonic()
records = []
rec_lock = threading.Lock()
stop_path = os.path.join(a.state, "stop")


def refresher():
    while not os.path.exists(stop_path):
        try:
            with open(os.path.join(a.state, "pool")) as f:
                p = [ln.strip().split(":") for ln in f if ln.strip()]
            with pool_lock:
                pool[:] = p
            with open(os.path.join(a.state, "phase")) as f:
                phase[0] = f.read().strip()
        except (FileNotFoundError, ValueError):
            pass
        time.sleep(0.2)


def worker(k):
    rnd = random.Random(k)
    conns = {}
    own = [i for i in range(1, N_WRITER_IDS + 1) if (i - 1) % a.workers == k]
    uncertain = {}  # 값을 바꾸다 실패한 id -> (옛 값, 새 값)
    rr = k
    pid_of = {}
    interval = 1.0 / a.rps_per_worker

    lat = [0.0]
    t_req = [0.0]

    def call(method, port, path):
        # 연결은 인스턴스(PID)마다 따로 둔다. 같은 포트를 새 인스턴스가 다시 쓸 때 끊긴 옛 연결을 재사용하지 않게
        key = port + ":" + pid_of.get(port, "?")
        t_req[0] = time.monotonic()
        lat[0] = 0.0
        c = conns.get(key)
        if c is None:
            c = http.client.HTTPConnection("127.0.0.1", int(port), timeout=5)
            conns[key] = c
        try:
            c.request(method, path)
            resp = c.getresponse()
            body = resp.read()
            lat[0] = (time.monotonic() - t_req[0]) * 1000
            return resp.status, body
        except Exception:
            c.close()
            conns.pop(key, None)
            lat[0] = (time.monotonic() - t_req[0]) * 1000
            return "ERR", b""

    def record(port, ver, op, status, verdict, ph):
        with rec_lock:
            records.append((round(time.monotonic() - T0, 3), ph, port, ver, op, status, verdict, round(lat[0], 1)))

    while not os.path.exists(stop_path):
        t_start = time.monotonic()
        with pool_lock:
            p = list(pool)
        pid_of = {e[0]: e[2] for e in p}
        if not p:
            time.sleep(0.05)
            continue
        rr += 1
        port, ver = p[rr % len(p)][:2]
        ph = phase[0]
        x = rnd.random()
        if x < 0.55:                                   # 한 건 조회
            i = rnd.randint(N_WRITER_IDS + 1, MAX_ID)
            st, body = call("GET", port, "/agents/%d" % i)
            if st != 200:
                record(port, ver, "get", st, "fail", ph)
            else:
                v = json.loads(body)["rrn"]
                record(port, ver, "get", st, "ok" if v == expected[i] else "mismatch", ph)
        elif x < 0.70:                                 # 목록 한 페이지
            i = rnd.randint(N_WRITER_IDS + 1, MAX_ID - 20)
            st, body = call("GET", port, "/agents?from=%d&limit=20" % i)
            if st != 200:
                record(port, ver, "list", st, "fail", ph)
            else:
                rows = json.loads(body)
                bad = any(r["rrn"] != expected[r["id"]] for r in rows)
                record(port, ver, "list", st, "mismatch" if bad else "ok", ph)
        elif x < 0.90:                                 # 로그인: 모든 컬럼을 다시 쓰는 UPDATE
            i = rnd.randint(N_WRITER_IDS + 1, MAX_ID)
            st, _ = call("POST", port, "/agents/%d/login" % i)
            record(port, ver, "login", st, "ok" if st == 200 else "fail", ph)
        else:                                          # 값 변경 후 다시 읽기 (다른 대로 갈 수 있다)
            i = rnd.choice(own)
            nv = "000000-%07d" % rnd.randint(0, 9999999)
            st, _ = call("POST", port, "/agents/%d/rrn?v=%s" % (i, urllib.parse.quote(nv)))
            if st == 200:
                expected[i] = nv
                uncertain.pop(i, None)
                record(port, ver, "update", st, "ok", ph)
            else:
                uncertain[i] = (expected[i], nv)
                record(port, ver, "update", st, "fail", ph)
            with pool_lock:
                p2 = list(pool)
            if p2:
                port2, ver2 = p2[(rr + 1) % len(p2)][:2]
                st2, body2 = call("GET", port2, "/agents/%d" % i)
                if st2 != 200:
                    record(port2, ver2, "readback", st2, "fail", ph)
                else:
                    v = json.loads(body2)["rrn"]
                    okset = uncertain.get(i, (expected[i],))
                    if v in okset:
                        expected[i] = v
                        uncertain.pop(i, None)
                    record(port2, ver2, "readback", st2, "ok" if v in okset else "mismatch", ph)
        dt = time.monotonic() - t_start
        if dt < interval:
            time.sleep(interval - dt)


threading.Thread(target=refresher, daemon=True).start()
time.sleep(0.3)
ts = [threading.Thread(target=worker, args=(k,)) for k in range(a.workers)]
for t in ts:
    t.start()
for t in ts:
    t.join()

with open(a.out, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["t", "phase", "port", "version", "op", "status", "verdict", "ms"])
    w.writerows(records)

by = collections.OrderedDict()
lats = collections.defaultdict(list)
for r in records:
    by.setdefault(r[1], collections.Counter())[r[6]] += 1
    lats[r[1]].append(r[7])


def pct(xs, q):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(len(xs) * q))] if xs else 0


print("%-26s %7s %7s %5s %8s %7s %8s" % ("phase", "total", "ok", "fail", "mismatch", "p99ms", "maxms"))
for ph, c in by.items():
    print("%-26s %7d %7d %5d %8d %7.0f %8.0f" % (ph, sum(c.values()), c["ok"], c["fail"], c["mismatch"],
                                                pct(lats[ph], 0.99), max(lats[ph])))
tot = collections.Counter(r[6] for r in records)
print("%-26s %7d %7d %5d %8d" % ("TOTAL", sum(tot.values()), tot["ok"], tot["fail"], tot["mismatch"]))
