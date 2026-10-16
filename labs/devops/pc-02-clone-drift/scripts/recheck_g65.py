#!/usr/bin/env python3
"""묶음 65 다시 추적: 끝 릴리스 대신 두 사본을 공통 유틸리티로 옮긴 커밋(c6fa180602)의 부모까지 줄 범위를 옮겨 -L 을 돌리고,
그 커밋 자체의 hunk 가 범위에 걸치는지 본다.  python3 scripts/recheck_g65.py <WORK>  -> out/recheck-g65.txt"""
import json, sys
sys.path.insert(0, 'scripts')
import track
work = sys.argv[1]; repo = f'{work}/src/repo'
d = json.load(open('out/track-v6.1.0-v6.2.0-t100.json'))
g = [x for x in d['groups'] if x['id'] == 65][0]
lines = []
for o in g['occ']:
    hs = track.hunks(repo, 'v6.1.0', 'c6fa180602^', o['path'], o['path'])
    a, b = track.map_line(hs, o['line'], 'start'), track.map_line(hs, o['endline'], 'end')
    cs = track.log_L(repo, 'v6.1.0', 'c6fa180602^', a, b, o['path'])
    out = track.git(repo, 'diff', '-U0', 'c6fa180602^', 'c6fa180602', '--', o['path'])
    hit = sum(1 for m in (track.HUNK.match(l) for l in out.splitlines())
              if m and int(m[1]) <= b and int(m[1]) + int(m[2] or 1) - 1 >= a)
    lines.append(f"{o['path']} {o['line']}-{o['endline']} -> c6fa180602^:{a}-{b}  "
                 f"commits={[(c['sha'][:10], c['code'], c['subject']) for c in cs]}  c6fa180602_hunks_in_range={hit}")
open('out/recheck-g65.txt', 'w').write('\n'.join(lines) + '\n')
print('\n'.join(lines))
