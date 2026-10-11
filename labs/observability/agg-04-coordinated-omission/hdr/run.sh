#!/usr/bin/env bash
# HdrHistogram 2.2.2 로 k6 결과를 보정한다. JDK 컨테이너에서 단일 파일 자바로 돌린다.
# 실습 디렉터리에서 실행한다: ./hdr/run.sh out/closed.csv 100
set -euo pipefail
JAR=hdr/HdrHistogram-2.2.2.jar
[ -f "$JAR" ] || curl -sSfL -o "$JAR" https://repo1.maven.org/maven2/org/hdrhistogram/HdrHistogram/2.2.2/HdrHistogram-2.2.2.jar
docker run --rm -v "$PWD:/w" -w /w eclipse-temurin:21-jdk java -cp "$JAR" hdr/Correct.java "$@"
