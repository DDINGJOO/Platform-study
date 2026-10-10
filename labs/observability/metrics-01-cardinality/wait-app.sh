#!/usr/bin/env bash
# 앱이 /actuator/health 에 답할 때까지 기다린다. 다시 띄운 직후 부하를 넣으면 요청이 전부 실패한다.
until curl -sf "${APP_URL:-http://localhost:21080}/actuator/health" >/dev/null; do sleep 2; done
