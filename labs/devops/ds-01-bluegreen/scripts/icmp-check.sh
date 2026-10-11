#!/usr/bin/env bash
# 엔드포인트가 0개인 NodePort 로 동시에 연결 20개를 열어, 즉시 거부와 타임아웃이 몇 개씩 나오는지 센다.
# 실행 위치: labs/devops/ds-01-bluegreen. 끝나면 web 을 원래 개수(4)로 되돌린다
set -euo pipefail
cd "$(dirname "$0")/.."
K="kubectl --context kind-ds-01 -n lab"
echo "# 노드의 ICMP 속도 제한 설정"
docker exec ds-01-control-plane sysctl net.ipv4.icmp_ratelimit net.ipv4.icmp_ratemask
$K scale deploy/web --replicas=0 >/dev/null
until [ -z "$($K get pods -l app=web -o name)" ]; do sleep 1; done
sleep 2
echo "# kube-proxy 가 넣은 규칙"
docker exec ds-01-control-plane sh -c 'iptables-save | grep "lab/web has no endpoints" | grep 30080'
for round in 1 2 3; do
  echo "# 동시 연결 20개, ${round}회 (0.5초 안에 끝나면 즉시 거부, 아니면 2초 타임아웃)"
  docker run --rm --network kind curlimages/curl:8.11.1 sh -c \
    'for i in $(seq 1 20); do curl -4 -s -o /dev/null -w "%{time_total}\n" -m 2 http://ds-01-control-plane:30080/ & done; wait; true' \
    | awk '{print ($1<0.5?"즉시 거부":"타임아웃")}' | sort | uniq -c
  sleep 3
done
$K scale deploy/web --replicas=4 >/dev/null
