#!/usr/bin/env python3
"""정상 상태 가설을 확인하고, 카오스를 걸고, 가설이 깨지면 스스로 멈추는 실험 실행기.

    python3 scripts/experiment.py <이름> <카오스.yaml> [--observe 180] [--baseline 60]
                                  [--recover 60] [--no-abort]

정상 상태 가설(loadgen 이 사용자 자리에서 잰 값, 최근 15초 창)
    성공률 >= 99%   그리고   p99 < 250ms

순서
  1. 기준 구간(--baseline 초): 가설이 처음부터 안 맞으면 카오스를 걸지 않고 끝낸다
  2. 카오스 적용 후 --observe 초 동안 5초마다 가설을 잰다.
     연속 2번 깨지면 카오스 객체를 지우고 멈춘다(중단 조건). --no-abort 면 끝까지 지켜본다
  3. 카오스를 지운 뒤 --recover 초 동안 회복을 기록한다

결과
  results/<이름>.tsv       5초마다 한 줄. 시각은 카오스를 건 순간부터의 경과 초
  results/summary.txt      실험마다 한 단락씩 덧붙인다
  results/raw/<이름>-*.txt 카오스 객체 상태와 이벤트(유닉스 시각이 들어 있어 커밋하지 않는다)
"""
import argparse
import json
import os
import subprocess
import sys
import time
import urllib.parse
import urllib.request

PROM = os.environ.get("PROM_URL", "http://localhost:29090")
K = ["kubectl", "--context", "kind-ir-03"]
SUCC_MIN = 0.99
P99_MAX = 0.250
WIN = "15s"
TICK = 5
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")


def q(expr):
    u = PROM + "/api/v1/query?" + urllib.parse.urlencode({"query": expr})
    with urllib.request.urlopen(u, timeout=10) as r:
        return json.load(r)["data"]["result"]


def scalar(expr):
    res = q(expr)
    if not res:
        return None
    v = float(res[0]["value"][1])
    return None if v != v else v   # NaN -> None


def counters():
    """loadgen 의 누적 요청 수(결과별)와 지연 버킷 누적 수"""
    by = {r["metric"]["outcome"]: float(r["value"][1]) for r in q("loadgen_requests_total")}
    buckets = {r["metric"]["le"]: float(r["value"][1]) for r in q("loadgen_request_seconds_bucket")}
    return by, buckets


def quantile(b0, b1, phi):
    """두 시점의 버킷 누적값 차이로 백분위를 낸다. histogram_quantile 과 같은 선형 보간"""
    les = sorted((float(k) if k != "+Inf" else float("inf"), k) for k in b1)
    cum = [(le, b1[k] - b0.get(k, 0)) for le, k in les]
    total = cum[-1][1]
    if total <= 0:
        return None
    rank = phi * total
    prev_le, prev_c = 0.0, 0.0
    for le, c in cum:
        if c >= rank:
            if le == float("inf"):
                return prev_le
            return prev_le + (le - prev_le) * (rank - prev_c) / max(c - prev_c, 1e-9)
        prev_le, prev_c = le, c
    return None


def front_calls():
    """front 가 stock 을 부른 결과별 누적 수(재시도 포함, 시도마다 하나)"""
    return {r["metric"]["outcome"]: float(r["value"][1])
            for r in q("sum by (outcome) (front_stock_calls_total)")}


def hypothesis():
    succ = scalar(f'sum(rate(loadgen_requests_total{{outcome="ok"}}[{WIN}])) / sum(rate(loadgen_requests_total[{WIN}]))')
    p99 = scalar(f"histogram_quantile(0.99, sum by (le) (rate(loadgen_request_seconds_bucket[{WIN}])))")
    p50 = scalar(f"histogram_quantile(0.50, sum by (le) (rate(loadgen_request_seconds_bucket[{WIN}])))")
    ok = succ is not None and p99 is not None and succ >= SUCC_MIN and p99 < P99_MAX
    return ok, succ, p50, p99


def kubectl(*args, check=True):
    return subprocess.run(K + list(args), check=check, capture_output=True, text=True)


def icmp():
    """노드의 ICMP 송신 통계. Service 에 엔드포인트가 없을 때 iptables REJECT 가 보내는
    port unreachable(OutDestUnreachs)과, 커널 속도 제한에 막혀 못 보낸 수(OutRateLimitHost)"""
    out = subprocess.run(["docker", "exec", "ir-03-control-plane", "cat", "/proc/net/snmp"],
                         capture_output=True, text=True).stdout.splitlines()
    rows = [l.split() for l in out if l.startswith("Icmp:")]
    d = dict(zip(rows[0][1:], map(int, rows[1][1:])))
    return d.get("OutDestUnreachs", 0), d.get("OutRateLimitHost", 0)


def fmt(v, pct=False):
    if v is None:
        return "-"
    return f"{v * 100:.2f}" if pct else f"{v * 1000:.0f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("name")
    ap.add_argument("chaos")
    ap.add_argument("--observe", type=int, default=180)
    ap.add_argument("--baseline", type=int, default=60)
    ap.add_argument("--recover", type=int, default=60)
    ap.add_argument("--no-abort", action="store_true")
    a = ap.parse_args()

    os.makedirs(os.path.join(ROOT, "results", "raw"), exist_ok=True)
    tsv = open(os.path.join(ROOT, "results", f"{a.name}.tsv"), "w")
    tsv.write("t_s\tphase\thold\tsucc15s_pct\tp50_15s_ms\tp99_15s_ms\treq_5s\terr_5s\terr_kinds_5s\n")

    rows = []
    t_chaos = None
    prev_by, _ = counters()

    def tick(phase):
        nonlocal prev_by
        ok, succ, p50, p99 = hypothesis()
        by, _ = counters()
        d = {k: by.get(k, 0) - prev_by.get(k, 0) for k in by}
        prev_by = by
        req = sum(d.values())
        errs = {k: int(v) for k, v in d.items() if k != "ok" and v > 0}
        t = time.time() - t_chaos if t_chaos else -1
        line = (f"{t:.0f}\t{phase}\t{'Y' if ok else 'N'}\t{fmt(succ, True)}\t{fmt(p50)}\t{fmt(p99)}\t"
                f"{int(req)}\t{sum(errs.values())}\t{','.join(f'{k}={v}' for k, v in sorted(errs.items())) or '-'}")
        tsv.write(line + "\n")
        tsv.flush()
        print(line, flush=True)
        rows.append((phase, ok))
        return ok

    # 1. 기준 구간
    t_chaos = time.time() + a.baseline
    end = t_chaos
    while time.time() < end:
        time.sleep(TICK)
        tick("baseline")
    if not all(ok for ph, ok in rows[-3:]):
        print("기준 구간 끝에서 정상 상태 가설이 맞지 않는다. 카오스를 걸지 않는다", file=sys.stderr)
        sys.exit(2)

    # 2. 카오스
    by0, b0 = counters()
    icmp0 = icmp()
    fc0 = front_calls()
    t_chaos = time.time()
    kubectl("apply", "-f", a.chaos)
    aborted_at = None
    bad = 0
    while time.time() - t_chaos < a.observe:
        time.sleep(TICK)
        ok = tick("chaos")
        bad = 0 if ok else bad + 1
        if bad >= 2 and not a.no_abort:
            aborted_at = time.time() - t_chaos
            print(f"중단 조건: 가설이 연속 2번 깨졌다. {aborted_at:.0f}초에 카오스를 지운다", flush=True)
            break
    by1, b1 = counters()
    icmp1 = icmp()
    fc1 = front_calls()
    status = kubectl("get", "-f", a.chaos, "-o", "yaml", check=False).stdout
    events = kubectl("-n", "ir03", "get", "events", "--sort-by=.lastTimestamp", check=False).stdout
    kubectl("delete", "-f", a.chaos, "--wait=false", check=False)
    t_removed = time.time() - t_chaos
    open(os.path.join(ROOT, "results", "raw", f"{a.name}-chaos.yaml.txt"), "w").write(status)
    open(os.path.join(ROOT, "results", "raw", f"{a.name}-events.txt"), "w").write(events)

    # 3. 회복
    end = time.time() + a.recover
    while time.time() < end:
        time.sleep(TICK)
        tick("recover")

    # 요약: 카오스 구간 전체(적용 ~ 제거)의 누적 수 차이로 계산한다
    d = {k: by1.get(k, 0) - by0.get(k, 0) for k in by1}
    total = sum(d.values())
    errs = {k: int(v) for k, v in d.items() if k != "ok" and v > 0}
    succ = d.get("ok", 0) / total if total else None
    p50, p99 = quantile(b0, b1, 0.5), quantile(b0, b1, 0.99)
    chaos_rows = [ok for ph, ok in rows if ph == "chaos"]
    rec_rows = [(i, ok) for i, (ph, ok) in enumerate(rows) if ph == "recover"]
    verdict = "가설 유지" if all(chaos_rows) else "가설 깨짐"
    summ = (f"== {a.name}  ({os.path.basename(a.chaos)})\n"
            f"   카오스 구간 {t_removed:.0f}초, 요청 {int(total)}건, 성공률 {fmt(succ, True)}%, "
            f"p50 {fmt(p50)}ms, p99 {fmt(p99)}ms\n"
            f"   실패 종류: {', '.join(f'{k} {v}' for k, v in sorted(errs.items())) or '없음'}\n"
            f"   5초 판정 {len(chaos_rows)}번 중 깨짐 {chaos_rows.count(False)}번 -> {verdict}"
            + (f", {aborted_at:.0f}초에 자동 중단" if aborted_at else "") + "\n"
            f"   front 의 stock 호출 실패(시도 단위): "
            + (", ".join(f"{k} {int(fc1[k] - fc0.get(k, 0))}" for k in sorted(fc1)
                         if k != "ok" and fc1[k] - fc0.get(k, 0) > 0) or "없음") + "\n"
            f"   노드 ICMP port unreachable 보냄 {icmp1[0] - icmp0[0]}, 속도 제한으로 못 보냄 {icmp1[1] - icmp0[1]}\n"
            f"   회복 구간 판정 {len(rec_rows)}번 중 깨짐 {sum(1 for _, ok in rec_rows if not ok)}번\n")
    print(summ)
    with open(os.path.join(ROOT, "results", "summary.txt"), "a") as f:
        f.write(summ)


if __name__ == "__main__":
    main()
