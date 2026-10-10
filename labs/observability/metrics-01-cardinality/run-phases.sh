#!/usr/bin/env bash
# 2~4절: user_id 태그를 붙이는 자리를 none → counter → timer → histogram → none 으로 바꿔 가며 잰다.
# 단계마다 앱을 다시 띄우고, 사용자 USERS 명(기본 1000)이 한 번씩 주문한 뒤 30초 기다렸다가 measure.py 로 찍는다.
set -euo pipefail
cd "$(dirname "$0")"
USERS=${USERS:-1000}
for mode in none counter timer histogram none; do
  echo "# $(date +%T) mode=$mode"
  LAB_USER_TAG=$mode docker compose up -d app >/dev/null 2>&1
  until curl -sf "${APP_URL:-http://localhost:21080}/actuator/health" >/dev/null; do sleep 2; done   # 앱 기동 대기
  docker compose --profile load run --rm -e USERS="$USERS" load >/dev/null 2>&1
  sleep 30                                             # 스크레이프 몇 번 돌 때까지
  python3 measure.py "$mode"
done
