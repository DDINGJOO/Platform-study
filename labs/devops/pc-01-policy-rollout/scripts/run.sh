#!/bin/bash
# 사용: ./scripts/run.sh <방식> <이름>
#   lib     : 스타터 1.1.0(정책 v2)을 내고, 서비스마다 재빌드 → 재기동(한 대씩)
#   dyn     : 서비스마다 정책 파일을 v2 로 바꾼다(재기동 없음)
#   sidecar : 사이드카 Envoy 마다 RDS 파일을 v2 로 바꿔치운다(재기동 없음)
#   upgrade : 사이드카 Envoy 자체를 v1.39.2 -> v1.39.3 으로 바꾼다(사이드카 재기동, 정책은 v2 그대로)
# 정책 v1 = 재시도 없음, 시도당 2초. v2 = 시도 3번(재시도 2번), 시도당 0.5초.
# 앞뒤 20초씩 부하만 흘리고, 그 사이에 바꾼다. 부하: 서비스마다 초당 RATE 건(기본 20).
set -e
source "$(dirname "$0")/lib.sh"
arm=$1; name=$2; RATE=${RATE:-20}; PAD=${PAD:-20}
MARKS=out/$name.marks; CSV=out/$name.csv; : > "$MARKS"
svcs="1 2 3 4 5"

case $arm in
  lib|dyn) prof=$arm; prefix=$arm-svc; base=3700 ;;
  sidecar|upgrade) prof=sidecar; prefix=sc-svc; base=3701 ;;
esac

# 처음 상태로 되돌린다
docker compose --profile lib --profile dyn --profile sidecar down --remove-orphans >/dev/null 2>&1 || true
mkdir -p state/dyn
for i in $svcs; do
  mkdir -p state/envoy/svc$i
  cp envoy/rds-v1.yaml state/envoy/svc$i/rds.yaml
  printf 'policy.name=v1\npolicy.maxAttempts=1\npolicy.timeoutMs=2000\n' > state/dyn/svc$i.properties
done
if [ "$arm" = upgrade ]; then for i in $svcs; do cp envoy/rds-v2.yaml state/envoy/svc$i/rds.yaml; done; fi
if [ "$arm" = lib ]; then publish_starter 1.0.0 v1 1 2000; fi    # 1.0.0 을 다시 내도 내용은 같다
ENVOY_TAG=v1.39.2 docker compose --profile $prof up -d >/dev/null 2>&1
for i in $svcs; do wait_up $base$i; done
curl -s -X POST localhost:37080/reset >/dev/null
sleep 3

targets=""; for i in $svcs; do targets="$targets svc$i=$base$i"; done
python3 scripts/loadgen.py "$CSV" $targets --rate "$RATE" &
LG=$!
trap 'kill $LG 2>/dev/null || true' EXIT
mark load_start
sleep "$PAD"
docker inspect -f '{{.Name}} {{.State.StartedAt}} {{.RestartCount}}' $(docker compose --profile $prof ps -q) > out/$name.before
mark rollout_start

case $arm in
  lib)
    mark starter_build_start
    publish_starter 1.1.0 v2 3 500
    mark starter_published
    for i in $svcs; do
      mark build_start svc$i
      BUILD_ID=$name build_svc svc$i 1.1.0
      mark build_done svc$i
      env SVC${i}_TAG=1.1.0 docker compose --profile lib up -d --no-deps lib-svc$i >/dev/null 2>&1
      mark restart_issued svc$i
      until curl -s "localhost:$base$i/policy" 2>/dev/null | grep -q '"v2"'; do sleep 0.1; done
      mark serving_v2 svc$i
    done ;;
  dyn)
    for i in $svcs; do
      printf 'policy.name=v2\npolicy.maxAttempts=3\npolicy.timeoutMs=500\n' > state/dyn/.svc$i.new
      mv state/dyn/.svc$i.new state/dyn/svc$i.properties
      mark pushed svc$i
    done
    for i in $svcs; do
      until curl -s "localhost:$base$i/policy" | grep -q '"v2"'; do sleep 0.05; done
      mark serving_v2 svc$i
    done ;;
  sidecar)
    for i in $svcs; do
      cp envoy/rds-v2.yaml state/envoy/svc$i/.rds.new
      # 호스트에서 mv 하면 Envoy 가 못 알아챈다(README 함정 1). 컨테이너 안에서 rename 한다
      docker exec "$(docker compose ps -q sc-envoy$i)" mv /etc/envoy/dyn/.rds.new /etc/envoy/dyn/rds.yaml
      mark pushed svc$i
    done
    for i in $svcs; do
      until curl -s "localhost:3702$i/stats?filter=rds.backend_route.version_text" | grep -q '"v2"'; do sleep 0.05; done
      mark serving_v2 svc$i "$(curl -s "localhost:3702$i/stats?filter=rds.backend_route.update_time" | awk '{print $2}')"
    done ;;
  upgrade)
    for i in $svcs; do
      mark recreate_issued svc$i
      ENVOY_TAG=v1.39.3 docker compose --profile sidecar up -d --no-deps sc-envoy$i >/dev/null 2>&1
      until curl -s "localhost:3702$i/server_info" 2>/dev/null | grep -q '1.39.3'; do sleep 0.05; done
      mark envoy_new svc$i
      until [ "$(curl -s -o /dev/null -w '%{http_code}' localhost:$base$i/work)" != 503 ]; do sleep 0.05; done
      mark serving svc$i
    done ;;
esac

mark rollout_done
docker inspect -f '{{.Name}} {{.State.StartedAt}} {{.RestartCount}}' $(docker compose --profile $prof ps -q) > out/$name.after
sleep "$PAD"
kill $LG; wait $LG 2>/dev/null || true
trap - EXIT
mark load_stop
curl -s localhost:37080/stats > out/$name.backend.json
docker stats --no-stream --format '{{.Name}} {{.MemUsage}} {{.CPUPerc}}' > out/$name.stats
echo done $name
