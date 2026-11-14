#!/usr/bin/env bash
# kube-proxy 는 무엇을 하나: Service ClusterIP 를 iptables 규칙으로 바꿔 각 노드 커널에 깐다 (Mac 에서 실행)
cd "$(dirname "$0")/../.."   # 실습 저장소 루트 (./lab 이 있는 곳)
K="./lab kubectl"; ts(){ date '+%T'; }
VIP=$($K get svc myweb -o jsonpath='{.spec.clusterIP}')
echo "# E15 kube-proxy ($(date '+%F %T %Z')), Service myweb ClusterIP $VIP"
echo; echo "## 1. 모드"
echo "configmap kube-proxy mode: $($K -n kube-system get cm kube-proxy -o jsonpath='{.data.config\.conf}' | awk '/^mode:/{print $2}')"
echo "worker1 kube-proxy /proxyMode: $(./lab ssh 1 -- curl -s 127.0.0.1:10249/proxyMode)"
echo; echo "## 2. ClusterIP 는 어느 인터페이스에도 없다"
echo "worker1 ip addr 에서 $VIP: $(./lab ssh 1 -- ip -br addr | grep -c $VIP)개"
echo "worker1 → $VIP ping: $(./lab ssh 1 -- ping -c1 -W1 $VIP 2>&1 | grep -oE '[0-9]+% packet loss')"
echo "worker1 → $VIP:80 curl: $(./lab ssh 1 -- curl -s -o /dev/null -w '%{http_code}' --max-time 2 http://$VIP/)"
echo; echo "## 3. 그 대신 worker1 iptables nat 표에 있는 규칙 (iptables-save -t nat, myweb 만)"
./lab ssh 1 -- sudo sh -c 'iptables-save -t nat 2>/dev/null' > /tmp/e15-nat.txt   # 'iptables-legacy tables present' 경고(stderr)는 버림
SVC=$(grep -- "-d $VIP/32" /tmp/e15-nat.txt | grep -oE 'KUBE-SVC-[A-Z0-9]+' | head -1)
grep -- "-A KUBE-SERVICES -d $VIP/32" /tmp/e15-nat.txt
grep -- "-A $SVC " /tmp/e15-nat.txt
SEP=$(grep -- "-A $SVC " /tmp/e15-nat.txt | grep -oE 'KUBE-SEP-[A-Z0-9]+' | head -1)
grep -- "-A $SEP " /tmp/e15-nat.txt
echo "worker1 nat 표의 KUBE 규칙 수: $(grep -c KUBE /tmp/e15-nat.txt)"
echo; echo "## 4. 엔드포인트가 바뀌면 규칙이 바뀐다: myweb 5 → 3 → 5"
cnt(){ ./lab ssh 1 -- sudo sh -c 'iptables-save -t nat 2>/dev/null' | grep -c -- "-A $SVC .*KUBE-SEP"; }
eps(){ ./lab ssh 1 -- sudo sh -c 'iptables-save -t nat 2>/dev/null' | grep -- "-A $SVC .*KUBE-SEP" | grep -oE '> [0-9.]+' | tr -d '> ' | paste -sd' ' -; }
pods(){ $K get pod -l app=myweb --no-headers -o custom-columns=N:.metadata.name,IP:.status.podIP,R:.status.containerStatuses[0].ready | awk '{printf "%s(%s,%s) ", substr($1,length($1)-4), $2, $3}'; }
echo "$(ts) worker1 의 $SVC → SEP 규칙 $(cnt)개: $(eps)"
$K scale deploy myweb --replicas=3 >/dev/null; T0=$(date +%s.%N); echo "$(ts) kubectl scale --replicas=3"
for i in $(seq 1 40); do c=$(cnt); [ "$c" = 3 ] && break; sleep 0.3; done
echo "$(ts) SEP 규칙 ${c}개 (scale 뒤 $(python3 -c "import time;print(round(time.time()-$T0,1))")초) 규칙의 엔드포인트: $(eps)"
$K scale deploy myweb --replicas=5 >/dev/null; T0=$(date +%s.%N); echo "$(ts) kubectl scale --replicas=5"
for i in $(seq 1 60); do c=$(cnt); [ "$c" = 5 ] && break; sleep 0.5; done
echo "$(ts) SEP 규칙 ${c}개 (scale 뒤 $(python3 -c "import time;print(round(time.time()-$T0,1))")초) 규칙의 엔드포인트: $(eps)"
echo "$(ts) 파드(이름끝,IP,ready): $(pods)"
echo; echo "## 5. kube-proxy 는 트래픽 길 위에 없다"
KP=$($K -n kube-system get pod -l k8s-app=kube-proxy --field-selector spec.nodeName=k8s-worker1 -o jsonpath='{.items[0].metadata.name}')
echo "worker1 kube-proxy 의 TCP 연결: $(./lab ssh 1 -- sudo ss -tnp | grep kube-proxy | awk '{print $5}' | sort | uniq -c | xargs)"
echo "$(ts) mac\$ kubectl -n kube-system delete pod $KP  (그동안 worker1 에서 ClusterIP 로 0.5초마다 curl)"
./lab ssh 1 -- sh -c "for i in \$(seq 1 24); do curl -s -o /dev/null -w '%{http_code} ' --max-time 1 http://$VIP/; sleep 0.5; done; echo" > /tmp/e15-curl.txt &
sleep 1; $K -n kube-system delete pod $KP >/dev/null; echo "$(ts) 삭제 완료"; wait
echo "curl 결과 24번: $(cat /tmp/e15-curl.txt)"
sleep 3; echo "$(ts) 새 kube-proxy: $($K -n kube-system get pod -l k8s-app=kube-proxy --field-selector spec.nodeName=k8s-worker1 --no-headers | awk '{print $1, $2, $3, $5}')"
rm -f /tmp/e15-nat.txt /tmp/e15-curl.txt
