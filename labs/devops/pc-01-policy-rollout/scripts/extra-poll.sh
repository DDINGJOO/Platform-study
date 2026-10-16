#!/bin/bash
# 덧붙인 확인: 호스트에서 RDS 파일을 바꿔치우면 Envoy 가 알아채나? (기본 감시 vs poll_interval)
set -e
source "$(dirname "$0")/lib.sh"
T=state/poll; rm -rf $T; mkdir -p $T/watch $T/poll
cp envoy/rds-v1.yaml $T/watch/rds.yaml; cp envoy/rds-v1.yaml $T/poll/rds.yaml
sed 's#path_config_source: { path: /etc/envoy/dyn/rds.yaml }#path_config_source: { path: /etc/envoy/dyn/rds.yaml, poll_interval: 1s }#' envoy/envoy.yaml > $T/envoy-poll.yaml
grep -c poll_interval $T/envoy-poll.yaml
docker run -d --rm --name pc01-watch -p 37031:15000 -v "$LAB/envoy/envoy.yaml:/etc/envoy/envoy.yaml:ro" -v "$LAB/$T/watch:/etc/envoy/dyn" envoyproxy/envoy:v1.39.3 >/dev/null
docker run -d --rm --name pc01-poll  -p 37032:15000 -v "$LAB/$T/envoy-poll.yaml:/etc/envoy/envoy.yaml:ro" -v "$LAB/$T/poll:/etc/envoy/dyn" envoyproxy/envoy:v1.39.3 >/dev/null
sleep 3
v() { curl -s "localhost:$1/stats?filter=rds.backend_route.version_text" | awk '{print $2}'; }
echo "처음: watch=$(v 37031) poll=$(v 37032)"
for d in watch poll; do cp envoy/rds-v2.yaml $T/$d/.new && mv $T/$d/.new $T/$d/rds.yaml; done
prev=0
for s in 1 3 10 30; do sleep $([ $s = 1 ] && echo 1 || echo $((s - prev))); prev=$s; echo "호스트에서 mv 후 ${s}초: watch=$(v 37031) poll=$(v 37032)"; done
docker exec pc01-watch sh -c 'cp /etc/envoy/dyn/rds.yaml /etc/envoy/dyn/.n && mv /etc/envoy/dyn/.n /etc/envoy/dyn/rds.yaml'
sleep 1; echo "컨테이너 안에서 mv 후 1초: watch=$(v 37031)"
docker logs pc01-poll 2>&1 | grep -iE 'poll|unknown field|error' | head -3 || true
docker rm -f pc01-watch pc01-poll >/dev/null
