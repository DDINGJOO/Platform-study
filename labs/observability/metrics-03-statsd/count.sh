#!/usr/bin/env bash
# 받은 쪽 숫자를 한 줄로 찍는다: 보낸 수는 sender 로그에서, 나머지는 statsd_exporter 지표와 커널 카운터에서.
cd "$(dirname "$0")"
m=$(curl -s "http://localhost:${STATSD_WEB_PORT:-21302}/metrics")
get(){ echo "$m" | awk -v n="$1" '$1==n{printf "%d", $2}'; }
snmp=$(docker compose exec -T statsd cat /proc/net/snmp | awk '/^Udp:/{n++} n==2 && /^Udp:/{print; exit}')
read -r _ indg noports inerr outdg rcvbuf _ <<<"$snmp"
printf "udp_packets(exporter)=%s  unixgram_packets(exporter)=%s  queue_drops(exporter)=%s  lab_sent=%s  kernel InDatagrams=%s  RcvbufErrors=%s  InErrors=%s\n" \
  "$(get statsd_exporter_udp_packets_total)" "$(get statsd_exporter_unixgram_packets_total)" "$(get statsd_exporter_udp_packet_drops_total)" "$(get lab_sent)" "$indg" "$rcvbuf" "$inerr"
