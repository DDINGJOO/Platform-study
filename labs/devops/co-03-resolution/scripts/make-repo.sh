#!/usr/bin/env bash
# libs/ 의 소스를 컴파일해 파일 기반 Maven 저장소 repo/ 를 만든다. mvn 컨테이너 안에서 돈다.
#   docker compose run --rm mvn bash scripts/make-repo.sh
set -euo pipefail
cd /work
rm -rf repo build-libs
mkdir -p repo build-libs
G=lab.co3
GP=lab/co3
grep -v '^#' libs/libs.txt | while read -r name ver deps; do
  [ -z "$name" ] && continue
  out=build-libs/$name-$ver
  mkdir -p "$out/classes"
  cp=""
  depxml=""
  if [ "$deps" != "-" ]; then
    IFS=',' read -ra arr <<< "$deps"
    for d in "${arr[@]}"; do
      dn=${d%%:*}; dv=${d##*:}
      cp="$cp:repo/$GP/$dn/$dv/$dn-$dv.jar"
      depxml="$depxml
    <dependency>
      <groupId>$G</groupId>
      <artifactId>$dn</artifactId>
      <version>$dv</version>
    </dependency>"
    done
  fi
  javac -nowarn --release 17 -d "$out/classes" -cp "${cp#:}" $(find "libs/$name-$ver" -name '*.java')
  dir=repo/$GP/$name/$ver
  mkdir -p "$dir"
  # 같은 입력이면 같은 jar 가 나오게 타임스탬프를 고정한다
  jar --create --date=2026-01-01T00:00:00Z --file "$dir/$name-$ver.jar" -C "$out/classes" .
  cat > "$dir/$name-$ver.pom" <<POM
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>$G</groupId>
  <artifactId>$name</artifactId>
  <version>$ver</version>
  <dependencies>$depxml
  </dependencies>
</project>
POM
  for f in "$dir/$name-$ver.jar" "$dir/$name-$ver.pom"; do
    sha1sum "$f" | cut -d' ' -f1 > "$f.sha1"
  done
  echo "published $G:$name:$ver deps=$deps"
done
rm -rf build-libs
find repo -name '*.jar' | sort
