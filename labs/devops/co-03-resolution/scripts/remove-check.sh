#!/usr/bin/env bash
# 분석기가 "안 쓴다"고 한 e, drv 와 상수만 쓰는 konst 를 하나씩 빼고 an 을 실행해 본다.
# repo/ 가 있어야 한다(./scripts/lab.sh repo). 호스트의 JDK 17 이상으로 돈다.
set -u
cd "$(dirname "$0")/.."
T=$(mktemp -d); R=repo/lab/co3
CP=$R/b/1.0/b-1.0.jar:$R/d/1.0/d-1.0.jar:$R/c/2.0/c-2.0.jar:$R/e/1.0/e-1.0.jar:$R/drv/1.0/drv-1.0.jar:$R/konst/1.0/konst-1.0.jar
javac --release 17 -d "$T" -cp "$CP" maven/an/src/main/java/lab/co3/Main.java
for lib in none e drv konst; do
  echo "--- 뺀 것: $lib"
  cp=$(echo "$CP" | tr ':' '\n' | grep -v "/$lib/" | paste -sd: -)
  java -cp "$T:$cp" lab.co3.Main 2>&1 | grep -E 'RESULT|Exception' | head -5
done
rm -rf "$T"
