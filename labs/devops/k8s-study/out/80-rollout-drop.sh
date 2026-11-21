#!/usr/bin/env bash
# 롤링 업데이트 중 요청이 끊기나: keep-alive 클라이언트 4개 + 매번 새 연결 클라이언트 1개로 Service 에 부하를 주며 rollout restart
# 비교: (1) nginx 기본 종료(SIGQUIT, 하던 요청 마무리) (2) 신호를 받자마자 빠른 종료(nginx -s stop) (3) 빠른 종료 + preStop sleep 5
# 그리고 headless Service 에서 DNS 응답(파드 IP)을 한 번만 받아 쓰는 클라이언트 (Mac 에서 실행)
cd "$(dirname "$0")/../.."
K="./lab kubectl"; NS=ch05; DUR=40
echo "# 32 롤링 업데이트와 요청 끊김 ($(date '+%F %T %Z')), replicas 3, maxSurge 25%·maxUnavailable 25%(기본)"
$K run client -n $NS --image=curlimages/curl:8.11.1 --command -- sleep 3600 >/dev/null 2>&1
$K wait pod/client -n $NS --for=condition=Ready --timeout=120s >/dev/null
deploy(){ # $1 이름 $2 컨테이너 추가 블록 $3 service 추가 spec
cat <<Y | $K apply -n $NS -f - >/dev/null
apiVersion: apps/v1
kind: Deployment
metadata: {name: $1}
spec:
  replicas: 3
  selector: {matchLabels: {app: $1}}
  template:
    metadata: {labels: {app: $1}}
    spec:
      containers:
      - name: web
        image: nginx:1.27-alpine
$2
---
apiVersion: v1
kind: Service
metadata: {name: $1}
spec: {selector: {app: $1}, ports: [{port: 80}]$3}
Y
$K rollout status deploy/$1 -n $NS --timeout=120s >/dev/null
}
FAST='        command: ["sh", "-c", "nginx -g \"daemon off;\" & p=$!; trap \"nginx -s stop\" TERM QUIT; wait $p; wait $p"]'
run(){ # $1 이름
  local S=$1.$NS.svc.cluster.local
  $K exec client -n $NS -- sh -c "
    ka(){ end=\$((\$(date +%s)+$DUR)); while [ \$(date +%s) -lt \$end ]; do curl -s -o /dev/null --max-time 2 -w 'ka%{http_code}\n' \$(for i in 1 2 3 4 5 6 7 8 9 10; do printf 'http://$S/ '; done); done; }
    nc(){ end=\$((\$(date +%s)+$DUR)); while [ \$(date +%s) -lt \$end ]; do curl -s -o /dev/null --max-time 2 -w 'new%{http_code}\n' http://$S/; sleep 0.02; done; }
    ka & ka & ka & ka & nc & wait" > /tmp/ch05-32-$1.log 2>&1 &
  local CP=$!
  sleep 4; $K rollout restart deploy/$1 -n $NS >/dev/null; s=$(date +%s)
  $K rollout status deploy/$1 -n $NS --timeout=120s >/dev/null; echo "  rollout 완료 $(( $(date +%s)-s ))초"
  wait $CP
  for t in ka new; do tot=$(grep -c "^$t" /tmp/ch05-32-$1.log); ok=$(grep -c "^${t}200$" /tmp/ch05-32-$1.log); echo "  $( [ $t = ka ] && echo 'keep-alive(4개)' || echo '새 연결(1개)  ') 요청 $tot, 실패 $((tot-ok)) $(grep "^$t" /tmp/ch05-32-$1.log | grep -v "^${t}200$" | sort | uniq -c | tr '\n' ' ')"; done
  rm -f /tmp/ch05-32-$1.log
  $K delete deploy,svc $1 -n $NS >/dev/null
}
echo; echo "## (1) graceful: nginx 기본 종료, preStop 없음"; deploy drop-graceful ""; run drop-graceful
echo; echo "## (2) fast-exit: 신호 받자마자 빠른 종료, preStop 없음"; deploy drop-fast "$FAST"; run drop-fast
echo; echo "## (3) fast-exit + preStop sleep 5"; deploy drop-prestop "$FAST
        lifecycle: {preStop: {sleep: {seconds: 5}}}"; run drop-prestop

echo; echo "## (4) headless Service: DNS 가 파드 IP 를 준다, 한 번 받은 IP 를 계속 쓰면"
deploy drop-headless "" ", clusterIP: None"
H=drop-headless.$NS.svc.cluster.local
echo "  DNS 응답(TTL, 마스터에서 dig @CoreDNS):"; limactl shell k8s-master -- dig @10.96.0.10 $H A +noall +answer | sed 's/^/    /'
IP=$($K exec client -n $NS -- nslookup $H 2>/dev/null | awk '/^Address/ && $2 !~ /:53$/ {print $2}' | head -1)
echo "  클라이언트가 처음 받은 파드 IP: $IP"
$K exec client -n $NS -- sh -c "end=\$((\$(date +%s)+$DUR)); while [ \$(date +%s) -lt \$end ]; do curl -s -o /dev/null --max-time 1 -w 'cached%{http_code}\n' http://$IP/; curl -s -o /dev/null --max-time 1 -w 'fresh%{http_code}\n' http://$H/; sleep 0.1; done" > /tmp/ch05-32-h.log 2>&1 &
CP=$!; sleep 4; $K rollout restart deploy/drop-headless -n $NS >/dev/null; $K rollout status deploy/drop-headless -n $NS --timeout=120s >/dev/null; wait $CP
for t in cached fresh; do tot=$(grep -c "^$t" /tmp/ch05-32-h.log); ok=$(grep -c "^${t}200$" /tmp/ch05-32-h.log); echo "  $t: 요청 $tot, 실패 $((tot-ok))"; done
echo "  rollout 뒤 DNS 응답:"; limactl shell k8s-master -- dig @10.96.0.10 $H A +noall +answer | sed 's/^/    /'
rm -f /tmp/ch05-32-h.log; $K delete deploy,svc drop-headless -n $NS >/dev/null; $K delete pod client -n $NS --grace-period=1 --wait=false >/dev/null
