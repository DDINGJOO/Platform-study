#!/usr/bin/env bash
# mysql CLI 로 같은 문장들을 돌린다. CLI 는 CLIENT_FOUND_ROWS 를 켜지 않는다.
set -euo pipefail
cd "$(dirname "$0")/.."
{
  while IFS='|' read -r id desc stmt; do
    [[ -z "$id" || "$id" == \#* ]] && continue
    echo "DELETE FROM item; INSERT INTO item(id,code,v,hits) VALUES (1,'a',1,0);"
    echo "SELECT '$id' AS c;"
    echo "$stmt;"
    echo "SELECT ROW_COUNT() AS row_count;"
  done < sql/cases.txt
} > out/cli-cases.sql
# -vvv: 문장마다 "Query OK, N rows affected" 와 info 문자열을 찍는다. --force: C04 오류 뒤에도 계속
docker compose exec -T mysql mysql -uroot -plab lab -vvv --force < out/cli-cases.sql 2>&1 | grep -v 'Using a password'
