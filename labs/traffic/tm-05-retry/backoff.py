"""svc-c 도착 로그(LOG_ARRIVALS=true)에서 Envoy 재시도 간격을 잰다. 같은 요청의 시도는 x-request-id 가 같다.
사용: docker compose logs --since <시각> svc-c | python3 backoff.py
간격 = svc-c 처리 시간(약 5ms) + Envoy 백오프 대기 + 몇 ms 의 왕복."""
import re, sys, collections, statistics

tries = collections.defaultdict(dict)
for line in sys.stdin:
    m = re.search(r"arrival rid=(\S+) attempt=(\d+).*t_us=(\d+)", line)
    if m:
        tries[m.group(1)][int(m.group(2))] = int(m.group(3))
for n in (1, 2):
    gaps = sorted((t[n + 1] - t[n]) / 1000 for t in tries.values() if n in t and n + 1 in t)
    if not gaps:
        continue
    hist = collections.Counter(int(g // 10) * 10 for g in gaps)
    print(f"{n}번째 시도 -> {n + 1}번째 시도 ({len(gaps)}건): 최소 {gaps[0]:.1f}ms, 중앙값 {statistics.median(gaps):.1f}ms, 최대 {gaps[-1]:.1f}ms")
    print("   10ms 구간:", " ".join(f"{k}~{k + 10}:{v}" for k, v in sorted(hist.items())))
