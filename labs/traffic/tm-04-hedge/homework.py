"""ROADMAP 숙제: retry_policy.retriable_request_headers(:method GET) 가 헤지 사본을 막는가?
백엔드를 모두 per_try_timeout(25ms)보다 느리게 띄운 상태에서 돌린다(README 참고).
경우마다 요청 N개를 보내고, Envoy 클러스터 통계의 증가분과 백엔드가 받은 요청 수를 센다.
사용: python3 homework.py [N]   (Envoy 리스너 27000, admin 27001)"""
import http.client, json, re, subprocess, sys, time, collections

N = int(sys.argv[1]) if len(sys.argv) > 1 else 20
HOST, PORT, ADMIN = "localhost", 27000, 27001
CASES = [  # (경로, 메서드, 본문)
    ("/hedge-getonly", "GET", None),
    ("/hedge-getonly", "POST", None),
    ("/hedge-getonly", "POST", b"order=1"),
    ("/retry-getonly", "GET", None),
    ("/retry-getonly", "POST", None),
]
STATS = ["upstream_rq_total", "upstream_rq_per_try_timeout", "upstream_rq_retry",
         "upstream_rq_retry_limit_exceeded", "upstream_rq_timeout", "upstream_rq_tx_reset"]

def stats(cluster):
    c = http.client.HTTPConnection(HOST, ADMIN); c.request("GET", "/stats?filter=^cluster\\." + cluster + "\\.")
    body = c.getresponse().read().decode()
    return {k: int(m.group(1)) if (m := re.search(rf"cluster\.{cluster}\.{k}: (\d+)", body)) else 0 for k in STATS}

def logs(since, kind):
    out = subprocess.run(["docker", "compose", "logs", "--no-log-prefix", "--since", since,
                          "backend-1", "backend-2", "backend-3"], capture_output=True, text=True).stdout
    return [dict(re.findall(r"(\w+)=(\S+)", l)) for l in out.splitlines() if f" {kind} rid=" in l]

for path, method, body in CASES:
    cluster = "backend_" + path.strip("/").replace("-", "_")
    before = stats(cluster)
    since = str(int(time.time()))
    codes, times, rids = collections.Counter(), [], []
    for _ in range(N):
        c = http.client.HTTPConnection(HOST, PORT, timeout=10)
        h = {"Content-Type": "text/plain"} if body else {}
        t = time.perf_counter(); c.request(method, path, body=body, headers=h); r = c.getresponse(); r.read()
        times.append((time.perf_counter() - t) * 1000); codes[r.status] += 1
    time.sleep(2.5)
    after = stats(cluster)
    heads = [a for a in logs(since, "head") if a.get("method") == method]
    seen = [a for a in logs(since, "arrival") if a.get("method") == method]
    aborted = collections.Counter(a["error"] for a in logs(since, "aborted"))
    per_rid = collections.Counter(a["rid"] for a in seen)
    bodies = collections.Counter((a["attempt"], a["clen"], a["body"]) for a in seen)
    print(f"{method:4} {path:15} body={'있음' if body else '없음'}  응답={dict(codes)}  "
          f"지연 중앙값={sorted(times)[N//2]:.0f}ms 최대={max(times):.0f}ms")
    print("     Envoy 증가분:", {k.replace('upstream_rq_', ''): after[k] - before[k] for k in STATS})
    print(f"     헤더 도착(필터): {len(heads)}건, (시도 번호, Content-Length)={dict(collections.Counter((a['attempt'], a['clen']) for a in heads))}"
          + (f", 본문을 못 받고 끊김={dict(aborted)}" if aborted else ""))
    print(f"     컨트롤러 도착: {len(seen)}건 / 요청 {N}개, 요청당 도착 수 분포={dict(collections.Counter(per_rid.values()))}, "
          f"(시도 번호, Content-Length 헤더, 받은 본문 바이트)={dict(bodies)}")
