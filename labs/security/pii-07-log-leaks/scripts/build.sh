#!/usr/bin/env bash
# javac 로 컴파일한다. Lombok 은 어노테이션 프로세서로 붙인다.
set -euo pipefail
cd "$(dirname "$0")/.."
LIB="${LIB_DIR:-./lib}"
./scripts/fetch-deps.sh >/dev/null
CP=$(ls "$LIB"/*.jar | tr '\n' ':')
rm -rf build && mkdir -p build/classes
javac -encoding UTF-8 --release 25 -nowarn -proc:full -processorpath "$LIB/lombok-1.18.48.jar" \
  -cp "$CP" -d build/classes $(find src -name '*.java')
echo "빌드 완료: $(find build/classes -name '*.class' | wc -l | tr -d ' ') 클래스"
