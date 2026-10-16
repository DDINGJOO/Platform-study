#!/bin/bash
# 처음 한 번: 스타터 1.0.0(정책 v1: 재시도 없음, 타임아웃 2초)을 내고 서비스 다섯 개 이미지를 1.0.0 으로 만든다.
set -e
source "$(dirname "$0")/lib.sh"
mkdir -p repo out results state
publish_starter 1.0.0 v1 1 2000
for i in 1 2 3 4 5; do build_svc svc$i 1.0.0; echo "built svc$i:1.0.0"; done
