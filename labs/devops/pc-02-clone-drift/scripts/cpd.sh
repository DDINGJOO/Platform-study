#!/usr/bin/env bash
# 한 스냅숏의 제품 코드(spring-*/src/main/java)에 CPD 를 돌린다.
# 벤더링한 코드(asm, cglib, objenesis, javapoet)는 뺀다. 원래 프로젝트에서 가져와 고치지 않는 코드다.
# --ignore-identifiers 는 쓰지 않는다. PMD 7.28.0 에서는 파일 사이에 생성자 감지 상태가 남아
# 이 저장소 전체에 돌리면 NullPointerException 으로 멈춘다(pmd/pmd#7133, 7.29.0 에서 고침).
# 그래서 정규화는 리터럴만 한다(--ignore-literals).
#   WORK=... ./scripts/cpd.sh v6.1.0 [최소토큰=100]
set -euo pipefail
WORK=${WORK:?}; TAG=$1; MIN=${2:-100}
PMD=${PMD:-$WORK/pmd/pmd-bin-7.28.0}
HERE=$(cd "$(dirname "$0")/.." && pwd)
SNAP="$WORK/snap/$TAG"
LIST="$HERE/out/files-$TAG.txt"
(cd "$SNAP" && find . -path './spring-*/src/main/java/*.java' \
   | grep -vE '/org/springframework/(asm|cglib|objenesis|javapoet)/' \
   | sed 's#^\./##' | sort) > "$LIST"
echo "files: $(wc -l < "$LIST")"
(cd "$SNAP" && java -cp "$PMD/conf:$PMD/lib/*" net.sourceforge.pmd.cli.PmdCli cpd \
   --minimum-tokens "$MIN" --language java --ignore-literals \
   --file-list "$LIST" --format xml --no-fail-on-violation \
   --report-file "$HERE/out/cpd-$TAG-t$MIN.xml")
ls -la "$HERE/out/cpd-$TAG-t$MIN.xml"
