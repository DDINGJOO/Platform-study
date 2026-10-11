"""app-4 가 뜬 뒤의 접근 로그를 구간별로 나눠 본다.
사용: python3 join-report.py out/<설정> [--window 120] [--bucket 5]
- join 파일: app-4 컨테이너를 띄운 시각(유닉스초)
- 표 1: join 부터 window 초 동안 전체 요청 중 app-4 몫, 느린 요청(>50ms, >200ms) 수, 전체 p99
- 표 2: app-4 의 첫 요청부터 bucket 초 구간별 app-4 몫과 지연(p50, p99), 같은 구간 전체 p99"""
import argparse, collections, os

ap = argparse.ArgumentParser()
ap.add_argument("dir")
ap.add_argument("--window", type=float, default=120)
ap.add_argument("--bucket", type=float, default=5)
a = ap.parse_args()

join = float(open(os.path.join(a.dir, "join")).read().strip().replace("N", "0"))
rows = []
for line in open(os.path.join(a.dir, "access.log")):
    p = line.split()
    if len(p) >= 4 and p[0][:1].isdigit():
        rows.append((float(p[0]), p[1], p[2], float(p[3])))
rows.sort()

def pct(xs, q):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(len(xs) * q))] if xs else float("nan")

win = [r for r in rows if join <= r[0] < join + a.window]
a4 = [r for r in win if r[1] == "app-4"]
non200 = collections.Counter(r[2] for r in win if r[2] != "200")
first = a4[0][0] if a4 else None
print(f"# app-4 기동 후 {a.window:g}초 (요청 {len(win)}건)")
print(f"app-4 첫 요청: 기동 {first - join:.1f}초 뒤" if first else "app-4 요청 없음")
print(f"app-4 몫 {len(a4)/len(win)*100:.1f}% ({len(a4)}건)")
for th in (50, 200, 1000):
    print(f">{th}ms  전체 {sum(1 for r in win if r[3] > th):>5}건   그중 app-4 {sum(1 for r in a4 if r[3] > th):>5}건")
allx = [r[3] for r in win]
print(f"전체 p50 {pct(allx,.5):.0f}ms  p99 {pct(allx,.99):.0f}ms  p99.9 {pct(allx,.999):.0f}ms  max {max(allx):.0f}ms")
print(f"200 이 아닌 응답: {dict(non200) or '없음'}")
if first:
    print(f"\n# app-4 첫 요청부터 {a.bucket:g}초 구간별")
    print(f"{'초':>5} {'app-4 몫':>9} {'app-4 건':>8} {'app-4 p50':>10} {'app-4 p99':>10} {'전체 p99':>9}")
    b = collections.defaultdict(list)
    for r in rows:
        if r[0] >= first:
            b[int((r[0] - first) // a.bucket)].append(r)
    for k in sorted(b):
        if k * a.bucket >= a.window:
            break
        rs = b[k]
        xs = [r[3] for r in rs if r[1] == "app-4"]
        print(f"{k*a.bucket:>5.0f} {len(xs)/len(rs)*100:>8.1f}% {len(xs):>8} {pct(xs,.5):>9.0f}ms {pct(xs,.99):>9.0f}ms {pct([r[3] for r in rs],.99):>7.0f}ms")
