"""Envoy 접근 로그로 인스턴스별 요청 수와 지연을 센다.
사용: python3 access-summary.py <로그 파일...> [--skip 초] [--bucket 초] [--from 유닉스초 --to 유닉스초]
로그 한 줄 형식(envoy 설정의 access_log): <시작 유닉스초.ms> <X-Instance> <상태 코드> <걸린 ms> <업스트림 주소>
--skip 은 로그 첫 요청부터 이만큼은 빼고 센다(워밍업 제외). --bucket 을 주면 시간 구간별 표도 찍는다."""
import argparse, collections, sys

ap = argparse.ArgumentParser()
ap.add_argument("logs", nargs="+")
ap.add_argument("--skip", type=float, default=0)
ap.add_argument("--bucket", type=float)
ap.add_argument("--from", dest="t_from", type=float)
ap.add_argument("--to", dest="t_to", type=float)
ap.add_argument("--slow-ms", type=float, default=100, help="이보다 오래 걸린 요청 수도 센다")
a = ap.parse_args()

rows = []
for f in a.logs:
    for line in open(f):
        p = line.split()
        if len(p) < 4 or not p[0][0].isdigit():
            continue
        rows.append((float(p[0]), p[1], p[2], float(p[3])))
rows.sort()
if not rows:
    sys.exit("로그가 비었다")
t0 = rows[0][0] + a.skip
lo = a.t_from if a.t_from else t0
hi = a.t_to if a.t_to else float("inf")
rows = [r for r in rows if lo <= r[0] < hi]

def pct(xs, q):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(len(xs) * q))] if xs else float("nan")

def table(rs, title):
    by = collections.defaultdict(list)
    codes = collections.defaultdict(collections.Counter)
    for t, inst, code, ms in rs:
        by[inst].append(ms)
        codes[inst][code] += 1
    total = len(rs)
    print(f"# {title}  요청 {total}건")
    print(f"{'인스턴스':<10}{'요청':>8}{'몫':>8}{'p50ms':>9}{'p99ms':>9}{'max':>9}{'>'+str(int(a.slow_ms))+'ms':>8}  상태 코드")
    for inst in sorted(by):
        xs = by[inst]
        slow = sum(1 for x in xs if x > a.slow_ms)
        cs = " ".join(f"{c}:{n}" for c, n in sorted(codes[inst].items()))
        print(f"{inst:<10}{len(xs):>8}{len(xs)/total*100:>7.1f}%{pct(xs,.5):>9.0f}{pct(xs,.99):>9.0f}{max(xs):>9.0f}{slow:>8}  {cs}")
    allx = [r[3] for r in rs]
    slow = sum(1 for x in allx if x > a.slow_ms)
    print(f"{'전체':<10}{total:>8}{100:>7.1f}%{pct(allx,.5):>9.0f}{pct(allx,.99):>9.0f}{max(allx):>9.0f}{slow:>8}")

table(rows, "구간 전체")
if a.bucket:
    start = rows[0][0]
    insts = sorted({r[1] for r in rows})
    print(f"\n# {a.bucket:g}초 구간별 인스턴스 몫(%) / p99(ms)")
    print("초".rjust(6) + "".join(f"{i:>18}" for i in insts) + f"{'전체p99':>10}")
    buckets = collections.defaultdict(list)
    for r in rows:
        buckets[int((r[0] - start) // a.bucket)].append(r)
    for k in sorted(buckets):
        rs = buckets[k]
        line = f"{k*a.bucket:>6.0f}"
        for i in insts:
            xs = [r[3] for r in rs if r[1] == i]
            line += f"{len(xs)/len(rs)*100:>9.1f}%/{pct(xs,.99):>6.0f}ms" if xs else f"{'-':>18}"
        line += f"{pct([r[3] for r in rs],.99):>8.0f}ms"
        print(line)
