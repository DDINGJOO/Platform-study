#!/usr/bin/env bash
# Spring Boot 앱 모드 실행. 사용: [ERRCODES=1] scripts/app.sh <port> <mode> [kind] [code]
#  ERRCODES=1 이면 errcodes/sql-error-codes.xml 을 클래스패스 루트에 얹는다(loader.path)
set -euo pipefail
cd "$(dirname "$0")/.."
port=$1; shift
url="jdbc:mysql://127.0.0.1:${port}/lab?useSSL=false&allowPublicKeyRetrieval=true"
if [ "${ERRCODES:-0}" = 1 ]; then
  java -Dloader.path=errcodes -cp app/build/libs/scope.jar org.springframework.boot.loader.launch.PropertiesLauncher \
    "$@" --spring.datasource.url="$url"
else
  java -jar app/build/libs/scope.jar "$@" --spring.datasource.url="$url"
fi
