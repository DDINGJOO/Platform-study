#!/bin/bash
# 지금 상태의 불일치를 센다. 한 줄 key=value 로 출력
CONF=/etc/nginx/apps/apps.conf
rows=$(psql -tAc "SELECT count(*) FROM tenants")
distinct=$(psql -tAc "SELECT count(DISTINCT name) FROM tenants")
locs=$(grep -c '^location' "$CONF")
locs_u=$(grep '^location' "$CONF" | sort -u | wc -l | tr -d ' ')
up=0; [ "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1/healthz)" = 200 ] && up=1
missing=0
for n in $(psql -tAc "SELECT DISTINCT name FROM tenants"); do
  [ "$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1/t/$n/")" = 200 ] || missing=$((missing+1))
done
orphan=0
for n in $(grep -o '/t/[^/]*/' "$CONF" | cut -d/ -f3 | sort -u); do
  [ "$(psql -tAc "SELECT count(*) FROM tenants WHERE name='$n'")" = 0 ] && orphan=$((orphan+1))
done
dup_rows=$((rows - distinct)); dup_locs=$((locs - locs_u))
echo "rows=$rows dup_rows=$dup_rows locations=$locs dup_locations=$dup_locs missing_routes=$missing orphan_routes=$orphan nginx_up=$up mismatch=$((dup_rows + dup_locs + missing + orphan))"
