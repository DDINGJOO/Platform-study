#!/bin/sh
# 리눅스 로드 애버리지가 같은 감쇠를 보이는지 본다. 기본: 2분 기록, CPU 태우기 8개 10분, 끄고 15분.
# 결과: ../data/loadavg.csv  (Docker VM 전체 값이라 다른 컨테이너의 부하가 섞인다)
cd "$(dirname "$0")"
docker run --rm --name metrics-05-loadavg \
  -e BASE="${BASE:-120}" -e ON="${ON:-600}" -e OFF="${OFF:-900}" -e BURN="${BURN:-8}" \
  -v "$PWD/probe.py:/probe.py:ro" -v "$PWD/../data:/data" \
  python:3.13-alpine python -u /probe.py
