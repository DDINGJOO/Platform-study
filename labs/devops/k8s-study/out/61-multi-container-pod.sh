#!/usr/bin/env bash
# 멀티 컨테이너 파드: c1(8000)·c2(8080) 가 localhost 와 파드 IP 로 서로 닿는가 (Mac 에서 실행)
# 응답에 자기 포트를 적는 작은 웹 서버 둘을 busybox httpd 로 띄운다("containerPort : 포트")
cd "$(dirname "$0")/../.."
K="./lab kubectl"; NS=ch05
echo "# 15 멀티 컨테이너 파드 ($(date '+%F %T %Z'))"
cat <<'Y' | $K apply -n $NS -f - >/dev/null
apiVersion: v1
kind: Pod
metadata: {name: multi-container-pod}
spec:
  containers:
  - name: c1
    image: busybox:1.37
    command: [sh, -c, 'mkdir -p /www && echo "containerPort : 8000" > /www/index.html && exec httpd -f -p 8000 -h /www']
    ports: [{containerPort: 8000}]
  - name: c2
    image: busybox:1.37
    command: [sh, -c, 'mkdir -p /www && echo "containerPort : 8080" > /www/index.html && exec httpd -f -p 8080 -h /www']
    ports: [{containerPort: 8080}]
Y
$K wait pod/multi-container-pod -n $NS --for=condition=Ready --timeout=60s >/dev/null
$K get pod multi-container-pod -n $NS -o wide --no-headers | awk '{print "  "$1, $2, $3, $6, $7}'
IP=$($K get pod multi-container-pod -n $NS -o jsonpath='{.status.podIP}')
run(){ echo; echo "## $1 → $2"; echo "  \$ kubectl exec multi-container-pod -c $1 -- wget -qO- $2"; $K exec multi-container-pod -n $NS -c $1 -- wget -qO- -T 3 $2 2>&1 | sed 's/^/  /'; }
run c1 localhost:8080; run c2 localhost:8000; run c1 $IP:8080; run c2 $IP:8000
echo; echo "## 두 컨테이너가 보는 네트워크 인터페이스와 호스트 이름"
for c in c1 c2; do echo "  [$c] hostname=$($K exec multi-container-pod -n $NS -c $c -- hostname)  eth0=$($K exec multi-container-pod -n $NS -c $c -- ip -4 -o addr show eth0 | awk '{print $4}')"; done
echo; echo "## 파일 시스템은 따로: c1 이 /www 에 쓴 파일을 c2 에서"
$K exec multi-container-pod -n $NS -c c1 -- sh -c 'echo from-c1 > /www/only-c1.txt'
$K exec multi-container-pod -n $NS -c c2 -- ls /www/ 2>&1 | sed 's/^/  c2 의 \/www: /'
$K delete pod multi-container-pod -n $NS --grace-period=1 --wait=false >/dev/null
