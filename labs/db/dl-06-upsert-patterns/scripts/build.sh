#!/usr/bin/env bash
# 앱 jar 를 만든다(JDK 21 이상). 결과: app/build/libs/upsert.jar
set -euo pipefail
cd "$(dirname "$0")/../app"
./gradlew bootJar -q --no-daemon
