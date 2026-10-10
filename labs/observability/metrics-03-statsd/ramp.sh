#!/usr/bin/env bash
# 4절: statsd 의 CPU 를 STATSD_CPUS(기본 0.25)로 묶고, 보내는 속도를 단계적으로 올린다.
# sender 를 `up` 으로 띄워야 Prometheus 가 sender:8000 을 이름으로 찾아 긁는다(`run` 컨테이너는 서비스 이름으로 안 잡힌다).
set -euo pipefail
cd "$(dirname "$0")"
export STATSD_CPUS=${STATSD_CPUS:-0.25}
export STEPS=${STEPS:-20000:30,50000:30,100000:30,200000:30,0:30}
docker compose up -d --force-recreate statsd kernel >/dev/null 2>&1
sleep 5
echo "# start $(date +%T) STATSD_CPUS=$STATSD_CPUS STEPS=$STEPS"
docker compose --profile send up --force-recreate --abort-on-container-exit sender 2>/dev/null | grep -E "step|sent=" | sed 's/^sender-1 *| //'
echo "# end $(date +%T)"
./count.sh
docker compose --profile send rm -fsv sender >/dev/null 2>&1 || true   # up 으로 띄운 sender 컨테이너를 남기지 않는다
