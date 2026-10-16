#!/bin/bash
# 절차서를 그대로 옮긴 스크립트 (신규 고객사 등록).
#   1) 이미 있으면 중단  2) DB 행 추가  3) 설정에 location 한 줄 덧붙이기  4) nginx 멈췄다 켜기
# CRASH_AT=after_db|after_conf 를 주면 그 지점에서 스스로 kill -9 한다(중간에 끊긴 실행 재현).
name=$1
CONF=/etc/nginx/apps/apps.conf
crash() { if [ "${CRASH_AT:-}" = "$1" ]; then echo "[naive] CRASH_AT=$1 에서 강제 종료"; kill -9 $$; fi; }

# 1. 애플리케이션이 이미 있는지 확인한다. 있으면 중단
n=$(psql -tAc "SELECT count(*) FROM tenants WHERE name='$name'")
if [ "$n" -gt 0 ]; then echo "[naive] $name already exists"; exit 0; fi

# 2. 새 고객사 행을 만든다
psql -qc "INSERT INTO tenants(name) VALUES ('$name')"
crash after_db

# 3. 경로를 설정에 더한다
echo "location /t/$name/ { proxy_pass http://app:8080/; }" >> "$CONF"
crash after_conf

# 4. 웹 서버를 멈추고 (옛 프로세스가 다 끝날 때까지 기다린 뒤) 다시 켠다
# (실습용 보강) 절차서에는 없지만, stop 이 실패하면 아래 기다림이 끝나지 않으므로 종료 코드를 남기고 10초에서 끊는다
nginx -s stop; src=$?
[ "$src" = 0 ] || echo "[naive] nginx -s stop rc=$src"
end=$((SECONDS + 10))
while pgrep -x nginx >/dev/null; do
  [ "$SECONDS" -ge "$end" ] && { echo "[naive] 10초 기다려도 nginx 가 내려가지 않음"; break; }
  sleep 0.01
done
if ! nginx; then echo "[naive] nginx 시작 실패"; exit 1; fi
echo "[naive] $name done"
