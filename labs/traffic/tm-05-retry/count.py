"""Envoy 통계로 층마다 몇 번 불렸는지 센다. 사용: python3 count.py [admin 포트, 기본 27101]
Envoy 를 새로 띄운 뒤 한 번의 부하만 돌렸다면 값이 곧 그 실행의 합계다."""
import re, sys, urllib.request

port = sys.argv[1] if len(sys.argv) > 1 else "27101"
s = urllib.request.urlopen(f"http://localhost:{port}/stats").read().decode()
v = lambda k: int(m.group(1)) if (m := re.search(rf"^{re.escape(k)}: (\d+)$", s, re.M)) else 0
top = v("http.edge.downstream_rq_total")
print(f"사용자 요청(edge 가 받은 것) {top}")
print(f"{'구간':<16}{'보낸 요청':>9}{'배율':>8}{'재시도':>8}{'overflow':>10}{'횟수 소진':>10}")
for name, c in [("edge -> svc-a", "svc_a"), ("svc-a -> svc-b", "svc_b"), ("svc-b -> svc-c", "svc_c")]:
    t = v(f"cluster.{c}.upstream_rq_total")
    print(f"{name:<16}{t:>9}{(t / top if top else 0):>8.2f}{v(f'cluster.{c}.upstream_rq_retry'):>8}"
          f"{v(f'cluster.{c}.upstream_rq_retry_overflow'):>10}{v(f'cluster.{c}.upstream_rq_retry_limit_exceeded'):>10}")
