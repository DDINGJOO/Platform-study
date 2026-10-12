#!/usr/bin/env python3
"""trial-1..N 의 타임라인을 만들고(timeline.py) 탐지 시간을 한 표로 모은다 → results/trials-summary.md"""
import json, os, statistics, subprocess, sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
prefix, n = sys.argv[1], int(sys.argv[2])
rows = []
for i in range(1, n + 1):
    run = f"{prefix}-{i}"
    subprocess.run([sys.executable, os.path.join(HERE, "scripts", "timeline.py"), run], check=True, capture_output=True)
    s = json.load(open(os.path.join(HERE, "results", run, "timeline.json")))["summary"]
    rows.append((run, s))
keys = [("주입→영향 시작(첫 503 스크레이프)", "주입→첫 503"),
        ("주입→pending", "주입→pending"),
        ("주입→firing", "주입→firing"),
        ("주입→page 알림 수신 (TTD)", "주입→page 수신(TTD)")]
out = ["# 같은 장애 반복 주입: 탐지 시간", "",
       "조건: 초당 20건, latency 900ms jitter 300ms, 주문의 재고 호출 타임아웃 1초, 스크레이프 5s, 규칙 평가 10s, for 1m, group_wait 30s.",
       "매 회 주입 전 0~20초 무작위 대기. page 알림을 받자마자 독 제거. 단위 초.", "",
       "| 회차 | " + " | ".join(k[1] for k in keys) + " | firing→수신 | 탐지 구간 스크레이프 |", "|---" * (len(keys) + 3) + "|"]
for run, s in rows:
    vals = [s[k[0]] for k in keys]
    out.append(f"| {run} | " + " | ".join(str(v) for v in vals) + f" | {round(s[keys[3][0]] - s[keys[2][0]], 1)} | {s['점검: 탐지 구간(start→page 수신) 스크레이프 수 / 기대값']} |")
ttd = [s[keys[3][0]] for _, s in rows]
out += ["", f"TTD 최소 {min(ttd)}, 최대 {max(ttd)}, 평균 {round(statistics.mean(ttd), 1)}, 표준편차 {round(statistics.pstdev(ttd), 1)} (n={len(ttd)})"]
open(os.path.join(HERE, "results", "trials-summary.md"), "w").write("\n".join(out) + "\n")
print("\n".join(out))
