#!/usr/bin/env python3
"""out/ 의 bench·retry·spring 출력을 바퀴별로 모아 results/summary.txt 를 만든다."""
import glob, os, re, sys
from collections import defaultdict

os.chdir(os.path.join(os.path.dirname(__file__), '..'))
rows = defaultdict(list)
for f in sorted(glob.glob('out/bench-*.txt') + glob.glob('out/retry-*.txt')):
    t = open(f, encoding='utf-8').read()
    m = re.search(r'pattern=(\S+) iso=(\S+) retry=(\S+)', t)
    v = re.search(r'verdicts=\{(.*)\}', t).group(1)
    g = re.search(r'failed=(\d+) wrong_verdict=(\d+) correct_rounds=(\d+)/(\d+) zero_row_rounds=(\d+)', t).groups()
    d = re.search(r'lock_deadlocks\+=(\d+) Innodb_deadlocks\+=(-?\d+) retried_requests=(\d+) extra_attempts=(\d+)', t).groups()
    st = re.search(r'Innodb_deadlocks status before=(-?\d+)', t).group(1)
    lat = re.search(r'p50=([\d.]+) p99=([\d.]+)', t).groups()
    run = re.search(r'-r(\d+)\.txt$', f).group(1)
    key = ('retry ' if m.group(3) == 'true' else '') + f'{m.group(1)} {m.group(2)}'
    rows[key].append((run, v, g, d, st, lat))

out = ['# 4건 동시 x 90 라운드 = 360건, 바퀴마다 한 줄',
       '# failed=예외로 끝난 요청, wrong=판정이 실제와 다른 요청, ok_rounds=4건 모두 맞게 판정하고 행이 1개인 라운드',
       '# dl=INNODB_METRICS lock_deadlocks 증가분, Innodb_deadlocks 상태 변수 값(없으면 -1), retried=재시도한 요청 수/추가 시도 수', '']
order = ['p1 RR', 'p2 RR', 'p2a RR', 'p3 RR', 'p4 RR', 'p4b RR', 'p5 RR',
         'p1 RC', 'p2 RC', 'p2a RC', 'p3 RC', 'p4 RC', 'p4b RC', 'p5 RC', 'retry p1 RR', 'retry p5 RR']
for k in order:
    for run, v, g, d, st, lat in rows.get(k, []):
        out.append(f'{k:12s} r{run}  failed={g[0]:>3} wrong={g[1]:>3} ok_rounds={g[2]:>2}/{g[3]} zero_row={g[4]} '
                   f'dl={d[0]:>3} Innodb_deadlocks={st} retried={d[2]}/{d[3]} p50={lat[0]}ms p99={lat[1]}ms  [{v}]')
    out.append('')
for f in sorted(glob.glob('out/spring-*.txt')):
    t = open(f, encoding='utf-8').read()
    out.append(os.path.basename(f) + '  ' + ' | '.join(l.strip() for l in t.strip().splitlines() if l.strip() and 'WARN' not in l))
open('results/summary.txt', 'w', encoding='utf-8').write('\n'.join(out) + '\n')
print('\n'.join(out))
