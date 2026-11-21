#!/usr/bin/env python3
# 80-e28-trace 의 tcpdump·클라이언트 원본에서 옛 파드별 마지막 응답·RST·무응답 시각과 RST 출처, e7·e56 이 어느 SYN 시도와 짝인지 다시 센다
# 사용: python3 80-e28-rst-order.py <원본 디렉터리> <회차 이름...>   (같은 폴더의 80-e28-analyze.py 앞부분을 재사용)
# 원본(tcpdump 텍스트·클라이언트 로그, 약 69MB)은 저장소에 넣지 않았다. 결과는 80-e28-rst-order.txt
import sys, os, collections
here = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(here, '80-e28-analyze.py')).read().split("# 1. curl 실패 분류")[0]
d = sys.argv[1]
for name in sys.argv[2:]:
    g = {'__name__': 'x'}
    exec(src.replace("d, name = sys.argv[1], sys.argv[2]", f"d, name = {d!r}, {name!r}"), g)
    OLD, att, R0, F, who = g['OLD'], g['att'], g['R0'], g['F'], g['who']
    print(f"## {name}")
    for ip, (n, node) in OLD.items():
        ev = sorted((a['t'] - R0, 'RST' if a['rst'] else 'DROP' if a['unans'] else 'OK') for a in att.values() if ip in a['dst'])
        ok = [t for t, k in ev if k == 'OK']; rs = [t for t, k in ev if k == 'RST']; dr = [t for t, k in ev if k == 'DROP' and t < 5]
        print(f"  옛 파드 {n} ({node}): 마지막 응답 {('%.2f' % max(ok)) if ok else '-'}  RST {('%.2f~%.2f' % (min(rs), max(rs))) if rs else '-'}  무응답 {('%.2f~%.2f' % (min(dr), max(dr))) if dr else '-'}  (재시작 기준 초)")
    r = [a for a in att.values() if a['rst']]
    c = collections.Counter(who(next(iter(a['dst'])) if a['dst'] else '') for a in r)
    print(f"  RST 받은 SYN 시도 {len(r)}개, 출처(DNAT 목적지): {dict(c)}")
    for ex in ('e7', 'e56'):
        fs = [f for f in F if f['ex'] == ex]
        paired = 0; rstp = 0
        for f in fs:
            cand = [a for a in att.values() if a['syn'] and abs(a['syn'][0] - f['t']) <= 0.05]
            if cand: paired += 1
            if any(a['rst'] for a in cand): rstp += 1
        print(f"  {ex} {len(fs)}건: 50ms 안 SYN 시도와 짝 {paired}건, 그중 RST 받은 시도와 짝 {rstp}건")
    print()
