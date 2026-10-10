#!/usr/bin/env bash
# 같은 이미지를 에이전트 켜고/끄고 세 번씩 띄워 기동 시간을 잰다.
# "process running for" 는 JVM 시작부터, "Started ... in" 은 스프링 컨텍스트 기동부터 잰 값이다.
set -u
IMAGE=${IMAGE:-obs-lab/shop:dev}
for mode in off on; do
  for i in 1 2 3; do
    opts=""; [ "$mode" = on ] && opts="-javaagent:/otel/opentelemetry-javaagent.jar"
    name="startup-$mode-$i"
    docker run -d --rm --name "$name" -e JAVA_TOOL_OPTIONS="$opts" \
      -e OTEL_TRACES_EXPORTER=none -e OTEL_METRICS_EXPORTER=none -e OTEL_LOGS_EXPORTER=none \
      -e SPRING_PROFILES_ACTIVE=inventory "$IMAGE" >/dev/null
    line=""
    for _ in $(seq 1 60); do
      line=$(docker logs "$name" 2>&1 | grep -o "Started ShopApplication in .*" || true)
      [ -n "$line" ] && break
      sleep 1
    done
    echo "agent=$mode run=$i  $line"
    docker kill "$name" >/dev/null 2>&1
  done
done
