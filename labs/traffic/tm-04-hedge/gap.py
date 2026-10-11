"""백엔드 로그(LOG_ARRIVALS=true)에서 같은 x-request-id 의 원본과 사본 도착 간격을 잰다.
사용: docker compose logs --since <시각> backend-1 backend-2 backend-3 | python3 gap.py"""
import re, sys, collections, statistics

first, second = {}, {}
for line in sys.stdin:
    m = re.search(r"^(backend-\d).*arrival rid=(\S+) attempt=(\d+).*t_us=(\d+)", line)
    if not m:
        continue
    host, rid, attempt, t = m.group(1), m.group(2), int(m.group(3)), int(m.group(4))
    (first if attempt == 1 else second)[rid] = (host, t)
gaps = sorted((second[r][1] - first[r][1]) / 1000 for r in second if r in first)
same = sum(1 for r in second if r in first and first[r][0] == second[r][0])
print(f"사본(attempt=2) {len(second)}건")
print(f"원본 도착 -> 사본 도착 간격(ms): 최소 {gaps[0]:.1f}, 중앙값 {statistics.median(gaps):.1f}, 최대 {gaps[-1]:.1f}")
print(f"  25ms(per_try_timeout)를 뺀 대기: 최소 {gaps[0] - 25:.1f}, 최대 {gaps[-1] - 25:.1f}")
hist = collections.Counter(int((g - 25) // 5) * 5 for g in gaps)
print("  5ms 구간 분포:", {f"{k}~{k + 5}": v for k, v in sorted(hist.items())})
print(f"사본이 원본과 같은 백엔드로 간 경우: {same}건 / {len(second)}건")
