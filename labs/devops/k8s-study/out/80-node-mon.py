#!/usr/bin/env python3
"""80편 e28 추적용 노드 관측기 (읽기만 한다).
conntrack CLI 와 /proc/net/nf_conntrack 이 없는 노드라서 커널 nfnetlink conntrack 에 dump 를 요청해 읽는다(conntrack -L 과 같은 정보).
인자: 관측 초, client 파드 IP, ClusterIP, 덤프 간격(초)
출력(한 줄씩, 시각은 노드 epoch 초):
  MAP <uptime> <epoch>                       파드 안 /proc/uptime 을 epoch 으로 바꾸는 기준
  U <epoch> cpu=<바쁨%> ct=<conntrack 전체 개수>  1초마다
  C <epoch> n=<client→ClusterIP:80 항목 수> <목적지 파드 IP>/<상태>=<개수> ...   덤프마다 요약
  D <epoch> <출발 포트> <목적지 파드 IP> <상태> <남은 초>   TIME_WAIT 가 아닌 항목 하나하나
"""
import socket, struct, sys, time

dur, cli, cip, every = float(sys.argv[1]), sys.argv[2], sys.argv[3], float(sys.argv[4])
STATES = ['NONE', 'SYN_SENT', 'SYN_RECV', 'ESTABLISHED', 'FIN_WAIT', 'CLOSE_WAIT', 'LAST_ACK', 'TIME_WAIT', 'CLOSE', 'SYN_SENT2']
cli_b, cip_b = socket.inet_aton(cli), socket.inet_aton(cip)

def attrs(data):
    r = {}
    while len(data) >= 4:
        ln, kind = struct.unpack_from('HH', data)
        if ln < 4 or ln > len(data):
            break
        r[kind & 0x3fff] = data[4:ln]
        data = data[(ln + 3) & ~3:]
    return r

def tup(data):
    a = attrs(data)
    ip, pr = attrs(a.get(1, b'')), attrs(a.get(2, b''))
    if pr.get(1) != b'\x06' or 1 not in ip:
        return None
    return ip[1], ip[2], struct.unpack('!H', pr[2])[0], struct.unpack('!H', pr[3])[0]

def dump():
    s = socket.socket(socket.AF_NETLINK, socket.SOCK_RAW, 12)  # NETLINK_NETFILTER
    s.settimeout(5); s.bind((0, 0))
    s.send(struct.pack('IHHII', 20, (1 << 8) | 1, 0x301, 1, 0) + struct.pack('BBH', socket.AF_INET, 0, 0))
    out, done = [], False
    while not done:
        data = s.recv(4 * 1024 * 1024)
        while len(data) >= 16:
            ln, kind, flags, seq, pid = struct.unpack_from('IHHII', data)
            body = data[16:ln]
            if kind == 3:
                done = True
            elif kind == 2 and struct.unpack_from('i', body)[0]:
                raise OSError('dump failed')
            elif kind == 256 and cip_b in body and cli_b in body:
                a = attrs(body[4:])
                o = tup(a.get(1, b''))
                if o and o[0] == cli_b and o[1] == cip_b and o[3] == 80:
                    rp = tup(a.get(2, b''))
                    st = attrs(attrs(a.get(4, b'')).get(1, b'')).get(1, b'\x00')[0]
                    to = struct.unpack('!I', a[7])[0] if 7 in a else -1
                    out.append((o[2], socket.inet_ntoa(rp[0]) if rp else '?', STATES[st] if st < len(STATES) else str(st), to))
            data = data[(ln + 3) & ~3:]
    s.close()
    return out

def cpu():
    with open('/proc/stat') as f:
        v = list(map(int, f.readline().split()[1:]))
    return sum(v), v[3] + v[4]

with open('/proc/uptime') as f:
    print('MAP', f.read().split()[0], '%.3f' % time.time(), flush=True)
end = time.time() + dur
t0, i0 = cpu(); nxt = time.time()
while time.time() < end:
    time.sleep(1)
    t1, i1 = cpu()
    with open('/proc/sys/net/netfilter/nf_conntrack_count') as f:
        ct = f.read().strip()
    print('U %.3f cpu=%.0f ct=%s' % (time.time(), 100.0 * (1 - (i1 - i0) / max(1, t1 - t0)), ct), flush=True)
    t0, i0 = t1, i1
    if time.time() >= nxt:
        nxt = time.time() + every
        now = time.time(); es = dump(); cnt = {}
        for sport, dst, st, to in es:
            cnt[(dst, st)] = cnt.get((dst, st), 0) + 1
            if st != 'TIME_WAIT':
                print('D %.3f %d %s %s %d' % (now, sport, dst, st, to))
        print('C %.3f n=%d %s' % (now, len(es), ' '.join('%s/%s=%d' % (d, s, c) for (d, s), c in sorted(cnt.items()))), flush=True)
