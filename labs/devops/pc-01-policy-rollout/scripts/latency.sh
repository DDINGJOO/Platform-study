#!/bin/bash
# 사이드카 한 홉의 값. 하위 실패 0, 정책 v1(재시도 없음)에서 같은 네트워크 안의 k6 로 초당 RATE 건씩 60초.
#   direct  : k6 -> backend           (기준)
#   lib     : k6 -> lib-svc1 -> backend
#   sidecar : k6 -> sc-svc1 -> Envoy(같은 이름공간) -> backend
# 두 바퀴 번갈아 돌리고, 끝에 컨테이너 메모리를 찍는다.
set -e
source "$(dirname "$0")/lib.sh"
RATE=${RATE:-200}
docker compose --profile lib --profile dyn --profile sidecar down --remove-orphans >/dev/null 2>&1 || true
for i in 1 2 3 4 5; do mkdir -p state/envoy/svc$i; cp envoy/rds-v1.yaml state/envoy/svc$i/rds.yaml; done
FAIL_RATE=0 ENVOY_TAG=v1.39.3 docker compose --profile lib --profile sidecar up -d >/dev/null 2>&1
for p in 37001 37011; do wait_up $p; done
# 데우기
for t in http://198.18.37.11:8080/work http://198.18.37.21:8080/work; do
  docker compose run --rm -e TARGET=$t -e NAME=warm -e RATE=100 -e DURATION=20s k6 run -q /scripts/latency.js >/dev/null
done
for round in 1 2; do
  for pair in direct=http://198.18.37.80:8080/data lib=http://198.18.37.11:8080/work sidecar=http://198.18.37.21:8080/work; do
    n=${pair%%=*}; t=${pair#*=}
    docker compose run --rm -e TARGET=$t -e NAME=$n-$round -e RATE=$RATE -e DURATION=60s k6 run -q /scripts/latency.js
  done
done
rm -f out/latency-warm.txt
docker stats --no-stream --format '{{.Name}} {{.MemUsage}}' | grep pc-01 | sort > out/latency-mem.txt
cat out/latency-mem.txt
