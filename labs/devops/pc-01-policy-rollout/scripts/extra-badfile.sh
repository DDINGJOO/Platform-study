#!/bin/bash
# 덧붙인 확인: 실행 중에 읽는 정책 파일이 깨지면? (dyn 방식, svc1 만)
set -e
source "$(dirname "$0")/lib.sh"
docker compose --profile lib --profile dyn --profile sidecar down --remove-orphans >/dev/null 2>&1 || true
mkdir -p state/dyn
for i in 1 2 3 4 5; do printf 'policy.name=v1\npolicy.maxAttempts=1\npolicy.timeoutMs=2000\n' > state/dyn/svc$i.properties; done
docker compose --profile dyn up -d >/dev/null 2>&1; wait_up 37001
echo "## 처음";            curl -s localhost:37001/policy; echo
printf 'policy.name=v3\npolicy.maxAttempts=three\npolicy.timeoutMs=500\n' > state/dyn/.n && mv state/dyn/.n state/dyn/svc1.properties
sleep 3; echo "## maxAttempts=three 로 바꾼 뒤"; curl -s localhost:37001/policy; echo
printf 'policy.name=v0\npolicy.maxAttempts=0\npolicy.timeoutMs=500\n' > state/dyn/.n && mv state/dyn/.n state/dyn/svc1.properties
sleep 3; echo "## maxAttempts=0 으로 바꾼 뒤"; curl -s localhost:37001/policy; echo
printf 'policy.name=v9\npolicy.maxAttempts=50\npolicy.timeoutMs=1\n' > state/dyn/.n && mv state/dyn/.n state/dyn/svc1.properties
sleep 3; echo "## maxAttempts=50, timeoutMs=1 로 바꾼 뒤"; curl -s localhost:37001/policy; echo
for k in 1 2 3; do curl -s -o /dev/null -w '%{http_code} ' -D - localhost:37001/work | tr -d '\r' | grep -iE 'x-attempts' | tr '\n' ' '; echo; done
echo "## 앱 로그"; docker compose logs dyn-svc1 2>&1 | grep -E 'policy (changed|file)' | sed 's/^.*\(WARN\|INFO\)/\1/' | sed 's/ 1 --- \[   policy-watch\] lab.platform.PlatformAutoConfiguration   ://' | cut -c1-260
docker compose --profile dyn down >/dev/null 2>&1
