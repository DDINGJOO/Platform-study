#!/usr/bin/env bash
# konst 의 상수를 쓰는 방식에 따라 javac 가 상수 풀에 lab/konst/K 참조를 남기는지 본다.
# repo/ 가 있어야 한다. 호스트 JDK 로 돈다(javac 버전을 함께 찍는다).
set -u
cd "$(dirname "$0")/.."
T=$(mktemp -d); K=repo/lab/co3/konst/1.0/konst-1.0.jar
CP=$K:repo/lab/co3/b/1.0/b-1.0.jar:repo/lab/co3/d/1.0/d-1.0.jar:repo/lab/co3/c/2.0/c-2.0.jar
javac -version 2>&1
javac --release 17 -d "$T" -cp "$CP" maven/an/src/main/java/lab/co3/Main.java extra/const/*.java
for c in Main SwitchUse AnnotationUse; do
  n=$(javap -v -cp "$T" lab.co3.$c | grep -c 'Class .*lab/konst/K')
  echo "== $c : 상수 풀의 'Class lab/konst/K' 항목 $n 개"
  javap -v -cp "$T" lab.co3.$c | grep -E 'lab/konst/K|konst' | head -4
done
rm -rf "$T"
