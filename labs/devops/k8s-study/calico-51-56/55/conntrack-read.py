#!/usr/bin/env python3
"""Read-only nfnetlink dump; print only TCP connections to experiment port."""
import json
import socket
import struct
import sys

port = int(sys.argv[1]) if len(sys.argv) > 1 else 18555

def attrs(data):
    result = {}
    while len(data) >= 4:
        length, kind = struct.unpack_from('HH', data)
        if length < 4 or length > len(data):
            raise ValueError('malformed netlink attribute')
        result[kind & 0x3fff] = data[4:length]
        data = data[(length + 3) & ~3:]
    return result

def tuple4(data):
    a = attrs(data)
    ip, proto = attrs(a[1]), attrs(a[2])
    if 1 not in ip or proto.get(1) != bytes([6]):
        return None
    return {'src': socket.inet_ntoa(ip[1]), 'dst': socket.inet_ntoa(ip[2]),
            'sport': struct.unpack('!H', proto[2])[0],
            'dport': struct.unpack('!H', proto[3])[0]}

sock = socket.socket(socket.AF_NETLINK, socket.SOCK_RAW, 12)
sock.settimeout(5)
sock.bind((0, 0))
payload = struct.pack('BBH', socket.AF_INET, 0, 0)
sock.send(struct.pack('IHHII', 16 + len(payload), 257, 0x301, 1, 0) + payload)
results = []
done = False
while not done:
    data = sock.recv(1024 * 1024)
    while len(data) >= 16:
        length, kind, flags, sequence, pid = struct.unpack_from('IHHII', data)
        body = data[16:length]
        if kind == 3:
            done = True
        elif kind == 2:
            error = struct.unpack_from('i', body)[0]
            if error:
                raise OSError(-error, 'nfnetlink dump failed')
        elif kind == 256:
            a = attrs(body[4:])
            original = tuple4(a[1])
            if original and original['dport'] == port:
                reply = tuple4(a[2])
                status = struct.unpack('!I', a[3])[0]
                results.append({'original': original, 'reply': reply,
                                'status': hex(status), 'src_nat': bool(status & 16),
                                'timeout_seconds': struct.unpack('!I', a[7])[0]})
        data = data[(length + 3) & ~3:]
print(json.dumps(results, indent=2))
