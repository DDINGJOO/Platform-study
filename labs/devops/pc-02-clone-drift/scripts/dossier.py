#!/usr/bin/env python3
"""불일치 변경이 있었던 묶음마다, 사본 위치와 커밋별 diff(-L 범위 안)를 한 파일로 모은다. 손으로 판정하기 위한 자료.
  python3 scripts/dossier.py <WORK> <base> <end> [최소토큰=100]   ->  out/review/g<id>.txt
"""
import json, os, subprocess, sys
work, base, end = sys.argv[1:4]
tok = sys.argv[4] if len(sys.argv) > 4 else '100'
repo = f'{work}/src/repo'
d = json.load(open(f'out/track-{base}-{end}-t{tok}.json'))
cls = json.load(open(f'out/groups-{base}-{end}-t{tok}.json'))
os.makedirs('out/review', exist_ok=True)
for g in d['groups']:
    c = cls[str(g['id'])]
    if c['class'] != 'has_inconsistent':
        continue
    lines = [f"group {g['id']} tokens={g['tokens']} together_at_end={c['together_at_end']} late={c['late_propagation']}"]
    for i, o in enumerate(g['occ']):
        lines.append(f"  [{i}] {o['path']}:{o['line']}-{o['endline']} -> {o.get('end_path')}:{o.get('end_line')}-{o.get('end_endline')} {o['status']}")
        for cm in o['commits']:
            lines.append(f"      {cm['date']} {cm['sha'][:10]} code={cm['code']} {cm['subject']}")
    for i, o in enumerate(g['occ']):
        if o['status'] != 'present':
            continue
        out = subprocess.run(['git', '-C', repo, 'log', f"-L{o['end_line']},{o['end_endline']}:{o['end_path']}",
                              '--no-merges', '--format=### [%x%x] %h %cs %s'.replace('%x%x', str(i)), f'{base}..{end}'],
                             capture_output=True, text=True, errors='replace').stdout
        # 문맥 줄은 빼고 바뀐 줄과 hunk 머리만 남긴다
        keep = [l for l in out.splitlines() if l.startswith(('###', '@@', '+', '-')) and not l.startswith(('+++', '---'))]
        lines.append('\n'.join(keep))
    open(f"out/review/g{g['id']}.txt", 'w').write('\n'.join(lines) + '\n')
print(len(os.listdir('out/review')))
