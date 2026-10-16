#!/usr/bin/env bash
# 세 데모를 릴리스별로 돌려 out/demo/ 에 남긴다. 컴파일 경고(삭제 예정 API)는 stderr 라 버린다.
#   WORK=... ./scripts/run_demos.sh
set -uo pipefail
WORK=${WORK:?}; HERE=$(cd "$(dirname "$0")/.." && pwd); cd "$HERE"
mkdir -p out/demo
java -version 2>&1 | head -1 > out/demo/java-version.txt
for v in 6.1.3 6.2.0; do ./scripts/fetch-jars.sh $v >/dev/null; java -cp "$WORK/jars/$v/*" demo/MaxPartsDemo.java 2>/dev/null; done > out/demo/maxparts.txt
for v in 6.2.0 6.2.19 7.0.0; do ./scripts/fetch-jars.sh $v >/dev/null; java -cp "$WORK/jars/$v/*" demo/HeadersDemo.java 2>/dev/null; done > out/demo/headers.txt
for v in 6.2.0 6.2.19 7.0.0; do java -cp "$WORK/jars/$v/*" demo/ErrorMessageDemo.java 2>/dev/null; done > out/demo/error-message.txt
head -50 out/demo/*.txt
