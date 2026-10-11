#!/usr/bin/env python3
"""out/<이름>.csv (k6) 와 out/<이름>.events 를 읽어 초 단위 표와 요약을 낸다.
시각은 전부 부하 시작(load-start) 기준 상대 초로 바꿔 적는다."""
import csv, sys, collections

name = sys.argv[1]
ev = sorted((l.split(None, 1) for l in open(f'out/{name}.events') if l.strip()), key=lambda x: int(x[0]))
ev = [e for e in ev if e[1].strip() == 'load-start'] + [e for e in ev if e[1].strip() != 'load-start']
t0 = int(ev[0][0])  # load-start
events = sorted(((int(t) - t0) / 1000, e.strip()) for t, e in ev)

reqs = []   # (상대초, 버전 또는 fail, 오류, 지연ms)
pending = {}
rows = list(csv.DictReader(open(f'out/{name}.csv')))
dur = {}
errs = collections.Counter()
for r in rows:
    m = r['metric_name']
    if m == 'http_reqs' and r['status'] != '200':
        errs[(r['status'], r['error_code'], r['error'][:60])] += 1
for r in rows:
    if r['metric_name'] == 'ver':
        v = dict(kv.split('=', 1) for kv in r['extra_tags'].split('&') if '=' in kv).get('v', '?')
        reqs.append(((int(r['timestamp']) - t0) / 1000, v))
reqs.sort()

lat = collections.defaultdict(list)
for r in rows:
    if r['metric_name'] == 'http_req_duration':
        lat[int((int(r['timestamp']) - t0) // 1000)].append(float(r['metric_value']))

per = collections.defaultdict(collections.Counter)
for t, v in reqs:
    per[int(t // 1)][v] += 1

def pct(a, p):
    a = sorted(a); return a[min(len(a) - 1, int(len(a) * p))] if a else 0

print(f'# {name}  (요청 {len(reqs)}건, 초당 50건 목표)')
print('## 사건 (부하 시작 기준 초)')
for t, e in events:
    print(f'  {t:7.1f}s  {e}')
fails = [t for t, v in reqs if v == 'fail']
print('## 요약')
print(f'  실패 {len(fails)}건 / {len(reqs)}건')
if fails:
    print(f'  첫 실패 {fails[0]:.1f}s, 마지막 실패 {fails[-1]:.1f}s (구간 {fails[-1]-fails[0]:.1f}s)')
for (st, code, msg), n in errs.most_common(6):
    print(f'  status={st or "-"} code={code or "-"} {msg}  x{n}')
print('## 초별 (실패가 있거나 버전이 섞인 초, 그리고 앞뒤 경계)')
print('  초    v1   v2  fail   p50ms   p99ms')
keys = sorted(per)
interesting = set()
for s in keys:
    c = per[s]
    if c['fail'] or (c['v1'] and c['v2']):
        interesting |= {s - 1, s, s + 1}
prev = None
for s in keys:
    if s not in interesting:
        continue
    if prev is not None and s != prev + 1:
        print('  ...')
    c = per[s]
    print(f'  {s:3d} {c["v1"]:5d} {c["v2"]:4d} {c["fail"]:5d} {pct(lat[s],.5):7.0f} {pct(lat[s],.99):7.0f}')
    prev = s
# 전환 시점: 마지막 v1 응답, 첫 v2 응답
v1 = [t for t, v in reqs if v == 'v1']; v2 = [t for t, v in reqs if v == 'v2']
def span(xs):
    return f'{xs[0]:.1f}s ~ {xs[-1]:.1f}s ({len(xs)}건)' if xs else '없음'
print(f'## 버전  v1 {span(v1)}, v2 {span(v2)}')
