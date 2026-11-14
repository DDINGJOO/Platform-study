#!/usr/bin/env bash
# 실습 저장소의 shared/components/11-apiserver-clients.sh 를 옮긴 것. 실습 저장소 루트에서 실행한다.
# API 서버에 실제로 붙어 있는 클라이언트: 노드마다 컨테이너의 네트워크 네임스페이스 안에서 6443(직접) 또는 10.96.0.1:443(kubernetes Service) 연결을 찾는다 (Mac 에서 실행)
cd "$(dirname "$0")/../.."   # 실습 저장소 루트 (./lab 이 있는 곳)
echo "# API 서버에 붙어 있는 클라이언트 ($(date '+%F %T %Z'))"
for n in master 1 2 3; do
  ./lab ssh $n -- sudo bash -s <<'R'
H=$(hostname | sed 's/^lima-//')
echo; echo "[$H]"
# 호스트 네트워크(systemd 서비스·hostNetwork 파드)
ss -tnpH state established '( dport = :6443 or dport = :443 )' 2>/dev/null | awk '$4 ~ /(192\.168\.104\.1:6443|10\.96\.0\.1:443)$/' | grep -oE 'users:\(\("[^"]+' | sed 's/users:((\"//' | sort | uniq -c | awk '{printf "  host  %-24s 연결 %s\n", $2, $1}'
# 파드 네트워크 네임스페이스마다
for c in $(crictl ps -q 2>/dev/null); do
  pid=$(crictl inspect -o go-template --template '{{.info.pid}}' $c 2>/dev/null)
  [ -z "$pid" ] && continue
  hn=$(readlink /proc/$pid/ns/net); [ "$hn" = "$(readlink /proc/1/ns/net)" ] && continue
  n=$(nsenter -t $pid -n ss -tnH state established 2>/dev/null | awk '$4 ~ /(10\.96\.0\.1:443|192\.168\.104\.1:6443)$/' | wc -l)
  [ "$n" -gt 0 ] || continue
  pod=$(crictl inspect -o go-template --template '{{index .status.labels "io.kubernetes.pod.namespace"}}/{{index .status.labels "io.kubernetes.pod.name"}} ({{.status.metadata.name}})' $c 2>/dev/null)
  printf "  pod   %-60s 연결 %s\n" "$pod" "$n"
done
R
done
