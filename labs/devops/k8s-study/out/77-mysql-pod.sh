#!/usr/bin/env bash
# MySQL 파드: 필수 환경 변수 없이 띄우면 어떻게 끝나나, 넣으면 (Mac 에서 실행). 원본 스크립트의 A 절(mysql:5.7)은 이 글과 무관해 뺐다
cd "$(dirname "$0")/../.."
K="./lab kubectl"; NS=ch05
mk(){ cat <<Y
apiVersion: v1
kind: Pod
metadata: {name: $1, labels: {type: $1}}
spec:
  containers:
  - name: mysql-container
    image: $2
    ports: [{containerPort: 3306}]
$3
Y
}
watchp(){ local last="" t0=$(date +%s); for i in $(seq 1 $2); do cur=$($K get pod $1 -n $NS --no-headers 2>/dev/null | awk '{print $2, $3, "restarts="$4}'); [ "$cur" != "$last" ] && { printf '  +%3ss  %s\n' $(( $(date +%s)-t0 )) "$cur"; last=$cur; }; sleep 2; done; }
echo "# 23 MySQL 파드 ($(date '+%F %T %Z')), 노드 arch: $($K get nodes -o jsonpath='{.items[*].status.nodeInfo.architecture}' | tr ' ' '\n' | sort -u | paste -sd, -)"
echo; echo "## B. mysql:8.4, 환경 변수 없음"
mk mysql84-pod mysql:8.4 "" | $K apply -n $NS -f - >/dev/null; watchp mysql84-pod 45
echo "  로그(마지막 실행 또는 직전 실행):"
{ $K logs mysql84-pod -n $NS 2>/dev/null || $K logs mysql84-pod -n $NS --previous 2>&1; } | tail -5 | cut -c1-200 | sed 's/^/    /'
$K delete pod mysql84-pod -n $NS --wait=false >/dev/null
echo; echo "## C. mysql:8.4, MYSQL_ROOT_PASSWORD 를 env 로 넣음(실습용 값)"
mk mysql84-env mysql:8.4 "    env: [{name: MYSQL_ROOT_PASSWORD, value: lab-only-pass}]" | $K apply -n $NS -f - >/dev/null; watchp mysql84-env 30
echo "  (Running 이어도 첫 기동은 DB 초기화 중이다. 로그에 최종 'ready for connections' 가 나올 때까지 기다린다)"
t0=$(date +%s); until [ "$($K logs mysql84-env -n $NS 2>/dev/null | grep -c 'ready for connections.*port: 3306')" -ge 1 ] || [ $(( $(date +%s)-t0 )) -gt 120 ]; do sleep 2; done
echo "  준비 로그까지 +$(( $(date +%s)-t0 ))초 더 걸림: $($K logs mysql84-env -n $NS 2>/dev/null | grep 'ready for connections.*port: 3306' | tail -1 | cut -c1-120)"
$K exec mysql84-env -n $NS -- mysql -uroot -plab-only-pass -e 'select version();' 2>&1 | grep -v Warning | sed 's/^/  /'
$K delete pod mysql84-env -n $NS --wait=false >/dev/null
