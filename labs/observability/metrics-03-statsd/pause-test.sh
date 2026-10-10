#!/usr/bin/env bash
# 3절: 받는 프로세스를 멈춰 두고(docker pause) 초당 1,000개를 5초 보낸다.
# 커널 수신 버퍼에 몇 개가 들어가고 몇 개가 버려지는지 본다.
set -euo pipefail
cd "$(dirname "$0")"
docker compose up -d --force-recreate statsd kernel >/dev/null 2>&1
sleep 3
docker compose pause statsd >/dev/null
RATE=1000 SECONDS_TO_SEND=5 docker compose --profile send run --rm -e HOLD=0 sender 2>/dev/null | grep '^sent='
# statsd 컨테이너의 네트워크 네임스페이스에서 소켓 상태를 본다(r=큐에 쌓인 바이트, rb=버퍼 한도, d=버린 수)
docker run --rm --network "container:$(docker compose ps -q statsd)" alpine:3.20 \
  sh -c "apk add -q iproute2 >/dev/null 2>&1; ss -uamn sport = :9125" | tail -2
docker compose unpause statsd >/dev/null
sleep 3
./count.sh
