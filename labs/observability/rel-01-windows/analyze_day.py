"""압축한 하루의 요청 기록(CSV)으로 SLI 를 여러 기준으로 계산한다. 표준 라이브러리만.

  python3 analyze_day.py out/day-night.csv [--outage-at 1 --outage-min 60]

출력
  1) 분모를 바꿔 가며 본 요청 기준 SLI (서버가 받은 요청 = 시도 단위)
  2) 사용자 기준 최종 결과(재시도 뒤 성공이면 성공)
  3) 시간 기준 SLI: 압축 1분(실제 1초)마다 사용자 API 에러율이 5% 이하면 좋은 분
"""
import argparse
import csv
from collections import defaultdict

ap = argparse.ArgumentParser()
ap.add_argument("csv")
ap.add_argument("--outage-at", type=float)
ap.add_argument("--outage-min", type=float, default=0)
ap.add_argument("--bad-minute-ratio", type=float, default=0.05)
a = ap.parse_args()

rows = list(csv.DictReader(open(a.csv)))
for r in rows:
    r["code"] = int(r["code"]); r["attempt"] = int(r["attempt"]); r["minute"] = float(r["minute"])

def sli(sel, bad=lambda r: r["code"] >= 500 or r["code"] < 0):
    xs = [r for r in rows if sel(r)]
    n = len(xs); b = sum(1 for r in xs if bad(r))
    return n, b, 100 * (1 - b / n) if n else float("nan")

print(f"파일 {a.csv}: 요청 {len(rows)}건")
cases = [
    ("서버가 받은 모든 요청 (봇·헬스체크 포함)", lambda r: True),
    ("헬스체크 제외", lambda r: r["kind"] != "probe"),
    ("헬스체크·봇 제외", lambda r: r["kind"] == "user"),
    ("API 경로만, 사용자·봇", lambda r: r["path"] == "/api/checkout"),
    ("API 경로만, 사용자만 (기준)", lambda r: r["path"] == "/api/checkout" and r["kind"] == "user"),
]
base = sli(cases[-1][1])[2]
print("\n[요청 기준 SLI: 5xx 와 연결 실패를 나쁜 요청으로, 시도마다 1건]")
for name, sel in cases:
    n, b, s = sli(sel)
    print(f"  {name:28s} 전체 {n:7d}  나쁨 {b:5d}  SLI {s:8.4f}%  (기준 대비 {s-base:+.4f}%p)")

n404 = sli(lambda r: True, bad=lambda r: r["code"] >= 400 or r["code"] < 0)
print(f"  {'(참고) 4xx 도 나쁨으로, 모든 요청':28s} 전체 {n404[0]:7d}  나쁨 {n404[1]:5d}  SLI {n404[2]:8.4f}%")

# 사용자 최종 결과: 첫 시도와 재시도를 이어 붙인다. 재시도는 첫 시도 바로 뒤에 같은 순서로 기록됐다고 보지 않고,
# 첫 시도 실패 수와 재시도 성공 수로 센다.
first = [r for r in rows if r["kind"] == "user" and r["attempt"] == 1]
second = [r for r in rows if r["kind"] == "user" and r["attempt"] == 2]
f_bad = sum(1 for r in first if r["code"] >= 500 or r["code"] < 0)
s_ok = sum(1 for r in second if 0 < r["code"] < 500)
print("\n[사용자 기준 최종 결과]")
print(f"  사용자 요청 {len(first)}건, 첫 시도 실패 {f_bad}건, 재시도 {len(second)}건 중 성공 {s_ok}건")
print(f"  첫 시도 기준 SLI {100*(1-f_bad/len(first)):.4f}%  /  재시도 뒤 최종 SLI {100*(1-(f_bad-s_ok)/len(first)):.4f}%")

# 시간 기준
per = defaultdict(lambda: [0, 0])
for r in rows:
    if r["kind"] == "user" and r["path"] == "/api/checkout":
        m = int(r["minute"])
        if 0 <= m < 1440:
            per[m][0] += 1
            per[m][1] += r["code"] >= 500 or r["code"] < 0
bad_min = [m for m in range(1440) if per[m][0] and per[m][1] / per[m][0] > a.bad_minute_ratio]
empty = [m for m in range(1440) if per[m][0] == 0]
if a.outage_at is not None:
    o0, o1 = a.outage_at * 60, a.outage_at * 60 + a.outage_min
    in_out = [m for m in bad_min if o0 - 1 <= m <= o1 + 1]
else:
    in_out = []
print("\n[시간 기준 SLI: 압축 1분마다 사용자 API 에러율 > %.0f%% 면 나쁜 분]" % (100 * a.bad_minute_ratio))
print(f"  나쁜 분 {len(bad_min)}개 (장애 구간 안 {len(in_out)}개, 밖 {len(bad_min)-len(in_out)}개), 요청 없는 분 {len(empty)}개(좋은 분으로 셈)")
print(f"  시간 기준 SLI {100*(1-len(bad_min)/1440):.4f}%")
outside = sorted(set(bad_min) - set(in_out))
if outside:
    print("  장애 밖 나쁜 분:", ", ".join(f"{m//60:02d}:{m%60:02d}({per[m][1]}/{per[m][0]})" for m in outside[:20]))
