#!/usr/bin/env bash
# 29편 보강: 파드의 DNS 설정을 누가 넣나, search·ndots 가 실제로 만드는 질의, busybox nslookup 의 함정,
# 환경 변수가 정해지는 시점, pods insecure (Mac 에서 실행, 네임스페이스 w29 만 만들고 지운다)
cd "$(dirname "$0")/../.."   # 실습 저장소 루트 (./lab 이 있는 곳)
K="./lab kubectl"; N="-n w29"; ts(){ date '+%T'; }
# 노드 resolv.conf 의 공유기 검색 도메인은 출력에서 <router-domain> 으로 가린다 (맨 아래 main | sed)
RD=$(./lab ssh 1 -- bash -s <<'R' | sed 's/\./\\./g'
awk '/^search/{print $2}' /run/systemd/resolve/resolv.conf
R
)
main(){
echo "# w29 DNS search·ndots 관찰 ($(date '+%F %T %Z'), Mac 에서 ./lab 으로 실행, 네임스페이스 w29)"
$K delete ns w29 --ignore-not-found --wait=true >/dev/null 2>&1
$K create ns w29 >/dev/null

echo; echo "## 1. 같은 명령으로 Service 와 클라이언트를 만든다 (w29)"
$K $N create deployment redis-dns --image=redis --replicas=1 >/dev/null
$K $N expose deployment redis-dns --name=redis-dns-svc --port=6379 --target-port=6379 >/dev/null
$K $N rollout status deploy/redis-dns --timeout=180s >/dev/null
$K $N run dns-client --image=busybox:1.36.1 --restart=Never -- sleep 900 >/dev/null
$K $N wait --for=condition=Ready pod/dns-client --timeout=120s >/dev/null
SIP=$($K $N get svc redis-dns-svc -o jsonpath='{.spec.clusterIP}')
CN=$($K $N get pod dns-client -o jsonpath='{.spec.nodeName}'); CIP=$($K $N get pod dns-client -o jsonpath='{.status.podIP}')
echo "svc/redis-dns-svc ClusterIP $SIP, pod/dns-client $CIP ($CN)"
echo "dns-client 의 libc: $($K $N exec dns-client -- ls /lib | grep -E '^libc\.so' | head -1) (busybox:1.36.1)"

echo; echo "## 2. resolv.conf 를 만드는 것은 그 노드의 kubelet"
echo "dns-client\$ cat /etc/resolv.conf"; $K $N exec dns-client -- cat /etc/resolv.conf | grep -E 'search|nameserver|options' | sed 's/^/  /'
echo "$CN\$ grep -A1 -E 'clusterDNS|clusterDomain|resolvConf' /var/lib/kubelet/config.yaml"
./lab ssh ${CN#k8s-worker} -- sudo bash -s <<'R' | grep -v '^--' | sed 's/^/  /'
grep -A1 -E 'clusterDNS|clusterDomain|resolvConf' /var/lib/kubelet/config.yaml
R
echo "$CN\$ grep search /run/systemd/resolve/resolv.conf (kubelet resolvConf, 노드의 검색 도메인)"
./lab ssh ${CN#k8s-worker} -- grep search /run/systemd/resolve/resolv.conf | sed 's/^/  /'

echo; echo "## 3. 이름 풀이: glibc 리졸버(ping 첫 줄) vs busybox nslookup"
q(){ r=$($K $N exec dns-client -- ping -c1 -W1 $1 2>&1 | head -1 | grep -oE '\([0-9.]+\)' | tr -d '()'); n=$($K $N exec dns-client -- nslookup $1 2>&1 | awk '/^Name:/{f=1} f&&/^Address: /{print $2; exit} /NXDOMAIN/{x=1} END{if(!f&&x) print "NXDOMAIN"}' | head -1); printf "  %-42s ping→ %-15s nslookup→ %s\n" "$1" "${r:-못 찾음}" "${n:-없음}"; }
for n in redis-dns-svc redis-dns-svc.w29 redis-dns-svc.w29.svc redis-dns-svc.w29.svc.cluster.local kubernetes kubernetes.default kubernetes.default.svc.cluster.local; do q $n; done
echo "  (redis-dns-svc ClusterIP $SIP, kubernetes ClusterIP $($K get svc kubernetes -o jsonpath='{.spec.clusterIP}'))"
echo "dns-client\$ printf 'PING\\r\\n' | nc -w 2 redis-dns-svc 6379 → $($K $N exec dns-client -- sh -c "printf 'PING\r\n' | nc -w 2 redis-dns-svc 6379" | tr -d '\r')"

echo; echo "## 4. ndots:5 가 만드는 질의 ($CN 에서 dns-client 의 veth 를 tcpdump, udp 53)"
for NAME in www.kubernetes.io www.kubernetes.io. redis-dns-svc redis-dns-svc.w29.svc.cluster.local; do
  echo "dns-client\$ ping -c1 -W1 $NAME"
  ./lab ssh ${CN#k8s-worker} -- sudo bash -s <<R
IF=\$(ip route get $CIP | grep -oE 'dev [^ ]+' | awk '{print \$2}')
timeout 5 tcpdump -i \$IF -nn -l "udp port 53 and src host $CIP" > /tmp/w29-dns.txt 2>/dev/null &
sleep 1
CID=\$(crictl ps --name dns-client -q | head -1)
crictl exec \$CID ping -c1 -W1 $NAME >/dev/null 2>&1
wait
echo "  보낸 질의 \$(grep -c . /tmp/w29-dns.txt)개:"; grep . /tmp/w29-dns.txt | grep -oE '(A|AAAA)\? [^ ]+' | sed 's/^/    /'
rm -f /tmp/w29-dns.txt
R
done

echo; echo "## 5. 환경 변수는 컨테이너가 시작하는 순간의 Service 목록으로 정해진다"
$K $N run envcheck --image=busybox:1.36.1 --restart=Always --env=TZ=KST-9 -- sh -c 'echo "$(date +%T) 컨테이너 시작, LATE_SVC_SERVICE_HOST=${LATE_SVC_SERVICE_HOST:-없음}"; sleep 15' >/dev/null
$K $N wait --for=condition=Ready pod/envcheck --timeout=120s >/dev/null; sleep 3
$K $N create service clusterip late-svc --tcp=80:80 >/dev/null; echo "$(ts) Service late-svc 생성 (ClusterIP $($K $N get svc late-svc -o jsonpath='{.spec.clusterIP}'))"
for i in $(seq 1 60); do [ "$($K $N get pod envcheck -o jsonpath='{.status.containerStatuses[0].restartCount}')" -ge 1 ] && [ "$($K $N get pod envcheck -o jsonpath='{.status.containerStatuses[0].ready}')" = true ] && break; sleep 1; done
echo "같은 파드 envcheck, 첫 컨테이너 로그:   $($K $N logs envcheck --previous)"
echo "같은 파드 envcheck, 재시작한 컨테이너: $($K $N logs envcheck)"
echo "dns-client(late-svc 전에 시작) 의 *_SERVICE_HOST: $($K $N exec dns-client -- env | grep -oE '^[A-Z0-9_]+_SERVICE_HOST' | sort | paste -sd' ' -)"
echo "  (default 네임스페이스의 Service: $($K -n default get svc --no-headers | awk '{print $1}' | paste -sd' ' -))"

echo; echo "## 6. pods insecure: 파드가 없어도 IP 모양 이름이면 A 레코드를 돌려준다"
FAKE=10.244.0.99
echo "  클러스터에 IP 가 $FAKE 인 파드: $($K get pod -A -o jsonpath='{range .items[*]}{.status.podIP}{"\n"}{end}' | grep -cx "$FAKE")개"
for n in ${CIP//./-}.w29.pod.cluster.local ${FAKE//./-}.w29.pod.cluster.local; do
  echo "  nslookup $n → $($K $N exec dns-client -- nslookup $n 2>&1 | awk '/^Name:/{f=1} f&&/^Address: /{print $2; exit}')"
done

echo; echo "## 7. Metrics Server 는 없다"
echo "kubectl get apiservice | grep metrics: $($K get apiservice --no-headers | grep -c metrics)줄"
echo "kubectl top node: $($K top node 2>&1 | head -1)"

echo; echo "## 8. 정리"
$K delete ns w29 --wait=false >/dev/null; echo "$(ts) w29 네임스페이스 삭제"
}
main 2>&1 | sed "s/${RD:-__none__}/<router-domain>/g"
