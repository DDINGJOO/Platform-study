#!/usr/bin/env bash
# Maven Central 에서 jar 를 받아 sha1 을 대조한다. mvn/gradle 없이 javac 로 빌드하기 위한 것.
set -euo pipefail
cd "$(dirname "$0")/.."
LIB="${LIB_DIR:-./lib}"
mkdir -p "$LIB"
grep -v '^#' deps.txt | while read -r g a v; do
  [ -z "$g" ] && continue
  f="$LIB/$a-$v.jar"
  [ -s "$f" ] && continue
  base="https://repo1.maven.org/maven2/$g/$a/$v/$a-$v.jar"
  curl -fsSL -o "$f.part" "$base"
  want=$(curl -fsSL "$base.sha1" | cut -c1-40)
  got=$(shasum -a 1 "$f.part" | cut -c1-40)
  [ "$want" = "$got" ] || { echo "sha1 불일치: $a $v" >&2; rm -f "$f.part"; exit 1; }
  mv "$f.part" "$f"; echo "받음 $a-$v.jar"
done
