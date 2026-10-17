#!/usr/bin/env bash
# 드라이버 jar 를 lib/ 에 두고 Lab.java 를 build/ 로 컴파일한다. Java 21 이상.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p lib build
J=lib/mysql-connector-j-9.1.0.jar
if [ ! -f "$J" ]; then
  if [ -f ~/.m2/repository/com/mysql/mysql-connector-j/9.1.0/mysql-connector-j-9.1.0.jar ]; then
    cp ~/.m2/repository/com/mysql/mysql-connector-j/9.1.0/mysql-connector-j-9.1.0.jar "$J"
  else
    curl -fsSL -o "$J" https://repo1.maven.org/maven2/com/mysql/mysql-connector-j/9.1.0/mysql-connector-j-9.1.0.jar
  fi
fi
javac -d build -cp "$J" src/Lab.java
echo "built: $(ls build | wc -l | tr -d ' ') classes"
