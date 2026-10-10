#!/usr/bin/env bash
# 한 번의 시험: statsd 를 새로 띄워 카운터를 0 으로 만들고, sender 로 보낸 뒤, 받은 쪽 숫자를 찍는다.
# 조건은 환경변수로: RATE(초당 패킷, 0=최대) SECONDS_TO_SEND STATSD_CPUS READ_BUFFER
set -euo pipefail
cd "$(dirname "$0")"
echo "# RATE=${RATE:-1000} SECONDS_TO_SEND=${SECONDS_TO_SEND:-30} STATSD_CPUS=${STATSD_CPUS:-1} READ_BUFFER=${READ_BUFFER:-기본} UNIX_SOCKET=${UNIX_SOCKET:-없음(UDP)} NONBLOCK=${NONBLOCK:-0}"
docker compose up -d --force-recreate statsd kernel >/dev/null 2>&1
sleep 3
docker compose --profile send run --rm -e HOLD=${HOLD:-0} sender 2>/dev/null | grep '^sent='
sleep 3
./count.sh
