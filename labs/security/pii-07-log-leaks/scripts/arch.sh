#!/usr/bin/env bash
# ArchUnit 규칙 세 개를 컴파일된 클래스에 돌린다.
set -euo pipefail
cd "$(dirname "$0")/.."
LIB="${LIB_DIR:-./lib}"
mkdir -p out
CP="build/classes:$(ls "$LIB"/*.jar | tr '\n' ':')"
java -Dlogback.configurationFile=conf/logback.xml -cp "$CP" lab.arch.PiiRules 2>&1 | grep -v -e '^WARNING' -e 'DEBUG' -e 'PluginLoader' | tee out/arch.txt
