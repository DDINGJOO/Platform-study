#!/usr/bin/env bash
# Connector/J 기본값과 useAffectedRows=true 로 같은 문장들을 돌린다.
# JAR 환경변수로 드라이버 jar 를 지정한다. 없으면 lib/ 에 Maven Central 에서 받는다.
set -euo pipefail
cd "$(dirname "$0")/.."
V=${CJ_VERSION:-9.7.0}
JAR=${JAR:-lib/mysql-connector-j-$V.jar}
if [[ ! -f "$JAR" ]]; then
  mkdir -p lib
  curl -sfL -o "$JAR" "https://repo1.maven.org/maven2/com/mysql/mysql-connector-j/$V/mysql-connector-j-$V.jar"
fi
BASE="jdbc:mysql://127.0.0.1:39020/lab?sslMode=DISABLED&allowPublicKeyRetrieval=true"
java -cp "$JAR" java/RowCount.java "Connector/J 기본값" "$BASE"
echo
java -cp "$JAR" java/RowCount.java "useAffectedRows=true" "$BASE&useAffectedRows=true"
