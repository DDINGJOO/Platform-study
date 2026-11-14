#!/usr/bin/env bash
# CoreDNS 로 서비스 이름 풀기: redis-dns Deployment + redis-dns-svc Service 를 만들고 다른 파드에서 이름으로 찾아 접속 (Mac 에서 실행)
cd "$(dirname "$0")/../.."   # 실습 저장소 루트 (./lab 이 있는 곳)
K="./lab kubectl"; ts(){ date '+%T'; }
echo "# E19 CoreDNS 를 이용한 DNS 검증 ($(date '+%F %T %Z'))"
$K delete deploy redis-dns --ignore-not-found >/dev/null; $K delete svc redis-dns-svc --ignore-not-found >/dev/null; $K delete pod dns-client --ignore-not-found --now >/dev/null; $K delete ns dns-test --ignore-not-found >/dev/null
echo; echo "## 1. 검증용 Deployment 와 Service"
echo "\$ kubectl create deployment redis-dns --image=redis --replicas=1"; $K create deployment redis-dns --image=redis --replicas=1
echo "\$ kubectl expose deployment redis-dns --name=redis-dns-svc --port=6379 --target-port=6379"; $K expose deployment redis-dns --name=redis-dns-svc --port=6379 --target-port=6379
$K rollout status deploy/redis-dns --timeout=180s >/dev/null
echo "\$ kubectl get deploy,po,svc -o wide | grep redis-dns"; $K get deploy,po,svc -o wide | grep redis-dns
echo "redis 버전: $($K exec deploy/redis-dns -- redis-server --version | cut -c1-40)"
SIP=$($K get svc redis-dns-svc -o jsonpath='{.spec.clusterIP}')
echo; echo "## 2. 클라이언트 파드 (Service 를 만든 뒤에 생성)"
$K run dns-client --image=busybox:1.36.1 --restart=Never -- sleep 600 >/dev/null; $K wait --for=condition=Ready pod/dns-client --timeout=120s >/dev/null
echo "dns-client 노드: $($K get pod dns-client -o jsonpath='{.spec.nodeName}')"
echo "resolv.conf: $($K exec dns-client -- cat /etc/resolv.conf | grep -E 'nameserver|search|options' | sed 's/ [A-Za-z0-9-]*$//;' | paste -sd'|' -)"
# 이름 풀이는 파드의 기본 리졸버(resolv.conf 의 search·ndots 적용)로 확인: ping 첫 줄의 (IP). ClusterIP 는 ping 응답이 없어도 풀이 결과는 찍힘
q(){ r=$($K exec ${2:-dns-client} ${3:+-n $3} -- ping -c1 -W1 $1 2>&1 | head -1 | grep -oE '\([0-9.]+\)' | tr -d '()'); echo "  $1 → ${r:-못 찾음}"; }
echo "같은 네임스페이스(default)에서:"
q redis-dns-svc; q redis-dns-svc.default; q redis-dns-svc.default.svc; q redis-dns-svc.default.svc.cluster.local
echo "  (Service ClusterIP = $SIP)"
echo; echo "## 3. 다른 네임스페이스에서는 짧은 이름이 안 됨"
$K create ns dns-test >/dev/null; $K -n dns-test run dns-client2 --image=busybox:1.36.1 --restart=Never -- sleep 600 >/dev/null; $K -n dns-test wait --for=condition=Ready pod/dns-client2 --timeout=120s >/dev/null
echo "dns-test/dns-client2 의 search: $($K -n dns-test exec dns-client2 -- grep search /etc/resolv.conf | awk '{print $2, $3, $4}')"
q redis-dns-svc dns-client2 dns-test; q redis-dns-svc.default dns-client2 dns-test
echo; echo "## 4. 이름으로 redis 에 접속"
echo "dns-client\$ printf 'PING\\r\\n' | nc -w 2 redis-dns-svc 6379 → $($K exec dns-client -- sh -c "printf 'PING\r\n' | nc -w 2 redis-dns-svc 6379" | tr -d '\r')"
echo "dns-test/dns-client2\$ … nc redis-dns-svc.default 6379 → $($K -n dns-test exec dns-client2 -- sh -c "printf 'PING\r\n' | nc -w 2 redis-dns-svc.default 6379" | tr -d '\r')"
echo; echo "## 5. DNS 말고 환경 변수로도 알려 줌 (컨테이너 시작 시점에 이미 있던 Service 만)"
$K exec dns-client -- env | grep -E '^REDIS_DNS_SVC_(SERVICE_HOST|SERVICE_PORT)=' | sed 's/^/  /'
echo "  svc 생성 $($K get svc redis-dns-svc -o jsonpath='{.metadata.creationTimestamp}') / redis-dns 컨테이너 시작 $($K get pod -l app=redis-dns -o jsonpath='{.items[0].status.containerStatuses[0].state.running.startedAt}') → redis-dns 파드에도 $($K exec deploy/redis-dns -- env | grep -c '^REDIS_DNS_SVC_SERVICE_HOST')개 (kubelet 은 컨테이너를 시작할 때 그 순간의 Service 목록으로 변수를 만듦)"
echo; echo "## 6. 파드 IP 도 이름이 있음 (Corefile 'pods insecure')"
PIP=$($K get pod -l app=redis-dns -o jsonpath='{.items[0].status.podIP}'); PN=$(echo $PIP | tr . -)
q $PN.default.pod.cluster.local; echo "  (redis-dns 파드 IP = $PIP)"
echo; echo "## 7. DNS 질의가 가는 곳: 10.96.0.10 → CoreDNS 파드 (kube-proxy 규칙)"
$K -n kube-system get pod -l k8s-app=kube-dns -o custom-columns='COREDNS:.metadata.name,IP:.status.podIP,NODE:.spec.nodeName' --no-headers | sed 's/^/  /'
./lab ssh 1 -- sudo sh -c 'iptables-save -t nat 2>/dev/null' > /tmp/e19-nat.txt
grep -- '-A KUBE-SERVICES -d 10.96.0.10/32 -p udp' /tmp/e19-nat.txt | sed 's/-m comment --comment //' | sed 's/^/  /'
SVC=$(grep -- '-A KUBE-SERVICES -d 10.96.0.10/32 -p udp' /tmp/e19-nat.txt | grep -oE 'KUBE-SVC-[A-Z0-9]+')
grep -- "-A $SVC .*KUBE-SEP" /tmp/e19-nat.txt | sed 's/-m comment --comment //' | cut -c1-150 | sed 's/^/  /'; rm -f /tmp/e19-nat.txt
echo; echo "## 8. 정리 (클라이언트만 지우고 redis-dns 는 남김)"
$K delete pod dns-client --now >/dev/null; $K delete ns dns-test --wait=false >/dev/null; echo "$(ts) dns-client, dns-test 네임스페이스 삭제"
