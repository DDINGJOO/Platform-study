#!/bin/bash
# 실험마다 처음 상태로: 고객사 base 하나, UNIQUE 인덱스 없음, nginx 새로 시작
CONF=/etc/nginx/apps/apps.conf
psql -qc "DROP INDEX IF EXISTS tenants_name_uq; TRUNCATE tenants RESTART IDENTITY; INSERT INTO tenants(name) VALUES ('base')" >/dev/null
echo 'location /t/base/ { proxy_pass http://app:8080/; }' > "$CONF"
rm -f /etc/nginx/apps/.apps.* /run/apps.applied
if pgrep -x nginx >/dev/null; then nginx -s stop; while pgrep -x nginx >/dev/null; do sleep 0.01; done; fi
nginx
sha1sum "$CONF" | cut -d' ' -f1 > /run/apps.applied
