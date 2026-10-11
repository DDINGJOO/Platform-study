#!/usr/bin/env bash
# 실습 디렉터리에서 실행한다: ./sim/run.sh
# sim/in/*.png 에 시뮬레이션을 걸어 sim/out/ 에 저장하고, stat 패널 두 칸의 색차를 잰다. 의존성은 컨테이너 안에서만 설치한다.
set -euo pipefail
docker run --rm -v "$PWD:/w" -w /w python:3.12-slim sh -c \
  "pip install -q --root-user-action=ignore numpy==2.3.4 pillow==12.0.0 daltonlens==0.1.5 && python sim/simulate.py && python sim/tiles.py"
