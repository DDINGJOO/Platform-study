#!/bin/bash
# 잠금 빌드가 저장소의 버전 목록(maven-metadata.xml)을 읽는지 확인한다
# 실행: 이 실습 디렉터리에서 `python3 scripts/lab.py up` 직후(빈 저장소) `bash scripts/lockcheck.sh`
G() { docker compose run --rm -T gradle-ci gradle -q --console=plain "$@"; }
for v in 2.10.9 2.10.10; do G -p /work/lib clean publish -Paid=dyn -Pver=$v -Pcontent=dyn-$v >/dev/null 2>&1; done
G -p /work/lib clean publish -Paid=util -Pver=1.0.0 -Pcontent=u >/dev/null 2>&1
rm -f projects/consumer-locked/gradle.lockfile
G -p /work/consumer-locked dependencies --configuration runtimeClasspath -Plock --write-locks --refresh-dependencies >/dev/null 2>&1
echo "## 잠금 파일"; grep lab projects/consumer-locked/gradle.lockfile
echo "## 1. 목록 파일이 정상일 때"
echo "locked:   $(G -p /work/consumer-locked resolved -Plock --refresh-dependencies 2>&1 | grep RESOLVED | tr '\n' ' ')"
echo "## 2. lab:dyn 의 목록 파일을 <metadata/> 로 덮어쓴다"
curl -s -o /dev/null -w "PUT releases/lab/dyn/maven-metadata.xml -> %{http_code}\n" -u lab:lab-secret-123 -X PUT --data '<metadata/>' localhost:30080/releases/lab/dyn/maven-metadata.xml
echo "## 3. 덮어쓴 뒤 (모두 --refresh-dependencies)"
echo "--- 잠금 있음 (빌드 파일은 lab:dyn:2.10.+, 잠금 2.10.10)"
G -p /work/consumer-locked resolved -Plock --refresh-dependencies 2>&1 | grep -E "RESOLVED|Could not|Cannot|No versions|BUILD|rejected|strictly" | head -8
echo "--- 잠금 없음 (같은 빌드 파일)"
G -p /work/consumer-locked resolved --refresh-dependencies 2>&1 | grep -E "RESOLVED|Could not|Cannot|No versions|BUILD" | head -6
echo "--- 고정 버전 lab:dyn:2.10.10"
G -p /work/consumer-gradle resolved '-Pdeps=lab:dyn:2.10.10' --refresh-dependencies 2>&1 | grep -E "RESOLVED|Could not|BUILD" | head -4
