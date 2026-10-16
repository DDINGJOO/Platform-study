#!/usr/bin/env bash
# 대상 저장소 클론, 릴리스 스냅숏 풀기, PMD 내려받기.
# 전부 WORK 아래(저장소 밖)에 둔다. 받은 저장소 안의 스크립트(gradlew 등)는 실행하지 않는다.
#   WORK=/tmp/clone-drift ./scripts/fetch.sh v6.1.0 v6.2.0
set -euo pipefail
WORK=${WORK:?WORK 를 저장소 밖 빈 디렉터리로 지정}
REPO_URL=${REPO_URL:-https://github.com/spring-projects/spring-framework.git}
PMD_VER=${PMD_VER:-7.28.0}
mkdir -p "$WORK"/{src,snap,pmd}

if [ ! -d "$WORK/src/repo/.git" ]; then
  git clone -q --no-checkout "$REPO_URL" "$WORK/src/repo"
fi
for t in "$@"; do
  if [ ! -d "$WORK/snap/$t" ]; then
    mkdir -p "$WORK/snap/$t"
    git -C "$WORK/src/repo" archive "$t" | tar -x -C "$WORK/snap/$t"
  fi
done
if [ ! -d "$WORK/pmd/pmd-bin-$PMD_VER" ]; then
  curl -sL -o "$WORK/pmd/pmd.zip" \
    "https://github.com/pmd/pmd/releases/download/pmd_releases%2F$PMD_VER/pmd-dist-$PMD_VER-bin.zip"
  shasum -a 256 "$WORK/pmd/pmd.zip"
  (cd "$WORK/pmd" && unzip -q pmd.zip)
fi
echo "repo=$WORK/src/repo pmd=$WORK/pmd/pmd-bin-$PMD_VER"
