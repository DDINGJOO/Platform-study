#!/usr/bin/env bash
set -euo pipefail
export LC_ALL=C
names=(cb53-src cb53-rtr cb53-dst)
for n in "${names[@]}"; do
  if ip netns list | awk '{print $1}' | grep -Fxq "$n"; then
    echo "existing namespace $n; refusing to alter" >&2; exit 1
  fi
done
if test -e /tmp/cb53-evidence; then echo 'existing evidence directory' >&2; exit 1; fi
mkdir /tmp/cb53-evidence
server_pid=''
capture_pid=''
cleanup() {
  if test -n "$capture_pid"; then kill -INT "$capture_pid" 2>/dev/null || true; wait "$capture_pid" 2>/dev/null || true; fi
  if test -n "$server_pid"; then kill "$server_pid" 2>/dev/null || true; wait "$server_pid" 2>/dev/null || true; fi
  for n in "${names[@]}"; do ip netns del "$n" 2>/dev/null || true; done
  echo 'cleanup: cb53-src cb53-rtr cb53-dst deleted'
}
trap cleanup EXIT
run() {
  printf '\n$'; printf ' %q' "$@"; printf '\n'
  "$@"
}
probe() {
  printf '\n$'; printf ' %q' "$@"; printf '\n'
  set +e; "$@"; code=$?; set -e
  printf 'exit_code=%s\n' "$code"
}
date --iso-8601=seconds
for n in "${names[@]}"; do run ip netns add "$n"; ip -n "$n" link set lo up; done
ip link add cb53-sa type veth peer name cb53-rs
ip link set cb53-sa netns cb53-src
ip link set cb53-rs netns cb53-rtr
ip link add cb53-rd type veth peer name cb53-dr
ip link set cb53-rd netns cb53-rtr
ip link set cb53-dr netns cb53-dst
ip -n cb53-src address add 192.0.2.2/24 dev cb53-sa
ip -n cb53-rtr address add 192.0.2.1/24 dev cb53-rs
ip -n cb53-rtr address add 198.51.100.1/24 dev cb53-rd
ip -n cb53-dst address add 198.51.100.2/24 dev cb53-dr
ip -n cb53-src link set cb53-sa up mtu 1500
ip -n cb53-rtr link set cb53-rs up mtu 1500
ip -n cb53-rtr link set cb53-rd up mtu 1300
ip -n cb53-dst link set cb53-dr up mtu 1500
ip -n cb53-src route add default via 192.0.2.1
ip -n cb53-dst route add default via 198.51.100.1
run ip netns exec cb53-rtr sysctl -w net.ipv4.ip_forward=1
run ip netns exec cb53-src sysctl -w net.ipv4.tcp_mtu_probing=0
if command -v ethtool >/dev/null; then
  for pair in 'cb53-src cb53-sa' 'cb53-rtr cb53-rs' 'cb53-rtr cb53-rd' 'cb53-dst cb53-dr'; do
    read -r ns dev <<<"$pair"
    probe ip netns exec "$ns" ethtool -K "$dev" tso off gso off gro off
  done
fi
for n in "${names[@]}"; do run ip -n "$n" -br link; run ip -n "$n" route; done
cat >/tmp/cb53-evidence/server.py <<'PY'
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
class Handler(BaseHTTPRequestHandler):
 def do_POST(self):
  data=self.rfile.read(int(self.headers['Content-Length']))
  if len(data)!=int(self.headers['Content-Length']): return
  reply=f'received={len(data)}\n'.encode()
  self.send_response(200);self.send_header('Content-Length',str(len(reply)));self.end_headers()
  self.wfile.write(reply)
ThreadingHTTPServer(('198.51.100.2',18553),Handler).serve_forever()
PY
python3 - <<'PY'
from pathlib import Path
Path('/tmp/cb53-evidence/body.bin').write_bytes(b'x'*65536)
PY
ip netns exec cb53-dst python3 -u /tmp/cb53-evidence/server.py >/tmp/cb53-evidence/server.log 2>&1 &
server_pid=$!
sleep 0.3
run ip netns exec cb53-rtr iptables -A OUTPUT -p icmp --icmp-type 3/4 -j DROP
ip netns exec cb53-src tcpdump -U -n -i cb53-sa -w /tmp/cb53-evidence/blocked.pcap 'icmp or tcp port 18553' 2>/tmp/cb53-evidence/blocked-capture.log &
capture_pid=$!
sleep 0.3
echo '=== ICMP fragmentation-needed blocked ==='
probe ip netns exec cb53-src ping -4 -n -c 1 -W 1 -M do -s 100 198.51.100.2
probe ip netns exec cb53-src ping -4 -n -c 1 -W 1 -M do -s 1400 198.51.100.2
probe ip netns exec cb53-src curl --noproxy '*' --silent --show-error --max-time 4 -H 'Expect:' --data-binary @/tmp/cb53-evidence/body.bin -w 'http=%{http_code} uploaded=%{size_upload} total=%{time_total}\n' http://198.51.100.2:18553/
run ip netns exec cb53-rtr iptables -nvL OUTPUT
run ip -n cb53-src route get 198.51.100.2
kill -INT "$capture_pid";wait "$capture_pid" || true;capture_pid=''
tcpdump -K -nn -tttt -vv -S -r /tmp/cb53-evidence/blocked.pcap >/tmp/cb53-evidence/blocked.txt 2>&1
echo '=== allow feedback, same 1300-byte bottleneck ==='
run ip netns exec cb53-rtr iptables -D OUTPUT -p icmp --icmp-type 3/4 -j DROP
ip netns exec cb53-src tcpdump -U -n -i cb53-sa -w /tmp/cb53-evidence/allowed.pcap 'icmp or tcp port 18553' 2>/tmp/cb53-evidence/allowed-capture.log &
capture_pid=$!
sleep 0.3
probe ip netns exec cb53-src curl --noproxy '*' --silent --show-error --max-time 4 -H 'Expect:' --data-binary @/tmp/cb53-evidence/body.bin -w 'http=%{http_code} uploaded=%{size_upload} total=%{time_total}\n' http://198.51.100.2:18553/
run ip -n cb53-src route get 198.51.100.2
probe ip netns exec cb53-src ping -4 -n -c 1 -W 1 -M do -s 1272 198.51.100.2
probe ip netns exec cb53-src ping -4 -n -c 1 -W 1 -M do -s 1273 198.51.100.2
kill -INT "$capture_pid";wait "$capture_pid" || true;capture_pid=''
tcpdump -K -nn -tttt -vv -S -r /tmp/cb53-evidence/allowed.pcap >/tmp/cb53-evidence/allowed.txt 2>&1
echo '=== source capture excerpts ==='
head -45 /tmp/cb53-evidence/blocked.txt
head -45 /tmp/cb53-evidence/allowed.txt
