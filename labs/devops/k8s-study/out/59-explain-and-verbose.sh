#!/usr/bin/env bash
# explain 이 알려 주는 제약(ephemeralContainers 의 probe)과 kubectl -v=9 의 curl 형태 요청 (Mac 에서 실행)
# 실습 저장소 루트에서 실행한다. 조회만 한다(네임스페이스 default 오브젝트를 GET 한 번).
K="./lab kubectl"
echo "# 59 explain 과 -v=9 ($(date '+%F %T %Z'))"
echo; echo "## 1. kubectl explain pod.spec.ephemeralContainers.livenessProbe 의 DESCRIPTION 첫 줄"
$K explain pod.spec.ephemeralContainers.livenessProbe | sed -n '/^DESCRIPTION:/{n;p;}' | sed 's/^ */  /'
echo; echo "## 2. kubectl get ns default -v=9 : 요청을 curl 명령 모양으로 찍는다 (헤더 -H 는 이름만 남기고 서버 주소는 지움)"
$K get ns default -v=9 2>&1 | grep -m1 -A1 'curlCommand' | tail -1 | sed -E 's/-H "([^:]*):[^"]*"/-H "\1: …"/g; s#https://[^/]+#https://<API 서버>#; s/^[[:space:]]*/  /' 
