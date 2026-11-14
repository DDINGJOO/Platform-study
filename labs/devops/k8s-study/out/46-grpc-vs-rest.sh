#!/usr/bin/env bash
# 46편: 구성 요소 사이 연결 중 gRPC 로 오가는 곳과 HTTP(REST) 로 오가는 곳을 조회만으로 확인한다.
# 파드·설정을 만들거나 바꾸지 않는다. 실습 저장소 루트(./lab 이 있는 곳)에서 bash <이 스크립트> 로 실행한다.
K="./lab kubectl"
echo "# 46 gRPC 와 REST 가 실제로 쓰이는 곳 ($(date '+%F %T %Z'), Mac 에서 실습 저장소 루트로 실행, 조회만)"

echo; echo "## 1. API 서버(6443)는 HTTP/2 위의 REST: worker1 에서 익명으로 /version (CA 확인은 함)"
./lab ssh worker1 -- sudo bash -s <<'R'
curl -sv --cacert /etc/kubernetes/pki/ca.crt https://192.168.104.1:6443/version 2>&1 \
  | grep -E 'ALPN|^< HTTP|^< content-type|"gitVersion"' | sed 's/^/  /'
R

echo; echo "## 2. etcd 는 gRPC 서버: 서비스·메서드별로 처리한 호출 수 (master, etcd 메트릭 127.0.0.1:2381, 0 인 줄은 뺌)"
./lab ssh master -- sudo bash -s <<'R'
M=$(curl -s http://127.0.0.1:2381/metrics)
echo "  etcd 프로세스 시작 시각: $(ps -o lstart= -C etcd)"
echo "$M" | grep -E '^grpc_server_handled_total' | grep 'grpc_code="OK"' \
  | sed -E 's/.*grpc_method="([^"]+)",grpc_service="([^"]+)",grpc_type="([^"]+)"} (.*)/\4 \2 \1 \3/' \
  | awk '$1>0 {printf "  %10d  %-28s %-16s %s\n", $1, $2, $3, $4}' | sort -k1,1nr
echo "  --- 스트림 RPC: 시작한 수와 끝난 수 (차이가 지금 열려 있는 스트림)"
for ms in "Watch etcdserverpb.Watch" "LeaseKeepAlive etcdserverpb.Lease" "RangeStream etcdserverpb.KV"; do
  set -- $ms
  s=$(echo "$M" | grep -E "^grpc_server_started_total\{grpc_method=\"$1\",grpc_service=\"$2\"" | awk '{s+=$2} END{print s+0}')
  h=$(echo "$M" | grep -E "^grpc_server_handled_total\{.*grpc_method=\"$1\",grpc_service=\"$2\"" | awk '{s+=$2} END{print s+0}')
  echo "  $2/$1 스트림 시작 $s, 끝남 $h"
done
echo "  --- etcd 안의 watch 수"
echo "$M" | grep -E '^etcd_debugging_mvcc_(watch_stream_total|watcher_total)' | sed 's/^/  /'
echo "  --- etcd 가 연 포트 (2379 클라이언트 gRPC, 2380 멤버끼리, 2381 메트릭)"
ss -ltnp | grep '"etcd"' | awk '{printf "  LISTEN %s\n", $4}'
echo "  2380 에 맺어진 연결 수: $(ss -tn state established '( sport = :2380 or dport = :2380 )' | tail -n +2 | wc -l)"
echo "  2379 로 연결을 연 프로세스: $(ss -tnp state established '( dport = :2379 )' | grep -o 'users:(("[^"]*' | sort | uniq -c | sed 's/users:(("//' | xargs)"
echo "  --- 같은 2379 에 HTTP/JSON 으로 Range 를 보내면 (etcd 의 grpc-gateway, /registry/namespaces/ 아래 키 개수만, API 서버의 etcd 클라이언트 인증서 사용)"
P=/etc/kubernetes/pki
curl -s -w '\n  (HTTP %{http_version}, %{content_type})\n' --cacert $P/etcd/ca.crt --cert $P/apiserver-etcd-client.crt --key $P/apiserver-etcd-client.key \
  -X POST https://127.0.0.1:2379/v3/kv/range \
  -d '{"key":"L3JlZ2lzdHJ5L25hbWVzcGFjZXMv","range_end":"L3JlZ2lzdHJ5L25hbWVzcGFjZXMw","count_only":true}' | sed 's/^/  /'
R

echo; echo "## 3. API 서버가 받은 watch 수 (API 서버 메트릭)"
$K get --raw /metrics | grep -E '^apiserver_longrunning_requests\{.*verb="WATCH"' \
  | awk '{s+=$2} END{print "  apiserver_longrunning_requests (WATCH) 합계: " s}'
$K get --raw /metrics | grep -E '^apiserver_watch_cache_resource_version\{' \
  | awk '{n++} END{print "  watch 캐시를 둔 리소스 종류 (apiserver_watch_cache_resource_version 줄 수): " n}'

echo; echo "## 4. kubelet 과 containerd: CRI 는 gRPC, exec·logs 스트림은 따로 (worker1)"
./lab ssh worker1 -- sudo bash -s <<'R'
echo "  --- CRI 버전 (crictl 이 CRI gRPC 로 묻는다)"
crictl version | sed 's/^/  /'
echo "  --- containerd 의 CRI 스트리밍 서버 설정"
containerd config dump 2>/dev/null | grep -E "stream_server_address|stream_server_port|enable_tls_streaming|stream_idle_timeout" | sed -E 's/^ +/  /'
echo "  --- containerd 가 연 TCP 포트"
ss -ltnp | grep '"containerd"' | awk '{printf "  LISTEN %s\n", $4}'
echo "  --- kubelet 이 서버로 여는 유닉스 소켓 (장치 플러그인 등록, pod-resources)"
ls -l /var/lib/kubelet/device-plugins/ /var/lib/kubelet/pod-resources/ 2>&1 | sed 's/^/  /'
R
