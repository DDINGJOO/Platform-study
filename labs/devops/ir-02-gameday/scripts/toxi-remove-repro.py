#!/usr/bin/env python3
"""Toxiproxy 에서 지연 독을 걷을 때 프록시가 멈추는지 되풀이해 본다.
부하(초당 20건)와 주문 서비스의 1초 타임아웃이 걸린 상태에서
  1) 프록시를 새로 띄우고 2) 지연 독을 걸고 3) HOLD 초 뒤 걷고 4) 주문 10건으로 경로를 확인한다.
mode=delete  : DELETE /toxics/<name> 만
mode=disable : 프록시 끄기 → 독 삭제 → 프록시 켜기
결과는 results/toxiproxy-remove/<mode>.jsonl (시각은 각 시도의 시작을 0 으로 둔 상대 초)
  toxi-remove-repro.py <mode> <trials> [hold_s]
"""
import json, os, subprocess, sys, time, urllib.request

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOXI = "http://localhost:28474"
ORDER = "http://localhost:28080/orders"


def call(method, path, body=None, timeout=30):
    t = time.time()
    try:
        req = urllib.request.Request(TOXI + path, method=method,
                                     data=json.dumps(body).encode() if body is not None else None)
        urllib.request.urlopen(req, timeout=timeout).read()
        return {"ok": True, "secs": round(time.time() - t, 3)}
    except Exception as e:
        return {"ok": False, "secs": round(time.time() - t, 3), "err": str(e)[:80]}


def probe(n=10):
    ok = 0
    for _ in range(n):
        try:
            urllib.request.urlopen(urllib.request.Request(ORDER, method="POST", data=b""), timeout=3).read()
            ok += 1
        except Exception:
            pass
        time.sleep(0.2)
    return ok


def main():
    mode, trials = sys.argv[1], int(sys.argv[2])
    hold = float(sys.argv[3]) if len(sys.argv) > 3 else 40
    out = os.path.join(HERE, "results", "toxiproxy-remove")
    os.makedirs(out, exist_ok=True)
    for i in range(1, trials + 1):
        subprocess.run(["docker", "compose", "restart", "toxiproxy"], cwd=HERE, capture_output=True)
        time.sleep(15)
        t0 = time.time()
        rec = {"mode": mode, "trial": i, "hold_s": hold, "before_ok_of_10": probe()}
        rec["add"] = call("POST", "/proxies/inventory/toxics",
                          {"name": "slow", "type": "latency", "stream": "downstream",
                           "attributes": {"latency": 900, "jitter": 300}})
        time.sleep(hold)
        rec["during_ok_of_10"] = probe()
        if mode == "delete":
            rec["delete"] = call("DELETE", "/proxies/inventory/toxics/slow")
        else:
            rec["disable"] = call("POST", "/proxies/inventory", {"enabled": False})
            rec["delete"] = call("DELETE", "/proxies/inventory/toxics/slow")
            rec["enable"] = call("POST", "/proxies/inventory", {"enabled": True})
        time.sleep(10)
        rec["after_ok_of_10"] = probe()
        rec["toxics_listed_after"] = json.loads(urllib.request.urlopen(TOXI + "/proxies/inventory/toxics", timeout=10).read()) if True else None
        rec["elapsed_s"] = round(time.time() - t0, 1)
        print(json.dumps(rec, ensure_ascii=False), flush=True)
        with open(os.path.join(out, f"{mode}.jsonl"), "a") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
