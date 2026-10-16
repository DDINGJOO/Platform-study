#!/usr/bin/env python3
"""track.py 결과를 묶음 단위·커밋 단위로 센다.

  python3 scripts/analyze.py <base> <end> [최소토큰=100]

정의 (Krinke, WCRE 2007 의 이력 기반 정의를 따른다. Juergens 외 ICSE 2009 와 다른 점은 README)
  변경        한 커밋이 묶음의 사본 하나 이상에서 코드 줄을 바꾼 것(주석·공백만 바뀐 것은 따로 센다)
  일관 변경    그 커밋이 끝까지 남은 사본 모두를 바꿨다
  불일치 변경  그 커밋이 남은 사본 중 일부만 바꿨다
  뒤늦은 전파  불일치 변경 뒤, 창 안의 다른 커밋이 나머지 사본을 바꿨다(같은 수정인지는 손으로 본다)
  끝에서 함께  끝 릴리스의 CPD 결과에서, 남은 사본 전부가 한 묶음 안에 다시 잡혔다
출력  results/summary-<base>-<end>-t<N>.md, results/events-<base>-<end>-t<N>.tsv
"""
import json, sys
from collections import Counter, defaultdict

base, end = sys.argv[1], sys.argv[2]
tok = sys.argv[3] if len(sys.argv) > 3 else '100'
d = json.load(open(f'out/track-{base}-{end}-t{tok}.json'))
groups = d['groups']


def overlap(a1, b1, a2, b2):
    inter = max(0, min(b1, b2) - max(a1, a2) + 1)
    return inter / max(1, min(b1 - a1 + 1, b2 - a2 + 1))


end_groups = d['end_groups']


def together_at_end(present):
    for eg in end_groups:
        ok = True
        for o in present:
            if not any(p == o['end_path'] and overlap(o['end_line'], o['end_endline'], a, b) >= 0.5 for p, a, b in eg):
                ok = False
                break
        if ok:
            return True
    return False


cls = Counter()
events = []        # (group, kind, sha, date, subject, touched/total)
by_group = {}
comment_only = 0
for g in groups:
    present = [o for o in g['occ'] if o['status'] == 'present']
    deleted = len(g['occ']) - len(present)
    touch = defaultdict(set)   # sha -> 사본 index (코드 변경만)
    meta = {}
    for i, o in enumerate(present):
        for c in o['commits']:
            meta[c['sha']] = c
            if c['code']:
                touch[c['sha']].add(i)
            else:
                comment_only += 1
    kinds = []
    if len(present) < 2:
        touch = {}             # 사본이 하나 이하로 줄면 일관/불일치를 따질 수 없다
    for sha in sorted(touch, key=lambda s: meta[s]['date']):
        k = 'consistent' if len(touch[sha]) == len(present) else 'inconsistent'
        kinds.append((sha, k, touch[sha]))
        events.append((g['id'], k, sha, meta[sha]['date'], meta[sha]['subject'], f"{len(touch[sha])}/{len(present)}"))
    # 뒤늦은 전파: 불일치 변경 뒤 다른 커밋이 빠진 사본을 건드렸나
    late = False
    for j, (sha, k, s) in enumerate(kinds):
        if k == 'inconsistent':
            missing = set(range(len(present))) - s
            later = set().union(*[t for _, _, t in kinds[j + 1:]]) if kinds[j + 1:] else set()
            if missing & later:
                late = True
    tog = together_at_end(present) if len(present) >= 2 else None
    if len(present) < 2:
        c = 'collapsed'        # 사본이 하나 이하로 줄었다(삭제·통합)
    elif not kinds:
        c = 'unchanged'
    elif all(k == 'consistent' for _, k, _ in kinds):
        c = 'consistent_only'
    else:
        c = 'has_inconsistent'
    cls[c] += 1
    by_group[g['id']] = {'class': c, 'together_at_end': tog, 'late_propagation': late, 'deleted': deleted,
                         'n_occ': len(g['occ']), 'tokens': g['tokens'],
                         'paths': [o['path'] for o in g['occ']]}

json.dump(by_group, open(f'out/groups-{base}-{end}-t{tok}.json', 'w'), ensure_ascii=False, indent=1)

ev = Counter(k for _, k, *_ in events)
tog = Counter((v['class'], v['together_at_end']) for v in by_group.values())
lp = sum(1 for v in by_group.values() if v['late_propagation'])
n = len(groups)
L = []
L.append(f'# {base} -> {end}, CPD 최소 {tok} 토큰\n')
L.append(f'묶음 {n}개 (사본 수 분포 {dict(Counter(len(g["occ"]) for g in groups))})\n')
L.append('| 묶음 분류 | 개수 | 끝 릴리스에서도 한 묶음 |')
L.append('|---|---|---|')
for c in ['unchanged', 'consistent_only', 'has_inconsistent', 'collapsed']:
    t = tog.get((c, True), 0)
    L.append(f'| {c} | {cls[c]} | {t if c != "collapsed" else "-"} |')
L.append('')
L.append(f'커밋 단위 변경 이벤트: 일관 {ev["consistent"]}, 불일치 {ev["inconsistent"]}')
L.append(f'주석·공백만 바꾼 (커밋, 사본) 쌍: {comment_only} (위 이벤트에서 제외)')
L.append(f'불일치 변경 뒤 창 안에서 빠진 사본이 나중에 바뀐 묶음(뒤늦은 전파 후보): {lp}')
open(f'results/summary-{base}-{end}-t{tok}.md', 'w').write('\n'.join(L) + '\n')
with open(f'results/events-{base}-{end}-t{tok}.tsv', 'w') as f:
    f.write('group\tkind\tsha\tdate\ttouched\tsubject\n')
    for gid, k, sha, date, subj, t in events:
        f.write(f'{gid}\t{k}\t{sha[:10]}\t{date}\t{t}\t{subj}\n')
print('\n'.join(L))
