#!/usr/bin/env python3
"""80편 e28 추적 결과를 한 회차씩 맞춰 본다 (80-e28-trace.sh 가 부른다).
인자: 작업 폴더, 회차 이름. 폴더 안 파일:
  NAME.pod   client 파드 결과: F(실패 전송) N(합계) S(sockstat) 줄
  NAME.tcpd  client 노드 tcpdump (SYN 과 RST 만)
  NAME.mon   client 노드 관측기(80-node-mon.py)
  NAME.meta  key=value: CLI CIP OFF(노드-Mac 초) RESTART(Mac epoch) OLD/NEW(이름=IP@노드 ...)
"""
import re, sys, collections
d, name = sys.argv[1], sys.argv[2]
meta = dict(l.rstrip('\n').split('=', 1) for l in open(f'{d}/{name}.meta') if '=' in l)
CLI, CIP, OFF = meta['CLI'], meta['CIP'], float(meta['OFF'])
R0 = float(meta['RESTART']) + OFF          # 노드 시계로 본 rollout restart 시각
def pods(s):
    r = {}
    for it in s.split():
        n, rest = it.split('=', 1); ip, node = rest.split('@'); r[ip] = (n.rsplit('-', 1)[-1], node)
    return r
OLD, NEW = pods(meta['OLD']), pods(meta['NEW'])
def who(ip):
    if ip in OLD: return f'옛파드 {OLD[ip][0]}({OLD[ip][1].replace("k8s-", "")})'
    if ip in NEW: return f'새파드 {NEW[ip][0]}({NEW[ip][1].replace("k8s-", "")})'
    return ip or '-'
rel = lambda t: f'{t - R0:+6.1f}s'

# 관측기
mp = None; U = []; C = []; D = collections.defaultdict(list)
for l in open(f'{d}/{name}.mon'):
    p = l.split()
    if not p: continue
    if p[0] == 'MAP': mp = (float(p[1]), float(p[2]))
    elif p[0] == 'U': U.append((float(p[1]), int(p[2][4:]), int(p[3][3:])))
    elif p[0] == 'C': C.append((float(p[1]), int(p[2][2:]), p[3:]))
    elif p[0] == 'D': D[int(p[2])].append((float(p[1]), p[3], p[4], int(p[5])))
up2ep = lambda u: mp[1] + (u - mp[0])

# 파드 결과
F = []; N = {}; S = []
for l in open(f'{d}/{name}.pod'):
    p = l.split()
    if not p: continue
    if p[0] == 'F':
        if len(p) == 8 and re.fullmatch(r'\d{3}', p[2]) and re.fullmatch(r'e\d+', p[3]):
            F.append(dict(src=p[1], code=p[2], ex=p[3], t=up2ep(float(p[4])), dur=float(p[5]), con=float(p[6]), n=int(p[7])))
    elif p[0] == 'N': N[p[1]] = int(p[3])   # 200 받은 전송 수
    elif p[0] == 'S': S.append((up2ep(float(p[1])), l.split('TCP:')[1].split()))

# tcpdump: SYN(In: client→ClusterIP, Out: DNAT 뒤 client→파드), RST
rx = re.compile(r'^(\d+\.\d+) (\S+) (In|Out)\s+IP (\d+\.\d+\.\d+\.\d+)\.(\d+) > (\d+\.\d+\.\d+\.\d+)\.(\d+): Flags \[([^\]]+)\], seq (\d+)')
att = collections.OrderedDict()   # seq -> dict (NAT 는 seq 를 바꾸지 않는다)
synin = []
rst_to = collections.defaultdict(list)
for l in open(f'{d}/{name}.tcpd'):
    m = rx.match(l)
    if not m: continue
    t, ifc, dr, s, sp, dd, dp, fl, sq = m.groups(); t = float(t); sp = int(sp); dp = int(dp)
    if fl == 'S' and s == CLI and dr == 'In' and dd == CIP:
        a = att.setdefault(sq, dict(sport=sp, t=t, syn=[], dst=set())); a['syn'].append(t); synin.append(t)
    elif fl == 'S' and dr == 'Out' and sq in att:
        att[sq]['dst'].add(dd if dd != CIP else 'ClusterIP그대로(DNAT없음)')
    elif 'R' in fl and dd == CLI and dr == 'In':
        rst_to[dp].append((t, s))
byport = collections.defaultdict(list)
for a in att.values():
    byport[a['sport']].append(a)
    a['rst'] = any(a['t'] <= t <= a['t'] + 2.1 for t, _ in rst_to[a['sport']])
    a['unans'] = len(a['syn']) >= 2 and not a['rst']

# 1. curl 실패 분류
kinds = collections.Counter()
for f in F:
    if f['ex'] == 'e28': kinds['e28 연결 단계(새 연결, connect 못 함)' if f['con'] == 0 else 'e28 연결 뒤(응답 기다리다)'] += 1
    else: kinds[f['ex']] += 1
ok = sum(N.values()); tot = ok + len(F)
print(f'  요청 {tot}, 실패 {tot - ok}: ' + ', '.join(f'{k} {v}' for k, v in sorted(kinds.items())))
print(f'  rollout restart = 노드 시각 {R0:.1f} (아래 +초는 restart 기준, client 노드 시계, Mac 과 차이 {OFF:+.2f}s)')
print('  옛 파드: ' + ' '.join(f'{v[0]}={k}@{v[1].replace("k8s-", "")}' for k, v in OLD.items()))
print('  새 파드: ' + ' '.join(f'{v[0]}={k}@{v[1].replace("k8s-", "")}' for k, v in NEW.items()))

# 2. 실패 전송 시각(시작 시각, 1초 단위로 묶음)
g = collections.Counter((int(f['t'] - R0 + 1000) - 1000, f['ex'], 'c' if f['con'] > 0 else '-') for f in F)
print('  실패 전송 시작 시각(restart 기준 초, 종류, c=연결된 뒤): ' + ' '.join(f'{s:+d}s {e}{"" if c == "-" else "(c)"}x{n}' for (s, e, c), n in sorted(g.items())))

# 3. SYN 시도
A = list(att.values())
un = [a for a in A if a['unans']]
print(f'  tcpdump SYN 시도 {len(A)}개, RST 받은 시도 {sum(a["rst"] for a in A)}개, 1초 안에 응답 없어 SYN 을 다시 보낸 시도 {len(un)}개')
reused = 0
for a in un:
    prev = [b for b in byport[a['sport']] if b['t'] < a['t']]
    pv = prev[-1] if prev else None
    if pv: reused += 1
    ct = [x for x in D.get(a['sport'], []) if a['t'] - 3.5 <= x[0] <= a['t'] + 3.5]
    ctb = [x for x in ct if x[0] <= a['t']]; cta = [x for x in ct if x[0] > a['t']]
    fmt = lambda x: f'{x[2]}->{who(x[1])} 남은{x[3]}s' if x else '없음'
    print(f'    {rel(a["t"])} 포트 {a["sport"]} SYN {len(a["syn"])}번 DNAT→{",".join(who(x) for x in sorted(a["dst"])) or "노드 밖으로 안 나감"}'
          f' | 이 포트 앞선 사용: {(rel(pv["t"]) + " " + ("RST" if pv["rst"] else "무응답" if pv["unans"] else "응답") + "→" + (",".join(who(x) for x in sorted(pv["dst"])) or "-")) if pv else "없음"}'
          f' | conntrack 직전 {fmt(ctb[-1] if ctb else None)} 직후 {fmt(cta[0] if cta else None)}')
print(f'  응답 없는 시도 {len(un)}개 중 같은 출발 포트를 이 회차에서 앞서 쓴 것 {reused}개')
synin.sort(); gaps = [(a, b - a) for a, b in zip(synin, synin[1:]) if b - a > 0.8]
print('  client 가 보낸 SYN 사이가 0.8초 넘게 빈 때(restart 기준): ' + (' '.join(f'{rel(a)}~{b:.2f}s' for a, b in gaps) or '없음'))

# 4. conntrack: 옛 파드 IP 로 가는 항목(상태별) 추이
print('  conntrack 덤프(client→ClusterIP:80, TIME_WAIT 아닌 항목만 상태별, 옛 파드 IP 로 가는 것):')
for t, n, items in C:
    o = [i for i in items if i.split('/')[0] in OLD and '/TIME_WAIT=' not in i]
    tw = sum(int(i.split('=')[1]) for i in items if i.split('/')[0] in OLD and '/TIME_WAIT=' in i)
    print(f'    {rel(t)} 전체 {n}, 옛 파드 TIME_WAIT {tw}, 그 밖: {" ".join(who(i.split("/")[0]).split("(")[0].replace("옛파드 ", "") + "/" + i.split("/")[1] for i in o) or "없음"}')

# 5. CPU, 소켓
cpu_fail = [c for t, c, _ in U if any(abs(f['t'] - t) < 1.5 for f in F if f['ex'] == 'e28')]
print(f'  client 노드 CPU 바쁨: 전체 {min(c for _, c, _ in U)}~{max(c for _, c, _ in U)}%, e28 시작 ±1.5초 안 {min(cpu_fail) if cpu_fail else "-"}~{max(cpu_fail) if cpu_fail else "-"}%')
tw = [int(v[v.index('tw') + 1]) for _, v in S if 'tw' in v]; inuse = [int(v[v.index('inuse') + 1]) for _, v in S if 'inuse' in v]
print(f'  client 파드 소켓(/proc/net/sockstat): TIME_WAIT {min(tw)}~{max(tw)}, inuse {min(inuse)}~{max(inuse)} (출발 포트 범위 32768~60999 = 28232개)')

# 6. e28 전송과 응답 없는 SYN 시도 대조 (e28 시작 -0.3~+0.5초 안에 첫 SYN 이 나간 시도)
e28 = sorted((f for f in F if f['ex'] == 'e28'), key=lambda x: x['t'])
used = set(); m = collections.Counter(); late = []
tend = max((a['t'] for a in A), default=R0)
for f in e28:
    cand = [a for a in un if id(a) not in used and -0.3 <= a['syn'][0] - f['t'] <= 0.5]
    if not cand:
        late.append(f); continue
    a = min(cand, key=lambda a: abs(a['syn'][0] - f['t'])); used.add(id(a))
    k = '옛 파드' if any(x in OLD for x in a['dst']) else '새 파드' if any(x in NEW for x in a['dst']) else '그 밖'
    m[(k, '포트 다시 씀' if [b for b in byport[a['sport']] if b['t'] < a['t']] else '포트 처음')] += 1
rest = [a for a in un if id(a) not in used]
print(f'  e28 {len(e28)}건 대조: ' + ', '.join(f'{k}로 DNAT·{r} {v}' for (k, r), v in sorted(m.items()))
      + (f', tcpdump 이 끝난 {rel(tend)} 뒤라 대조 못 함 {len(late)}' if late else ''))
print(f'  e28 이 아닌 응답 없는 시도 {len(rest)}개: ' + (' '.join(f'{rel(a["t"])}→{"새 파드" if any(x in NEW for x in a["dst"]) else "옛 파드"}' for a in rest) or '없음')
      + ' (실패한 전송과 짝이 없다: 다시 보낸 SYN 뒤에 응답을 받은 것으로 본다)' * bool(rest))
print(f'  응답 없는 시도의 출발 포트가 모두 짝수: {all(a["sport"] % 2 == 0 for a in un) if un else "-"}')
