#!/usr/bin/env bash
# 사용법: scripts/run.sh <이름> [dto=..] [code=..] [mask=..] [wire=..] [turbo=..]
# 출력은 out/<이름>.log 에 저장하고 화면에도 보낸다.
set -euo pipefail
cd "$(dirname "$0")/.."
LIB="${LIB_DIR:-./lib}"
name="$1"; shift
props=()
for kv in "$@"; do props+=("-D$kv"); done
mkdir -p out
CP="build/classes:$(ls "$LIB"/*.jar | tr '\n' ':')"
java -Dlogback.configurationFile=conf/logback.xml -Dfile.encoding=UTF-8 -Dstdout.encoding=UTF-8 \
  ${props[@]+"${props[@]}"} -cp "$CP" lab.Lab > "out/$name.log" 2>&1
cat "out/$name.log"
