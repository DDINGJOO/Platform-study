"""실습-4 측정 스크립트. compose 네트워크 안의 load 컨테이너에서 돈다.

python experiment.py shared    [--betas 0,0.1,0.5,1] [--slots 6000]   # A. 공통 원인 비율별 가용성
python experiment.py failover  [--trials 6]                           # B. 액티브-스탠바이 전환 시간
python experiment.py checks    [--seconds 30]                         # C. TCP 검사 vs 앱 검사
python experiment.py all
결과: /out/<실험>.jsonl, 요청 원자료는 /out/raw/
"""
import argparse, csv, http.client as hc, io, json, math, os, random, socket, threading, time

OUT = os.environ.get("OUT_DIR", "/out")
HAP = os.environ.get("HAPROXY", "haproxy")
REDIS = os.environ.get("REDIS", "redis:6379")


# ---------- 공통 ----------
def hreq(host, port, method, path, timeout=2):
    c = hc.HTTPConnection(host, port, timeout=timeout)
    c.request(method, path); r = c.getresponse(); b = r.read(); c.close()
    return r.status, b


def set_state(name, s):
    hreq(name, 8080, "POST", f"/admin/state?s={s}")


def redis_cmd(*args):
    s = socket.create_connection(tuple([REDIS.split(":")[0], int(REDIS.split(":")[1])]), timeout=1)
    payload = f"*{len(args)}\r\n" + "".join(f"${len(a)}\r\n{a}\r\n" for a in args)
    s.sendall(payload.encode()); s.recv(1024); s.close()


def write(name, row):
    os.makedirs(OUT, exist_ok=True)
    with open(f"{OUT}/{name}.jsonl", "a") as f:
        f.write(json.dumps(row) + "\n")
    print(json.dumps(row)[:400], flush=True)


class Load:
    """포트마다 초당 rate 건을 일정 간격으로 보낸다. 요청마다 (보낸 시각, 포트, 상태, 걸린 시간)을 남긴다."""

    def __init__(self, ports, rate, threads_per_port=4):
        self.ports, self.rate, self.k = ports, rate, threads_per_port
        self.rec = []; self.lock = threading.Lock(); self.stop = False; self.ts = []

    def _worker(self, port, offset):
        c = hc.HTTPConnection(HAP, port, timeout=10)
        interval = self.k / self.rate
        nxt = time.time() + offset
        while not self.stop:
            now = time.time()
            if now < nxt:
                time.sleep(nxt - now)
            t = time.time()
            try:
                c.request("GET", "/work"); r = c.getresponse(); r.read(); code = r.status
            except (hc.HTTPException, OSError):
                c.close(); c = hc.HTTPConnection(HAP, port, timeout=10); code = 599
            with self.lock:
                self.rec.append((t, port, code, time.time() - t))
            nxt += interval
            if nxt < time.time() - 1:    # 1초 넘게 밀리면 따라잡으려 몰아 보내지 않는다
                nxt = time.time()

    def start(self):
        for p in self.ports:
            for i in range(self.k):
                th = threading.Thread(target=self._worker, args=(p, i / self.rate), daemon=True)
                th.start(); self.ts.append(th)
        return self

    def finish(self):
        self.stop = True
        for t in self.ts: t.join()
        return self.rec


def max_gap(rec):
    ts = sorted(r[0] for r in rec)
    return max((b - a for a, b in zip(ts, ts[1:])), default=0)


def dump_raw(name, rec):
    os.makedirs(f"{OUT}/raw", exist_ok=True)
    with open(f"{OUT}/raw/{name}.csv", "w") as f:
        f.write("t,port,code,latency\n")
        for t, p, c, l in rec:
            f.write(f"{t:.4f},{p},{c},{l:.4f}\n")


def hap_status():
    """HAProxy 통계 CSV 에서 (listen, server) -> status"""
    _, b = hreq(HAP, 8404, "GET", "/stats;csv", timeout=1)
    out = {}
    for row in csv.DictReader(io.StringIO(b.decode().lstrip("# "))):
        out[(row["pxname"], row["svname"])] = row["status"]
    return out


# ---------- A. 공통 원인 비율 ----------
def shared(betas, slots, slot_ms=100, Q=0.1, rate=150, seed=7):
    for beta in betas:
        rng = random.Random(f"{seed}-{beta}")
        c = beta * Q
        q = (Q - c) / (1 - c)
        for r in ("r1", "r2", "r3"):
            set_state(r, "up")
        redis_cmd("SET", "mode", "ok")
        time.sleep(1)
        load = Load([9201, 9202], rate).start()
        sched = []      # (시작, 끝, ccf, [r1, r2, r3 다운 여부])
        cur = {"ccf": False, "down": [False] * 3}
        t_slot = time.time()
        for i in range(slots):
            ccf = rng.random() < c
            down = [rng.random() < q for _ in range(3)]
            t0 = time.time()
            if ccf != cur["ccf"]:
                redis_cmd("SET", "mode", "bad" if ccf else "ok")
            for j, r in enumerate(("r1", "r2", "r3")):
                if down[j] != cur["down"][j]:
                    set_state(r, "down" if down[j] else "up")
            t1 = time.time()
            cur = {"ccf": ccf, "down": down}
            t_slot += slot_ms / 1000
            sched.append((t0, t1, ccf, down))
            if t_slot > time.time():
                time.sleep(t_slot - time.time())
        rec = load.finish()
        for r in ("r1", "r2", "r3"):
            set_state(r, "up")
        redis_cmd("SET", "mode", "ok")
        dump_raw(f"shared-beta{beta}", rec)
        # 요청을 슬롯에 붙인다. 상태를 바꾸는 중(t0~t1)에 보낸 요청은 뺀다.
        import bisect
        starts = [s[0] for s in sched]
        res = {}
        for port in (9201, 9202):
            tot = ok = 0; any_up_tot = any_up_ok = 0; all_down_tot = all_down_ok = 0; trans = 0
            for t, p, code, lat in rec:
                if p != port: continue
                i = bisect.bisect_right(starts, t) - 1
                if i < 0: continue
                t0, t1, ccf, down = sched[i]
                if t < t1:
                    trans += 1; continue
                tot += 1; good = code == 200; ok += good
                alive = (not ccf) and not all(down)
                if alive:
                    any_up_tot += 1; any_up_ok += good
                else:
                    all_down_tot += 1; all_down_ok += good
            res[port] = {"requests": tot, "success": ok / tot, "excluded_in_transition": trans,
                         "share_any_up": any_up_tot / tot,
                         "success_when_any_up": any_up_ok / max(1, any_up_tot),
                         "success_when_all_down": all_down_ok / max(1, all_down_tot)}
        n = len(sched)
        row = {"exp": "shared", "beta": beta, "Q": Q, "slot_ms": slot_ms, "slots": n,
               "theory_availability": 1 - (c + (1 - c) * q ** 3),
               "slot_ccf_ratio": sum(s[2] for s in sched) / n,
               "slot_replica_down_ratio": [sum(s[2] or s[3][j] for s in sched) / n for j in range(3)],
               "slot_any_up_ratio": sum((not s[2]) and not all(s[3]) for s in sched) / n,
               "noretry_9201": res[9201], "retry_9202": res[9202],
               "max_gap_s": round(max_gap(rec), 3),
               "slot_overrun_ms_max": round(max((b[0] - a[0]) * 1000 - slot_ms for a, b in zip(sched, sched[1:])), 1)}
        write("shared", row)


# ---------- B. 액티브-스탠바이 전환 ----------
FO = {9301: "fo_i2f3", 9302: "fo_i1f3", 9303: "fo_i1f2", 9304: "fo_i2f3_fast",
      9305: "fo_i500f3", 9306: "fo_i2f3_redispatch", 9307: "fo_i2f3_observe"}


def wait_up(listens, server="a", limit=30):
    t = time.time()
    while time.time() - t < limit:
        st = hap_status()
        if all(st.get((l, server), "").startswith("UP") for l in listens):
            return True
        time.sleep(0.2)
    return False


def failover(trials, rate=100, hold=15, fault="down"):
    for k in range(trials):
        set_state("a", "up"); set_state("b", "up")
        if not wait_up(FO.values()):
            print("a 가 UP 으로 돌아오지 않았다"); return
        time.sleep(random.uniform(0.5, 2.5))     # 검사 주기와 고장 시점의 위상을 흩뜨린다
        load = Load(list(FO), rate).start()
        time.sleep(2)
        t_fault = time.time()
        set_state("a", fault)
        down_at = {}
        while time.time() - t_fault < hold:
            st = hap_status(); now = time.time()
            for port, l in FO.items():
                if l not in down_at and not st.get((l, "a"), "UP").startswith("UP"):
                    down_at[l] = now - t_fault
            time.sleep(0.05)
        rec = load.finish()
        set_state("a", "up")
        dump_raw(f"failover-{fault}-{k}", rec)
        per = {}
        for port, l in FO.items():
            after = [r for r in rec if r[1] == port and r[0] >= t_fault]
            fails = [r for r in after if r[2] != 200]
            before_fail = sum(1 for r in rec if r[1] == port and r[0] < t_fault and r[2] != 200)
            per[l] = {"failed": len(fails), "sent_after_fault": len(after),
                      "first_fail_s": round(fails[0][0] - t_fault, 3) if fails else None,
                      "last_fail_s": round(max(r[0] for r in fails) - t_fault, 3) if fails else None,
                      "hap_marked_down_s": round(down_at[l], 3) if l in down_at else None,
                      "p99_latency_ms_after": round(sorted(r[3] for r in after)[int(len(after) * 0.99)] * 1000, 1) if after else None,
                      "fail_before_fault": before_fail}
        write("failover", {"exp": "failover", "trial": k, "fault": fault, "rate_per_listen": rate,
                           "max_gap_s": round(max_gap(rec), 3), "listens": per})
        time.sleep(1)


# ---------- C. TCP 검사 vs 앱 검사 ----------
CK = {9401: "chk_tcp", 9402: "chk_http", 9403: "chk_observe"}


def checks(seconds=30, rate=150, faults=("down", "gray")):
    for fault in faults:
        for r in ("r1", "r2", "r3"):
            set_state(r, "up")
        redis_cmd("SET", "mode", "ok")
        if not all(wait_up([l], s) for l in CK.values() for s in ("r1", "r2", "r3")):
            print("UP 으로 돌아오지 않았다"); return
        load = Load(list(CK), rate).start()
        time.sleep(3)
        t_fault = time.time()
        set_state("r1", fault)
        down_at = {}
        while time.time() - t_fault < seconds:
            st = hap_status(); now = time.time()
            for l in CK.values():
                if l not in down_at and not st.get((l, "r1"), "UP").startswith("UP"):
                    down_at[l] = now - t_fault
            time.sleep(0.05)
        rec = load.finish()
        set_state("r1", "up")
        dump_raw(f"checks-{fault}", rec)
        per = {}
        for port, l in CK.items():
            after = [r for r in rec if r[1] == port and r[0] >= t_fault]
            fails = [r for r in after if r[2] != 200]
            per[l] = {"sent": len(after), "failed": len(fails), "fail_ratio": round(len(fails) / max(1, len(after)), 4),
                      "last_fail_s": round(max(r[0] for r in fails) - t_fault, 3) if fails else None,
                      "hap_marked_down_s": round(down_at[l], 3) if l in down_at else None}
        write("checks", {"exp": "checks", "fault": fault, "seconds": seconds, "rate_per_listen": rate,
                         "max_gap_s": round(max_gap(rec), 3), "listens": per})
        time.sleep(5)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("what", choices=["shared", "failover", "checks", "all"])
    ap.add_argument("--betas", default="0,0.1,0.5,1")
    ap.add_argument("--slots", type=int, default=3000)
    ap.add_argument("--trials", type=int, default=6)
    ap.add_argument("--seconds", type=int, default=30)
    ap.add_argument("--fault", default="down")
    a = ap.parse_args()
    if a.what in ("checks", "all"):
        checks(a.seconds)
    if a.what in ("failover", "all"):
        failover(a.trials, fault=a.fault)
    if a.what in ("shared", "all"):
        shared([float(b) for b in a.betas.split(",")], a.slots)


if __name__ == "__main__":
    main()
