#!/usr/bin/env bash
# 실습을 한 번 돌리고 출력을 out/run-<번호>.txt 로 남긴다. 사용: scripts/run.sh [번호]
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p out
n="${1:-1}"
java src/MaskVsEncrypt.java | tee "out/run-${n}.txt"
