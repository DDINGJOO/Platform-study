#!/usr/bin/env python3
"""로그 생성기. shop-src 의 자바 소스에서 log.xxx("...") 문장을 읽어, 그 형식 문자열에
변수(GUID, 사용자 이름, 숫자, IP 등)를 채워 표준 출력으로 찍는다. Alloy 가 도커 로그를 읽어 Loki 로 보낸다.

실행 구간은 둘이다.
  정상 구간  NORMAL_SECONDS 동안. 두 인스턴스 모두 평소 문장만 찍는다
  장애 구간  INCIDENT_SECONDS 동안. FAULT=1 인 인스턴스만 장애 문장(주소 조회 타임아웃 등)을 섞는다
구간 경계 시각은 /out/phase-<INSTANCE>.json 에 남긴다(분석 스크립트가 쓴다).
"""
import json, os, random, re, sys, time, uuid
from datetime import datetime, timezone

SRC = os.environ.get("SRC_DIR", "/src")
INSTANCE = os.environ.get("INSTANCE", "app")
FAULT = os.environ.get("FAULT", "0") == "1"
RATE = float(os.environ.get("RATE", "85"))
NORMAL_S = float(os.environ.get("NORMAL_SECONDS", "300"))
INCIDENT_S = float(os.environ.get("INCIDENT_SECONDS", "300"))
rnd = random.Random(int(os.environ.get("SEED", "1")))

STMT = re.compile(r'log\.(info|warn|error|debug)\("((?:[^"\\]|\\.)*)"')
statements = []
for root, _, files in os.walk(SRC):
    for fn in sorted(files):
        if not fn.endswith(".java"):
            continue
        path = os.path.join(root, fn)
        pkg = None
        for i, line in enumerate(open(path), 1):
            if line.startswith("package "):
                pkg = line.split()[1].rstrip(";")
            m = STMT.search(line)
            if m:
                statements.append({"logger": f"{pkg}.{fn[:-5]}", "level": m.group(1).upper(),
                                   "fmt": m.group(2), "where": f"{os.path.relpath(path, SRC)}:{i}"})

# 평소 비중. 이름에 없는 문장은 1. DEBUG 는 운영 로그 수준(INFO)에서 안 나오니 0
NORMAL_W = {
    "completed with status": 30, "created for user": 8, "confirmed, total": 7, "Payment {} authorized": 7,
    "Reserved {} units": 7, "Cache miss": 4, "Shipping label": 4, "Session {} for user": 3, "Heartbeat": 1,
    "GC {} pause": 1, "Low stock": 1, "Refund {}": 1, "cancelled by user": 1, "Payment declined": 1,
    "Loaded State Index": 1, "address updated": 1, "Rejected request": 0.5, "slowly": 0.3,
    "Postal Code Missing": 0.3, "invoice service returned": 0.2,
    "Error loading State Index": 0.02,
    # 장애 문장: 평소에는 나오지 않는다
    "Address Missing": 0, "timed out after {} ms (endpoint": 0, "Retrying address lookup": 0,
    "Connection is not available": 0, "failed with HTTP": 0,
}
# 고장 인스턴스의 장애 구간에서 더해지는 비중
FAULT_W = {"timed out after {} ms (endpoint": 9, "Retrying address lookup": 12, "Address Missing": 6,
           "Connection is not available": 5, "Cache miss": 6}


def weight(st, incident):
    if st["level"] == "DEBUG":
        return 0
    w = 1.0
    for k, v in NORMAL_W.items():
        if k in st["fmt"]:
            w = v
            break
    if incident and FAULT:
        for k, v in FAULT_W.items():
            if k in st["fmt"]:
                w += v
    return w


NAMES = [a + b for a in ["kim", "lee", "park", "choi", "jung", "kang", "cho", "yoon", "jang", "lim",
                         "han", "oh", "seo", "shin", "kwon", "hwang", "ahn", "song", "ryu", "hong"]
         for b in ["", ".j", ".s", ".h", ".m", ".y", ".k", ".w", ".b", ".d", ".e", ".n", ".r", ".t",
                   ".a", ".c", ".g", ".l", ".p", ".x", "1", "2", "3", "77", "_dev"]]
STATES = ["Alabama", "Alaska", "Arizona", "California", "Colorado", "Florida", "Georgia", "Hawaii",
          "Idaho", "Kansas", "Maine", "Nevada", "New York", "North Carolina", "Ohio", "Oregon", "Texas",
          "Utah", "Vermont", "West Virginia"]
REGIONS = ["seoul", "busan", "incheon", "daegu", "gwangju", "daejeon", "ulsan", "jeju"]
PATHS = ["/orders", "/orders/{id}", "/cart", "/payments", "/customers/{id}", "/stock/{sku}"]
REASONS = ["changed mind", "found cheaper", "delivery too slow", "duplicate order"]


def value(before, after):
    b = before.rstrip().split(" ")[-1].lower().lstrip("(") if before.strip() else ""
    a = after.strip().split(" ")[0].lower() if after.strip() else ""
    pool = int(os.environ.get("DB_POOL_MAX", "50"))
    if before.endswith("("):
        return str(rnd.randint(1000, 90000))
    if b == "threshold":
        return "500"
    if b == "after" and a == "minutes":
        return str(rnd.randint(5, 60))
    if b == "attempt":
        return str(rnd.randint(1, 3))
    if b == "of" and a.startswith(")"):
        return "3"
    if b == "total=":
        return str(pool)
    if b == "active=":
        return str(pool)
    if b == "idle=":
        return "0"
    if b == "waiting=":
        return str(rnd.randint(1, 40))
    if b == "with" and a == "items":
        return str(rnd.randint(1, 6))
    if a == "krw":
        return str(rnd.randint(5, 400) * 100)
    if b == "after" and "Address lookup" in before:
        return os.environ.get("ADDRESS_TIMEOUT_MS", "800")
    if b == "after" and "Connection" in before:
        return "30000"
    if b in ("order", "payment", "refund", "customer", "session"):
        return str(uuid.UUID(int=rnd.getrandbits(128), version=4))
    if b == "user":
        return rnd.choice(NAMES)
    if b == "from":
        return f"203.0.113.{rnd.randint(1, 254)}"
    if b == "region":
        return rnd.choice(REGIONS)
    if b == "index":
        return str(rnd.randint(1, 50))
    if b == "-":
        return rnd.choice(STATES)
    if b == "status":
        return rnd.choice(["200", "200", "200", "201", "204", "404"])
    if b == "endpoint":
        return os.environ.get("ADDRESS_SERVICE_URL", "http://address:8080")
    if b == "of" and a == "in":
        return f"SKU-{rnd.randint(1000, 9999)}"
    if b == "for" and a.startswith(":"):
        return f"SKU-{rnd.randint(1000, 9999)}"
    if b == "code":
        return rnd.choice(["05", "14", "51", "54"])
    if b == "gc":
        return rnd.choice(["G1 Young Generation", "G1 Concurrent GC"])
    if b in ("", "request"):
        return rnd.choice(["GET", "POST", "PUT"])
    if b == "default":
        return rnd.choice(REGIONS)
    if b in ("get", "post", "put"):
        return rnd.choice(PATHS)
    if before.endswith(": ") and "cancelled" in before:
        return rnd.choice(REASONS)
    if a.startswith("ms") or b in ("after", "slowly:"):
        return str(rnd.randint(3, 900) if not b == "after" else rnd.choice([3000, 5000]))
    if b == "warehouse":
        return rnd.choice(["W1", "W2", "W3"])
    return str(rnd.randint(1, 500))


def render(st):
    parts = st["fmt"].split("{}")
    out = parts[0]
    for i in range(1, len(parts)):
        out += value(out, parts[i]) + parts[i]
    return out


def emit(st):
    now = datetime.now(timezone.utc)
    ts = now.strftime("%Y-%m-%d %H:%M:%S.") + f"{now.microsecond // 1000:03d}"
    thread = f"nio-8080-exec-{rnd.randint(1, 10)}"
    sys.stdout.write(f"{ts} {st['level']:>5} 1 --- [{thread:>16}] {st['logger']:<40} : {render(st)}\n")


def main():
    OUT = os.environ.get("OUT_DIR", "/out"); os.makedirs(OUT, exist_ok=True)
    t0 = time.time()
    boundary = t0 + NORMAL_S
    end = boundary + INCIDENT_S
    json.dump({"instance": INSTANCE, "start": t0, "boundary": boundary, "end": end, "fault": FAULT,
               "statements": len(statements)}, open(f"{OUT}/phase-{INSTANCE}.json", "w"))
    weights = {False: [weight(s, False) for s in statements], True: [weight(s, True) for s in statements]}
    n = 0
    while True:
        now = time.time()
        if now >= end:
            break
        due = int((now - t0) * RATE)
        incident = now >= boundary
        while n < due:
            emit(rnd.choices(statements, weights=weights[incident])[0])
            n += 1
        sys.stdout.flush()
        time.sleep(0.05)
    sys.stderr.write(f"done: {n} lines\n")
    json.dump({"instance": INSTANCE, "start": t0, "boundary": boundary, "end": end, "fault": FAULT,
               "statements": len(statements), "lines": n}, open(f"{OUT}/phase-{INSTANCE}.json", "w"))
    while True:                       # 컨테이너를 남겨 둔다(env 비교에 쓴다)
        time.sleep(3600)


if __name__ == "__main__":
    main()
