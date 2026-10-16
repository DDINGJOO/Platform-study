#!/bin/bash
# 실습-1 의 실험 다섯 개를 차례로 돌리고 원자료를 out/ 에 남긴다.
# 실행 위치: labs/devops/auto-01-idempotent   (먼저 docker compose up -d --build)
set -u
cd "$(dirname "$0")/.."
mkdir -p out
X() { docker compose exec -T web "$@"; }
TRIALS=${TRIALS:-20}; LOAD_TRIALS=${LOAD_TRIALS:-5}

e1() {  # 같은 고객사를 차례로 두 번
  : > out/e1-seq.txt
  for s in naive idem; do
    X /ops/reset.sh
    { echo "## $s 1회차"; X /ops/$s.sh t1; echo "## $s 2회차"; X /ops/$s.sh t1; echo "## $s 확인"; X /ops/check.sh; } >> out/e1-seq.txt 2>&1
  done
}

e2() {  # 같은 고객사를 동시에 두 개
  : > out/e2-concurrent.txt
  for v in "naive" "idem LOCK=0" "idem LOCK=1"; do
    set -- $v; s=$1; envs=${2:-}
    for i in $(seq 1 "$TRIALS"); do
      X /ops/reset.sh
      outp=$(X env $envs bash -c "/ops/$s.sh t1 & /ops/$s.sh t1 & wait" 2>&1 | tr '\n' '|')
      echo "variant=\"$v\" trial=$i $(X /ops/check.sh) out=\"$outp\"" >> out/e2-concurrent.txt
    done
  done
}

e2b() {  # 서로 다른 고객사(t1, t2)를 동시에. 잠금이 없으면 늦게 읽은 목록이 먼저 쓴 파일을 덮을 수 있다
  : > out/e2b-concurrent-diff.txt
  for v in "naive" "idem LOCK=0" "idem LOCK=1"; do
    set -- $v; s=$1; envs=${2:-}
    for i in $(seq 1 "$TRIALS"); do
      X /ops/reset.sh
      outp=$(X env $envs bash -c "/ops/$s.sh t1 & /ops/$s.sh t2 & wait" 2>&1 | grep -E '^\[(naive|idem)\]' | tr '\n' '|')
      echo "variant=\"$v\" trial=$i $(X /ops/check.sh) out=\"$outp\"" >> out/e2b-concurrent-diff.txt
    done
  done
}

e3() {  # 부하를 건 채 설정 반영: stop/start(naive) 대 reload(idem)
  for v in naive idem; do
    for i in $(seq 1 "$LOAD_TRIALS"); do
      X /ops/reset.sh
      docker compose --profile load run --rm -e DURATION=20 -e OUT=/out/e3-$v-$i.csv load > /dev/null &
      lp=$!; sleep 8
      X bash -c "echo apply_start=\$EPOCHREALTIME; /ops/$v.sh n$i; echo rc=\$?; echo apply_end=\$EPOCHREALTIME" > out/e3-$v-$i.marks 2>&1
      wait $lp
    done
  done
}

e3b() {  # 틀린 설정(중복 location)을 반영할 때
  for v in stopstart reload killstart; do
    X /ops/reset.sh
    docker compose --profile load run --rm -e DURATION=20 -e OUT=/out/e3b-$v.csv load > /dev/null &
    lp=$!; sleep 8
    if [ $v = stopstart ]; then
      X bash -c 'echo "location /t/base/ { proxy_pass http://app:8080/; }" >> /etc/nginx/apps/apps.conf
        echo apply_start=$EPOCHREALTIME; nginx -s stop; echo stop_rc=$?
        end=$((SECONDS + 10)); while pgrep -x nginx >/dev/null; do [ $SECONDS -ge $end ] && { echo stop_timeout=1; break; }; sleep 0.01; done
        nginx; echo rc=$?; echo apply_end=$EPOCHREALTIME; echo nginx_running=$(pgrep -x nginx | wc -l)' > out/e3b-$v.marks 2>&1
    elif [ $v = killstart ]; then
      # nginx -s stop 대신 마스터에 직접 TERM 을 보낸다 (설정 파일을 읽지 않고 멈춘다)
      X bash -c 'echo "location /t/base/ { proxy_pass http://app:8080/; }" >> /etc/nginx/apps/apps.conf
        echo apply_start=$EPOCHREALTIME; kill -TERM $(cat /run/nginx.pid); echo stop_rc=$?
        end=$((SECONDS + 10)); while pgrep -x nginx >/dev/null; do [ $SECONDS -ge $end ] && { echo stop_timeout=1; break; }; sleep 0.01; done
        nginx; echo rc=$?; echo apply_end=$EPOCHREALTIME; echo nginx_running=$(pgrep -x nginx | wc -l)' > out/e3b-$v.marks 2>&1
    else
      X bash -c 'echo "location /t/base/ { proxy_pass http://app:8080/; }" >> /etc/nginx/apps/apps.conf
        echo apply_start=$EPOCHREALTIME; nginx -s reload; echo rc=$?; echo apply_end=$EPOCHREALTIME; echo nginx_running=$(pgrep -x nginx | wc -l)
        sleep 1; echo "nginx -t:"; nginx -t; echo "t_rc=$?"' > out/e3b-$v.marks 2>&1
    fi
    wait $lp
  done
  X /ops/reset.sh
}

e3c() {  # 문법은 맞지만 적용 단계에서 실패하는 설정 (이 호스트에 없는 문서용 주소 192.0.2.1 에 listen)
  X /ops/reset.sh
  X bash -c 'nginx -s stop; while pgrep -x nginx >/dev/null; do sleep 0.01; done
    rm -f /tmp/e3c-error.log; nginx -g "error_log /tmp/e3c-error.log notice;"; sleep 0.5
    echo "server { listen 192.0.2.1:81; return 200; }" > /etc/nginx/conf.d/bad.conf
    before=$(pgrep -P $(cat /run/nginx.pid) | sort | tr "\n" " ")
    echo "## nginx -t"; nginx -t; echo "t_rc=$?"
    echo "## nginx -s reload"; nginx -s reload; echo "reload_rc=$?"
    sleep 1
    after=$(pgrep -P $(cat /run/nginx.pid) | sort | tr "\n" " ")
    [ "$before" = "$after" ] && echo "workers_replaced=0" || echo "workers_replaced=1"
    echo "healthz=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1/healthz)"
    echo "## 마스터의 오류 로그 (notice 이상, 시각 제거)"
    grep -E "emerg|alert|crit|signal|reconfiguring|bind" /tmp/e3c-error.log | sed -E "s/^[0-9\/: ]+//"
    rm -f /etc/nginx/conf.d/bad.conf' > out/e3c-bind.txt 2>&1
  X /ops/reset.sh
}

e4() {  # 중간에 끊고 다시 돌리기
  : > out/e4-crash.txt
  for v in "naive" "idem APPLIED=file" "idem"; do
    set -- $v; s=$1; envs=${2:-}
    pts="after_db after_conf"; [ $s = idem ] && pts="after_db after_conf after_reload"
    for p in $pts; do
      X /ops/reset.sh
      c1=$(X env $envs CRASH_AT=$p /ops/$s.sh t1 2>&1 | tr '\n' '|')
      k1=$(X /ops/check.sh)
      c2=$(X env $envs /ops/$s.sh t1 2>&1 | tr '\n' '|'); rc=$?
      k2=$(X /ops/check.sh)
      echo "variant=\"$v\" crash_at=$p first=\"$c1\" after_crash: $k1 rerun=\"$c2\" after_rerun: $k2" >> out/e4-crash.txt
    done
  done
}

e5() {  # 드라이런과 빈 목록 막기
  X /ops/reset.sh
  { echo "## DRY_RUN=1 idem.sh t1"; X env DRY_RUN=1 /ops/idem.sh t1; echo "rc=$?"
    echo "## 드라이런 뒤 상태"; X /ops/check.sh
    echo "## DB 조회가 실패해 빈 목록을 받는 경우 (PGDATABASE=nope)"; X env PGDATABASE=nope /ops/idem.sh t1; echo "rc=$?"
    echo "## 그 뒤 상태"; X /ops/check.sh; } 2>&1 | sed -E 's/\((172|10|192\.168)\.[0-9.]+\)/(<컨테이너 IP>)/g' > out/e5-dryrun.txt
}

for e in ${@:-e1 e2 e2b e3 e3b e3c e4 e5}; do echo "== $e"; $e; done
