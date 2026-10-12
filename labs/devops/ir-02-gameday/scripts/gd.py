#!/usr/bin/env python3
"""게임데이 도구. 장애 주입·완화·복구 명령을 실행하면서 그 시각을 raw/events.jsonl 에 남긴다.
Grafana 에도 같은 시각에 주석(annotation)을 단다. 표준 라이브러리만 쓴다.

  gd.py event <kind> <note>              사람이 한 일(판단, 공지 등)을 기록만 한다
  gd.py inject <latency_ms> <jitter_ms>  재고 경로에 지연 독(toxic)을 건다
  gd.py heal                             독을 걷는다
  gd.py fallback on|off                  주문 서비스의 완화 스위치(재고 확인 보류)
  gd.py diag                             운영 절차서 2단계: 지표 네 개를 한 번에 본다
  gd.py wait <alertname> firing|resolved [timeout_s]   웹훅에 그 알림이 올 때까지 기다린다
  gd.py settle [timeout_s]               마지막 start 이후 울린 경고가 모두 resolved 알림까지 받을 때까지 기다린다
"""
import json, os, sys, time, urllib.request, urllib.parse

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(HERE, "raw")
PROM = os.environ.get("PROM_URL", "http://localhost:28090")
TOXI = os.environ.get("TOXI_URL", "http://localhost:28474")
ORDER = os.environ.get("ORDER_URL", "http://localhost:28080")
GRAFANA = os.environ.get("GRAFANA_URL", "http://localhost:28030")


def http(method, url, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode()


def log(kind, note):
    t = time.time()
    os.makedirs(RAW, exist_ok=True)
    with open(os.path.join(RAW, "events.jsonl"), "a") as f:
        f.write(json.dumps({"t": t, "kind": kind, "note": note}, ensure_ascii=False) + "\n")
    try:
        http("POST", f"{GRAFANA}/api/annotations", {"time": int(t * 1000), "tags": ["gameday", kind], "text": f"{kind}: {note}"})
    except Exception as e:
        print("annotation failed:", e, file=sys.stderr)
    print(f"{time.strftime('%H:%M:%S')} [{kind}] {note}")


def q(expr):
    r = json.loads(http("GET", f"{PROM}/api/v1/query?" + urllib.parse.urlencode({"query": expr})))
    return r["data"]["result"]


def val(expr):
    res = q(expr)
    return float(res[0]["value"][1]) if res else float("nan")


def main():
    cmd, args = sys.argv[1], sys.argv[2:]
    if cmd == "event":
        log(args[0], " ".join(args[1:]))
    elif cmd == "inject":
        lat, jit = int(args[0]), int(args[1])
        http("POST", f"{TOXI}/proxies/inventory/toxics",
             {"name": "slow", "type": "latency", "stream": "downstream", "toxicity": 1.0,
              "attributes": {"latency": lat, "jitter": jit}})
        log("inject", f"inventory 경로 latency={lat}ms jitter={jit}ms")
    elif cmd == "heal":
        http("DELETE", f"{TOXI}/proxies/inventory/toxics/slow")
        log("repair", "inventory 경로 지연 독 제거")
    elif cmd == "fallback":
        on = args[0] == "on"
        http("POST", f"{ORDER}/admin/fallback?on={1 if on else 0}")
        log("mitigate" if on else "restore", f"order fallback {'켬(재고 확인 보류)' if on else '끔(정상 경로)'}")
    elif cmd == "diag":
        m = {
            "주문 실패율(1m)": val("order:error_ratio:rate1m"),
            "주문 서버 p99(s)": val('histogram_quantile(0.99, sum by (le) (rate(http_server_duration_seconds_bucket{service="order"}[1m])))'),
            "order가 본 재고 호출 p99(s)": val('histogram_quantile(0.99, sum by (le) (rate(upstream_duration_seconds_bucket{service="order"}[1m])))'),
            "재고 서버 자체 p99(s)": val('histogram_quantile(0.99, sum by (le) (rate(http_server_duration_seconds_bucket{service="inventory"}[1m])))'),
        }
        outcomes = {r["metric"]["outcome"]: round(float(r["value"][1]), 2)
                    for r in q('sum by (outcome) (rate(upstream_requests_total{service="order"}[1m]))')}
        note = ", ".join(f"{k}={v:.3f}" for k, v in m.items()) + f", 재고 호출 결과/초={outcomes}"
        log("diagnose", note)
    elif cmd == "wait":
        name, want = args[0], args[1]
        timeout = float(args[2]) if len(args) > 2 else 900
        path = os.path.join(RAW, "notifications.jsonl")
        start_lines = sum(1 for _ in open(path)) if os.path.exists(path) else 0
        t0 = time.time()
        while time.time() - t0 < timeout:
            if os.path.exists(path):
                lines = open(path).read().splitlines()[start_lines:]
                for ln in lines:
                    rec = json.loads(ln)
                    if any(a["alertname"] == name and a["status"] == want for a in rec["alerts"]):
                        print(f"{time.strftime('%H:%M:%S')} 알림 도착: {name} {want}")
                        return
            time.sleep(1)
        sys.exit(f"timeout waiting {name} {want}")
    elif cmd == "settle":
        # 마지막 start 이후 firing 알림을 받은 경고마다 resolved 알림이 올 때까지 기다린다
        t_start = [json.loads(l)["t"] for l in open(os.path.join(RAW, "events.jsonl")) if '"kind": "start"' in l][-1]
        path = os.path.join(RAW, "notifications.jsonl")
        timeout = float(args[0]) if args else 1e9
        t0 = time.time()
        while True:
            if time.time() - t0 > timeout:
                sys.exit(f"{time.strftime('%H:%M:%S')} settle timeout: resolved 알림이 오지 않음")
            fired, resolved = set(), set()
            for ln in open(path):
                rec = json.loads(ln)
                if rec["received"] < t_start:
                    continue
                for a in rec["alerts"]:
                    (fired if a["status"] == "firing" else resolved).add(a["alertname"])
            if fired <= resolved:
                print(f"{time.strftime('%H:%M:%S')} 정리됨: firing {sorted(fired)} 모두 resolved 알림 받음")
                return
            time.sleep(3)
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
