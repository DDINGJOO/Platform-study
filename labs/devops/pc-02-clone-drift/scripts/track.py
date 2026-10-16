#!/usr/bin/env python3
"""기준 릴리스의 복제 묶음을 다음 릴리스까지 따라가며, 어떤 커밋이 묶음의 어느 사본을 고쳤는지 센다.

  python3 scripts/track.py <WORK> <base-tag> <end-tag> [최소토큰=100]

입력  out/cpd-<base>-t<N>.xml, out/cpd-<end>-t<N>.xml (scripts/cpd.sh 결과)
출력  out/track-<base>-<end>-t<N>.json  묶음, 사본, 사본별로 손댄 커밋(코드 줄 변경 여부 포함)

사본 하나를 따라가는 법
 1. 기준 릴리스의 줄 범위를 끝 릴리스의 줄 범위로 옮긴다(git diff base end -U0 의 hunk 로 계산).
    파일이 사라졌으면 rename 을 찾고(git diff -M), 그래도 없으면 "삭제"로 둔다.
 2. 끝 릴리스 기준 범위로 git log -L <a>,<b>:<path> base..end 를 돌려 그 줄을 바꾼 커밋을 모두 얻는다.
    -L 은 머지를 거슬러 실제로 바꾼 커밋을 찾아 준다(유지보수 브랜치에서 올라온 커밋 포함).
 3. 커밋마다 그 범위 안에서 지운 줄/더한 줄을 보고, 주석·공백만 바뀌었는지 코드가 바뀌었는지 가른다.
"""
import json, re, subprocess, sys, xml.etree.ElementTree as ET
from collections import defaultdict

NS = {'c': 'https://pmd-code.org/schema/cpd-report'}


def git(repo, *args):
    return subprocess.run(['git', '-C', repo, *args], check=True, capture_output=True, text=True,
                          errors='replace').stdout


def load_groups(xml_path, prefix):
    root = ET.parse(xml_path).getroot()
    groups = []
    for i, d in enumerate(root.findall('c:duplication', NS)):
        occ = []
        for f in d.findall('c:file', NS):
            p = f.get('path')
            if p.startswith(prefix):
                p = p[len(prefix):]
            occ.append({'path': p, 'line': int(f.get('line')), 'endline': int(f.get('endline'))})
        groups.append({'id': i, 'tokens': int(d.get('tokens')), 'lines': int(d.get('lines')), 'occ': occ})
    return groups


HUNK = re.compile(r'^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@')


def hunks(repo, base, end, old, new):
    out = git(repo, 'diff', '-U0', '--no-color', base, end, '--', old) if old == new else \
        git(repo, 'diff', '-U0', '--no-color', '-M', base, end, '--', old, new)
    hs = []
    for ln in out.splitlines():
        m = HUNK.match(ln)
        if m:
            os_, ol, ns_, nl = int(m[1]), int(m[2] or 1), int(m[3]), int(m[4] or 1)
            hs.append((os_, ol, ns_, nl))
    return hs


def map_line(hs, x, side):
    """기준 릴리스의 줄 x 를 끝 릴리스의 줄로. side=start 면 hunk 시작 쪽, end 면 끝 쪽으로 붙인다."""
    shift = 0
    for os_, ol, ns_, nl in hs:
        o_first = os_ if ol > 0 else os_ + 1   # ol==0 이면 os_ 줄 '뒤'에 끼운 것
        o_last = os_ + ol - 1
        if ol > 0 and o_first <= x <= o_last:
            if nl == 0:
                return ns_ + (1 if side == 'start' else 0)
            return ns_ if side == 'start' else ns_ + nl - 1
        if (ol > 0 and x > o_last) or (ol == 0 and x > os_):
            shift += nl - ol
    return x + shift


def end_path(repo, base, end, path, end_files):
    if path in end_files:
        return path
    out = git(repo, 'diff', '-M', '--name-status', '--diff-filter=R', base, end)
    for ln in out.splitlines():
        parts = ln.split('\t')
        if len(parts) == 3 and parts[1] == path:
            return parts[2]
    return None


COMMENT = re.compile(r'^\s*(\*|/\*|//|\*/)')


def code_lines(lines):
    return [l.strip() for l in lines if l.strip() and not COMMENT.match(l)]


def log_L(repo, base, end, a, b, path):
    out = git(repo, 'log', f'-L{a},{b}:{path}', '--no-merges', '--format=@@C %H %cs %an%x09%s', f'{base}..{end}')
    commits, cur = [], None
    for ln in out.splitlines():
        if ln.startswith('@@C '):
            sha, date, rest = ln[4:].split(' ', 2)
            author, subj = rest.split('\t', 1) if '\t' in rest else (rest, '')
            cur = {'sha': sha, 'date': date, 'author': author, 'subject': subj, 'minus': [], 'plus': []}
            commits.append(cur)
        elif cur is not None:
            if ln.startswith('-') and not ln.startswith('---'):
                cur['minus'].append(ln[1:])
            elif ln.startswith('+') and not ln.startswith('+++'):
                cur['plus'].append(ln[1:])
    for c in commits:
        c['code'] = code_lines(c['minus']) != code_lines(c['plus'])
        c['n_minus'], c['n_plus'] = len(c['minus']), len(c['plus'])
        del c['minus'], c['plus']
    return commits


def main():
    work, base, end = sys.argv[1], sys.argv[2], sys.argv[3]
    tok = sys.argv[4] if len(sys.argv) > 4 else '100'
    repo = f'{work}/src/repo'
    groups = load_groups(f'out/cpd-{base}-t{tok}.xml', f'{work}/snap/{base}/')
    end_groups = load_groups(f'out/cpd-{end}-t{tok}.xml', f'{work}/snap/{end}/')
    end_files = set(git(repo, 'ls-tree', '-r', '--name-only', end).splitlines())
    hcache = {}
    for g in groups:
        for o in g['occ']:
            ep = end_path(repo, base, end, o['path'], end_files)
            o['end_path'] = ep
            if ep is None:
                o['status'], o['commits'] = 'deleted', []
                continue
            key = (o['path'], ep)
            if key not in hcache:
                hcache[key] = hunks(repo, base, end, o['path'], ep)
            hs = hcache[key]
            a, b = map_line(hs, o['line'], 'start'), map_line(hs, o['endline'], 'end')
            o['end_line'], o['end_endline'] = a, b
            if b < a:
                o['status'], o['commits'] = 'deleted', []
                continue
            o['status'] = 'present'
            o['commits'] = log_L(repo, base, end, a, b, ep)
        print(f"group {g['id']}: {[len(o['commits']) for o in g['occ']]}", file=sys.stderr)
    out = {'base': base, 'end': end, 'min_tokens': int(tok), 'groups': groups,
           'end_groups': [[(o['path'], o['line'], o['endline']) for o in eg['occ']] for eg in end_groups]}
    with open(f'out/track-{base}-{end}-t{tok}.json', 'w') as f:
        json.dump(out, f, ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
