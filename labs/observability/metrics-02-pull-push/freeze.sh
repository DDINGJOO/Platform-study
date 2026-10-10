#!/usr/bin/env bash
# 시나리오 1: 앱 프로세스가 멈춘다(파드는 Running 그대로). kind 노드 안에서 두 앱의 java 에 SIGSTOP 을 보내고,
# HOLD 초(기본 400) 뒤에 SIGCONT 로 되살린다. 시각을 찍어 둔다.
set -euo pipefail
NODE=obs-lab-metrics-02-control-plane
echo "stop $(date +%s) $(date +%T)"
docker exec "$NODE" pkill -STOP -f /app/pp.jar
sleep "${HOLD:-400}"
docker exec "$NODE" pkill -CONT -f /app/pp.jar
echo "cont $(date +%s) $(date +%T)"
