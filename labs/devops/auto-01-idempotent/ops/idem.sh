#!/bin/bash
# 수렴형으로 고쳐 쓴 스크립트 (신규 고객사 등록).
#   0) flock 으로 동시 실행 막기  1) UNIQUE 제약 + ON CONFLICT DO NOTHING
#   2) DB 목록으로 설정 파일 전체를 새로 만들고, 다르면 임시 파일 + rename
#   3) 반영된 내용과 다르면 nginx -t 후 reload  4) 새 경로로 요청해 200 확인
# 환경변수
#   LOCK=0          flock 을 끈다 (잠금 없이 동시에 돌려 보기)
#   APPLIED=file    "바뀌었나"를 파일끼리만 비교한다 (처음 짠 판. 3단계 직전에 끊기면 반영이 빠진다)
#   APPLIED=marker  마지막으로 reload 에 성공한 내용의 해시와 비교한다 (기본)
#   DRY_RUN=1       바꾸지 않고 바뀔 내용만 diff 로 보여 준다
#   CRASH_AT=after_db|after_conf|after_reload
set -uo pipefail
name=$1
CONF=/etc/nginx/apps/apps.conf
MARK=/run/apps.applied
DRY=${DRY_RUN:-0}
crash() { if [ "${CRASH_AT:-}" = "$1" ]; then echo "[idem] CRASH_AT=$1 에서 강제 종료"; kill -9 $$; fi; }

if [ "${LOCK:-1}" = 1 ]; then
  exec 9>/run/register-tenant.lock
  flock -n 9 || { echo "[idem] 다른 실행이 진행 중이라 종료"; exit 75; }
fi

# 0~1. 고객사 행: 시스템 제약으로 중복을 막고, 없을 때만 넣는다
psql -qc "CREATE UNIQUE INDEX IF NOT EXISTS tenants_name_uq ON tenants(name)" 2>/dev/null
if [ "$DRY" = 1 ]; then
  [ "$(psql -tAc "SELECT count(*) FROM tenants WHERE name='$name'")" = 0 ] && echo "[dry-run] DB: INSERT $name"
  names=$( { psql -tAc "SELECT name FROM tenants"; echo "$name"; } | sort -u)
else
  psql -qc "INSERT INTO tenants(name) VALUES ('$name') ON CONFLICT (name) DO NOTHING"
  crash after_db
  names=$(psql -tAc "SELECT name FROM tenants ORDER BY name")
fi
[ -n "$names" ] || { echo "[idem] DB 에서 고객사 목록을 못 읽었다. 멈춤"; exit 2; }

# 2. 원하는 설정을 DB 목록에서 통째로 만든다
new=$(mktemp /etc/nginx/apps/.apps.XXXXXX)
for n in $names; do echo "location /t/$n/ { proxy_pass http://app:8080/; }"; done > "$new"
old_n=$(grep -c '^location' "$CONF" || true); new_n=$(grep -c '^location' "$new" || true)
if [ "$new_n" -lt $(( (old_n + 1) / 2 )) ]; then
  echo "[idem] 경로가 $old_n 개에서 $new_n 개로 준다. 적용하지 않고 사람에게 넘김"; rm -f "$new"; exit 2
fi
if [ "$DRY" = 1 ]; then
  diff -u "$CONF" "$new" | sed 's/^/[dry-run] /'; rm -f "$new"; exit 0
fi
filechanged=0
if cmp -s "$new" "$CONF"; then rm -f "$new"; else mv "$new" "$CONF"; filechanged=1; fi
crash after_conf

# 3. 반영: 지금 돌고 있는 설정과 다를 때만 검사 후 reload
want=$(sha1sum "$CONF" | cut -d' ' -f1)
if [ "${APPLIED:-marker}" = file ]; then
  changed=$filechanged      # 처음 짠 판: 이번 실행에서 파일을 고쳤을 때만 reload
else
  changed=0; [ "$want" != "$(cat $MARK 2>/dev/null)" ] && changed=1
fi
if [ "$changed" = 1 ]; then
  nginx -t -q || { echo "[idem] 설정 검사 실패. 반영하지 않음"; exit 1; }
  nginx -s reload || { echo "[idem] reload 실패"; exit 1; }
  echo "$want" > $MARK
fi
crash after_reload

# 4. 결과 확인: 새 경로가 200 을 돌려줄 때까지 최대 5초
code=000
for i in $(seq 1 50); do
  code=$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1/t/$name/")
  [ "$code" = 200 ] && break; sleep 0.1
done
[ "$code" = 200 ] || { echo "[idem] 확인 실패: /t/$name/ 가 $code"; exit 1; }
echo "[idem] $name ok (changed=$changed)"
