#!/usr/bin/env bash
# 28편 보강: ClusterIP 로 보낸 패킷은 노드 밖으로 어떤 주소를 달고 나가나, 확률 규칙의 실제 분배,
# 연결 단위 선택(keep-alive), readiness 가 규칙에 주는 영향 (Mac 에서 실행, 네임스페이스 w28 만 만들고 지운다)
cd "$(dirname "$0")/../.."   # 실습 저장소 루트 (./lab 이 있는 곳)
K="./lab kubectl"; N="-n w28"; ts(){ date '+%T'; }
echo "# w28 ClusterIP 패킷 관찰 ($(date '+%F %T %Z'), Mac 에서 ./lab 으로 실행, 네임스페이스 w28, 관찰 노드 worker1)"
$K delete ns w28 --ignore-not-found --wait=true >/dev/null 2>&1
$K create ns w28 >/dev/null
cat <<'Y' | $K apply -f - >/dev/null
apiVersion: apps/v1
kind: Deployment
metadata: {name: web, namespace: w28}
spec:
  replicas: 3
  selector: {matchLabels: {app: web}}
  template:
    metadata: {labels: {app: web}}
    spec:
      containers:
      - name: nginx
        image: nginx:1.25.1-alpine
        # 응답 본문 = 파드 이름. /tmp/ready 가 있을 때만 Ready
        command: ["sh","-c","printf %s \"$(hostname)\" > /usr/share/nginx/html/index.html; touch /tmp/ready; exec nginx -g 'daemon off;'"]
        readinessProbe:
          exec: {command: ["cat","/tmp/ready"]}
          periodSeconds: 1
          failureThreshold: 1
---
apiVersion: v1
kind: Service
metadata: {name: web, namespace: w28}
spec:
  selector: {app: web}
  ports: [{port: 80, targetPort: 80}]
Y
$K $N rollout status deploy/web --timeout=180s >/dev/null
VIP=$($K $N get svc web -o jsonpath='{.spec.clusterIP}')
echo; echo "## 0. 만든 것"
echo "\$ kubectl -n w28 get svc,pod -o wide"
$K $N get svc web -o wide --no-headers | awk '{print "svc/"$1, $2, $3, $5}'
$K $N get pod -l app=web -o wide --no-headers | awk '{print "pod/"$1, $2, $3, $6, $7}'
for i in $(seq 1 60); do ./lab ssh 1 -- sudo sh -c "iptables-save -t nat 2>/dev/null" | grep -q -- "-A KUBE-SERVICES -d $VIP/32" && break; sleep 0.5; done
echo "$(ts) worker1 nat 표에 $VIP 규칙이 생긴 것을 확인한 뒤 시작"
PIPS=$($K $N get pod -l app=web -o jsonpath='{.items[*].status.podIP}')
HF=$(for i in $PIPS; do printf 'host %s or ' $i; done | sed 's/ or $//')

echo; echo "## 1. ping: ICMP 에는 규칙이 없어 기본 경로로 나간다 (worker1)"
./lab ssh 1 -- sudo bash -s <<R
echo "worker1\$ ip route get $VIP"; ip route get $VIP | head -1
echo "worker1\$ iptables-save -t nat | grep -- '-A KUBE-SERVICES -d $VIP/32'"
iptables-save -t nat 2>/dev/null | grep -- "-A KUBE-SERVICES -d $VIP/32"
timeout 5 tcpdump -i any -nn -l "icmp and host $VIP" > /tmp/w28-icmp.txt 2>/dev/null &
sleep 1; echo "worker1\$ ping -c 2 -W 1 $VIP"; ping -c 2 -W 1 $VIP | grep -vE '^(PING|---|$)'; wait
echo "같은 동안 tcpdump -i any 'icmp and host $VIP':"; grep . /tmp/w28-icmp.txt | sed 's/^[0-9:.]* //'; rm -f /tmp/w28-icmp.txt
R

echo; echo "## 2. curl: 노드를 떠나는 패킷에는 ClusterIP 가 없다 (worker1)"
./lab ssh 1 -- sudo bash -s <<R
timeout 5 tcpdump -i any -nn -l "host $VIP" > /tmp/w28-vip.txt 2>/dev/null &
timeout 5 tcpdump -i any -nn -l "tcp port 80 and ($HF) and tcp[tcpflags] & tcp-syn != 0" > /tmp/w28-pod.txt 2>/dev/null &
sleep 1; echo "worker1\$ curl -s -w ' %{http_code} remote_ip=%{remote_ip}' http://$VIP/"
curl -s -w ' %{http_code} remote_ip=%{remote_ip}\n' http://$VIP/; wait
echo "tcpdump -i any 'host $VIP' 로 잡힌 패킷: \$(grep -c . /tmp/w28-vip.txt)개"; grep . /tmp/w28-vip.txt | sed 's/^[0-9:.]* /  /' 
echo "tcpdump -i any 'tcp port 80 and (파드 IP 셋) and SYN' 로 잡힌 패킷:"; grep . /tmp/w28-pod.txt | sed 's/^[0-9:.]* //' 
rm -f /tmp/w28-vip.txt /tmp/w28-pod.txt
R

echo; echo "## 3. 확률 규칙과 실제 분배 (worker1, 연결마다 curl 새로 실행)"
./lab ssh 1 -- sudo bash -s <<R
SVC=\$(iptables-save -t nat 2>/dev/null | grep -- "-A KUBE-SERVICES -d $VIP/32" | grep -oE 'KUBE-SVC-[A-Z0-9]+')
iptables-save -t nat 2>/dev/null | grep -- "-A \$SVC .*KUBE-SEP" | sed 's/-m comment --comment //'
echo "worker1\$ for i in \\\$(seq 300); do curl -s http://$VIP/; echo; done | sort | uniq -c"
for i in \$(seq 300); do curl -s --max-time 2 http://$VIP/; echo; done | sort | uniq -c
R

echo; echo "## 4. 연결 하나로 여러 번 요청하면 (curl 한 번에 URL 30개 = keep-alive)"
./lab ssh 1 -- bash -s <<R
U=\$(for i in \$(seq 30); do printf 'http://%s/ ' $VIP; done)
for run in 1 2 3; do
  curl -s -w ' %{num_connects}\n' \$U | awk -v r=\$run '{c[\$1]++; n+=\$2} END{printf "%d회차: 요청 30번, 새 연결 %d개, 응답한 파드:", r, n; for(k in c) printf " %s x%d", k, c[k]; print ""}'
done
R

echo; echo "## 5. readiness 가 깨지면 규칙에서 빠진다"
P=$($K $N get pod -l app=web -o jsonpath='{.items[0].metadata.name}')
PIP=$($K $N get pod $P -o jsonpath='{.status.podIP}')
cnt(){ ./lab ssh 1 -- sudo sh -c "iptables-save -t nat 2>/dev/null" | awk -v v="$VIP/32" '$0 ~ "-A KUBE-SERVICES -d "v {match($0,/KUBE-SVC-[A-Z0-9]+/); s=substr($0,RSTART,RLENGTH)} {l[NR]=$0} END{n=0; for(i in l) if (l[i] ~ "-A "s" .*KUBE-SEP") n++; print n}'; }
eps(){ $K $N get endpointslice -l kubernetes.io/service-name=web -o jsonpath='{range .items[*].endpoints[*]}{.addresses[0]}(ready={.conditions.ready}) {end}'; }
echo "$(ts) 대상 파드 $P ($PIP). worker1 SEP 규칙 $(cnt)개, EndpointSlice: $(eps)"
$K $N exec $P -- rm /tmp/ready; T0=$(date +%s.%N); echo "$(ts) kubectl -n w28 exec $P -- rm /tmp/ready"
for i in $(seq 1 60); do c=$(cnt); [ "$c" = 2 ] && break; sleep 0.3; done
echo "$(ts) worker1 SEP 규칙 ${c}개 (rm 뒤 $(python3 -c "import time;print(round(time.time()-$T0,1))")초)"
echo "$(ts) EndpointSlice: $(eps)"
echo "$(ts) 파드: $($K $N get pod $P --no-headers | awk '{print $1, "READY", $2, $3}')"
D=$(./lab ssh 1 -- bash -s <<R
for i in \$(seq 60); do curl -s --max-time 2 http://$VIP/; echo; done | sort | uniq -c | awk '{printf "%s x%s  ", \$2, \$1}'
R
)
echo "$(ts) worker1 에서 60번 curl: $D"
$K $N exec $P -- touch /tmp/ready; T0=$(date +%s.%N); echo "$(ts) kubectl -n w28 exec $P -- touch /tmp/ready"
for i in $(seq 1 60); do c=$(cnt); [ "$c" = 3 ] && break; sleep 0.3; done
echo "$(ts) worker1 SEP 규칙 ${c}개 (touch 뒤 $(python3 -c "import time;print(round(time.time()-$T0,1))")초), EndpointSlice: $(eps)"

echo; echo "## 6. kube-proxy 가 스스로 알려 주는 것 (worker1, 127.0.0.1:10249/metrics, :10256/healthz)"
./lab ssh 1 -- bash -s <<'R'
curl -s 127.0.0.1:10249/metrics | grep -E '^kubeproxy_sync_proxy_rules_(duration_seconds_(sum|count)|last_timestamp_seconds|endpoint_changes_total|service_changes_total|iptables_total\{table="nat")'
echo "healthz: $(curl -s 127.0.0.1:10256/healthz | cut -c1-160)"
R

echo; echo "## 7. 정리"
$K delete ns w28 --wait=false >/dev/null; echo "$(ts) w28 네임스페이스 삭제"
