#!/usr/bin/env bash
# kubectl get pod 의 "API 호출"은 어디서 보이나: strace(시스템 콜) vs kubectl -v(HTTP 요청) (Mac 에서 실행, 마스터에서 돈다)
cd "$(dirname "$0")/../.."
echo "# 16 strace vs kubectl -v ($(date '+%F %T %Z')), k8s-master 에서 실행"
limactl shell k8s-master -- bash -s <<'IN'
echo; echo "## 1. strace -f kubectl get pod -n ch05 : 시스템 콜 개수 상위"
strace -f -c -o /tmp/st.sum kubectl get pod -n ch05 >/dev/null 2>&1; sed -n '1,4p;/total/p' /tmp/st.sum | sed 's/^/  /'
grep -E '^ +[0-9.]+ ' /tmp/st.sum | sort -k4 -nr | head -6 | awk '{print "  "$NF" "$4"회"}'
echo; echo "## 2. 네트워크 관련 콜만: API 서버에 붙는 connect, 오가는 바이트"
strace -f -e trace=connect,write,read -s 60 -o /tmp/st.net kubectl get pod -n ch05 >/dev/null 2>&1
grep -E 'connect\(.*(6443|sin_port)' /tmp/st.net | grep -v ENOENT | head -3 | sed -E 's/^[0-9]+ +/  /' | cut -c1-150
echo "  TLS 라 write/read 내용은 암호문. 평문 GET 이 보이는가: $(grep -c 'GET /api' /tmp/st.net)줄"
echo; echo "## 3. kubectl -v=6 : 실제 REST 요청"
kubectl get pod -n ch05 -v=6 2>&1 | grep -oE 'verb="[A-Z]+" url="[^"]+" status="[^"]+"' | sed 's/^/  /'
echo; echo "## 4. kubectl -v=8 : 요청·응답 헤더와 본문 일부"
kubectl get pod -n ch05 -v=8 2>&1 | grep -E 'Request Headers|Accept|User-Agent|Response Body' | head -5 | cut -c1-170 | sed 's/^/  /'
rm -f /tmp/st.sum /tmp/st.net
IN
