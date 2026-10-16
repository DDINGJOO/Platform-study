"""실습-3 측정 스크립트. compose 네트워크 안의 load 컨테이너에서 돈다.

python experiment.py chain    --retry none|hop|edge --mode random|slotted [--requests N | --seconds S]
python experiment.py parallel --pick first|failover [--requests N]
python experiment.py all      # 글에 실은 측정 전부. 결과는 /out/*.jsonl, /out/summary.txt

체인: h1 -> h2 -> ... -> h6. 길이 N 체인은 h(7-N) 로 들어가서 h6 까지 간다.
병렬: pf -> (r1, r2, r3)
"""
import argparse, hashlib, http.client, json, os, threading, time, sys

CHAIN = [f"h{i}" for i in range(1, 7)]
REPL = ["r1", "r2", "r3"]
OUT = os.environ.get("OUT_DIR", "/out")
# 컨테이너 밖에서 돌릴 때만 쓴다: ADDR='{"h1": "127.0.0.1:33101", ...}'
ADDR = json.loads(os.environ.get("ADDR", "{}"))


def conn(name, timeout=10):
    host, _, port = ADDR.get(name, f"{name}:8080").partition(":")
    return http.client.HTTPConnection(host, int(port), timeout=timeout)


def req(host, method, path):
    c = conn(host)
    c.request(method, path); r = c.getresponse(); b = r.read(); c.close()
    return json.loads(b) if b.startswith(b"{") else b


def config(hosts, **kw):
    q = "&".join(f"{k}={v}" for k, v in kw.items())
    for h in hosts:
        req(h, "POST", "/config?" + q)


def reset(hosts):
    for h in hosts:
        req(h, "POST", "/reset")


def stats(hosts):
    return {h: req(h, "GET", "/stats") for h in hosts}


def load(entry, n=None, seconds=None, conc=16, edge_retries=0, rate=None):
    """entry 로 GET /work 를 보낸다. 사용자 요청 하나에 최대 1+edge_retries 번 시도."""
    lock = threading.Lock()
    res = {"users": 0, "ok": 0, "attempts": 0, "codes": {}}
    gaps = []; lats = []; sends = []
    stop_at = time.time() + seconds if seconds else None
    left = [n]

    def take():
        with lock:
            if stop_at:
                return time.time() < stop_at
            if left[0] <= 0:
                return False
            left[0] -= 1
            return True

    def worker():
        c = conn(entry)
        last = time.time()
        nxt = time.time()
        while take():
            if rate:   # 정해진 속도로 보낸다(실패가 빨리 끝나도 요청이 몰리지 않게)
                nxt += conc / rate
                d = nxt - time.time()
                if d > 0: time.sleep(d)
            ok = False
            t_user = time.time()
            for _ in range(1 + edge_retries):
                try:
                    c.request("GET", "/work"); r = c.getresponse(); r.read(); code = r.status
                except (http.client.HTTPException, OSError):
                    c.close(); c = conn(entry); code = 599
                with lock:
                    res["attempts"] += 1
                    res["codes"][code] = res["codes"].get(code, 0) + 1
                if code == 200:
                    ok = True
                    break
            now = time.time()
            with lock:
                res["users"] += 1; res["ok"] += ok
                gaps.append(now - last); lats.append((now - t_user, ok)); sends.append((t_user, ok))
            last = now

    t0 = time.time()
    ts = [threading.Thread(target=worker) for _ in range(conc)]
    for t in ts: t.start()
    for t in ts: t.join()
    res["elapsed"] = round(time.time() - t0, 2)
    res["max_gap_s"] = round(max(gaps), 3) if gaps else None
    res["rps"] = round(res["users"] / res["elapsed"], 1)
    res["success"] = res["ok"] / res["users"]
    def q(xs, p):
        xs = sorted(xs); return round(xs[min(len(xs) - 1, int(len(xs) * p))] * 1000, 1) if xs else None
    allv = [l for l, _ in lats]; okv = [l for l, o in lats if o]
    res["lat_ms"] = {"p50": q(allv, 0.5), "p99": q(allv, 0.99), "p999": q(allv, 0.999), "max": q(allv, 1.0),
                     "ok_p99": q(okv, 0.99), "ok_p999": q(okv, 0.999)}
    res["_sends"] = sends
    return res


def slot_down(name, slot, fail, seed="1"):
    h = hashlib.blake2b(f"{seed}:{name}:{slot}".encode(), digest_size=8).digest()
    return int.from_bytes(h, "big") / 2**64 < fail


def realized(hosts, t0, t1, fail, slot_ms):
    """실행 구간의 슬롯 일정으로 계산한 '모든 홉이 살아 있던 시간 비율'과 홉별 다운 시간 비율"""
    s0, s1 = int(t0 * 1000) // slot_ms, int(t1 * 1000) // slot_ms
    slots = range(s0, s1 + 1)
    down = {h: [slot_down(h, s, fail) for s in slots] for h in hosts}
    all_up = sum(not any(down[h][i] for h in hosts) for i in range(len(slots))) / len(slots)
    return all_up, [round(sum(down[h]) / len(slots), 5) for h in hosts], len(slots)


def write(name, row):
    os.makedirs(OUT, exist_ok=True)
    with open(f"{OUT}/{name}.jsonl", "a") as f:
        f.write(json.dumps(row) + "\n")
    print(json.dumps(row), flush=True)


def chain(retry, mode, n_req=None, seconds=None, ns=range(1, 7), fail=0.01, slot_ms=100, rate=None):
    hop_retries = 1 if retry == "hop" else 0
    edge = 1 if retry == "edge" else 0
    config(CHAIN, fail_rate=fail, mode=mode, retries=hop_retries, slot_ms=slot_ms, pick="first")
    for n in ns:
        hosts = CHAIN[6 - n:]
        reset(CHAIN)
        t0 = time.time()
        r = load(hosts[0], n=n_req, seconds=seconds, edge_retries=edge, rate=rate)
        t1 = time.time()
        st = stats(hosts)
        row = {"exp": "chain", "retry": retry, "mode": mode, "fail_rate": fail, "slot_ms": slot_ms, "N": n,
               **{k: r[k] for k in ("users", "ok", "attempts", "success", "elapsed", "rps", "max_gap_s", "codes", "lat_ms")},
               "theory_no_retry": (1 - fail) ** n,
               "received_per_user": [round(st[h]["received"] / r["users"], 4) for h in hosts],
               "own_fail_ratio": [round(st[h]["own_fail"] / max(1, st[h]["received"]), 5) for h in hosts],
               "reconnect": sum(st[h]["reconnect"] for h in hosts), "rate_limit": rate}
        if mode == "slotted":
            au, dr, ns_ = realized(hosts, t0, t1, fail, slot_ms)
            row.update({"slots": ns_, "time_all_up": au, "time_down_ratio": dr})
            # 요청을 '보낸 순간 모든 홉이 살아 있었나'로 나눠 성공률을 따로 센다
            up_n = up_ok = dn_n = dn_ok = 0
            for t, ok in r["_sends"]:
                sl = int(t * 1000) // slot_ms
                if any(slot_down(h, sl, fail) for h in hosts):
                    dn_n += 1; dn_ok += ok
                else:
                    up_n += 1; up_ok += ok
            row.update({"sent_while_all_up": up_n / r["users"], "success_sent_all_up": up_ok / max(1, up_n),
                        "success_sent_some_down": dn_ok / max(1, dn_n), "sent_some_down": dn_n})
        write("chain", row)


def parallel(pick, n_req, fail=0.1, mode="random"):
    config(REPL, fail_rate=fail, mode=mode, retries=0)
    config(["pf"], fail_rate=0, retries=0, pick=pick)
    reset(REPL + ["pf"])
    r = load("pf", n=n_req)
    st = stats(REPL + ["pf"])
    row = {"exp": "parallel", "pick": pick, "mode": mode, "fail_rate": fail,
           **{k: r[k] for k in ("users", "ok", "success", "elapsed", "rps", "max_gap_s", "codes")},
           "fail_count": r["users"] - r["ok"],
           "replica_calls_per_user": round(st["pf"]["down_calls"] / r["users"], 4),
           "replica_fail_ratio": [round(st[h]["own_fail"] / max(1, st[h]["received"]), 5) for h in REPL],
           "reconnect": sum(st[h]["reconnect"] for h in REPL + ["pf"])}
    write("parallel", row)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("what", choices=["chain", "parallel", "all"])
    ap.add_argument("--retry", default="none"); ap.add_argument("--mode", default="random")
    ap.add_argument("--pick", default="failover")
    ap.add_argument("--requests", type=int); ap.add_argument("--seconds", type=int)
    ap.add_argument("--rate", type=int); ap.add_argument("--n", default="1,2,3,4,5,6")
    ap.add_argument("--slot-ms", type=int, default=100)
    a = ap.parse_args()
    if a.what == "chain":
        chain(a.retry, a.mode, a.requests or (None if a.seconds else 20000), a.seconds,
              ns=[int(x) for x in a.n.split(",")], rate=a.rate, slot_ms=a.slot_ms)
    elif a.what == "parallel":
        parallel(a.pick, a.requests or 100000)
    else:
        for retry in ("none", "hop", "edge"):
            chain(retry, "random", 100000)
        chain("none", "slotted", seconds=120, ns=[6])          # 속도 제한 없이(닫힌 고리) 한 번
        for retry in ("none", "hop", "edge"):
            chain(retry, "slotted", seconds=240, ns=[6], rate=1000)
        parallel("first", 300000)
        parallel("failover", 300000)


if __name__ == "__main__":
    main()
