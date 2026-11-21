#!/usr/bin/env bash
# 32b 에서 롤아웃과 무관한 시각에도 실패가 섞였다. DNS 를 빼려고 ClusterIP 로 직접 보내고, 실패를 curl 종료 코드로 나눈다 (Mac 에서 실행)
cd "$(dirname "$0")/../.."
K="./lab kubectl"; NS=ch05; DUR=35
echo "# 32c 롤링 업데이트 실패 시각·종류 (DNS 를 빼고 ClusterIP 로 직접) ($(date '+%F %T %Z'))"
$K run client -n $NS --image=curlimages/curl:8.11.1 --command -- sleep 3600 >/dev/null 2>&1
$K wait pod/client -n $NS --for=condition=Ready --timeout=120s >/dev/null
FAST='        command: ["sh", "-c", "nginx -g \"daemon off;\" & p=$!; trap \"nginx -s stop\" TERM QUIT; wait $p; wait $p"]'
PRE='        lifecycle: {preStop: {sleep: {seconds: 5}}}'
RP='        readinessProbe: {httpGet: {path: /, port: 80}, periodSeconds: 1}'
deploy(){ cat <<Y | $K apply -n $NS -f - >/dev/null
apiVersion: apps/v1
kind: Deployment
metadata: {name: $1}
spec:
  replicas: 3
  selector: {matchLabels: {app: $1}}
  template:
    metadata: {labels: {app: $1}}
    spec:
      containers:
      - name: web
        image: nginx:1.27-alpine
$2
---
apiVersion: v1
kind: Service
metadata: {name: $1}
spec: {selector: {app: $1}, ports: [{port: 80}]}
Y
$K rollout status deploy/$1 -n $NS --timeout=120s >/dev/null; }
run(){ local S=$($K get svc $1 -n $NS -o jsonpath="{.spec.clusterIP}")
  $K exec client -n $NS -- sh -c "
    ka(){ end=\$((\$(date +%s)+$DUR)); while [ \$(date +%s) -lt \$end ]; do o=\$(curl -s -o /dev/null --max-time 2 -w 'ka%{http_code} e%{exitcode}\n' \$(for i in 1 2 3 4 5 6 7 8 9 10; do printf 'http://$S/ '; done)); echo \"\$o\"; echo \"\$o\" | grep ka000 | sed \"s/^/fail \$(date +%T) /\"; done; }
    nc(){ end=\$((\$(date +%s)+$DUR)); while [ \$(date +%s) -lt \$end ]; do o=\$(curl -s -o /dev/null --max-time 2 -w 'new%{http_code} e%{exitcode}' http://$S/); echo \"\$o\"; case \"\$o\" in new000*) echo \"fail \$(date +%T) \$o\";; esac; sleep 0.02; done; }
    ka & ka & ka & ka & nc & wait" > /tmp/ch05-32c-$1.log 2>&1 &
  local CP=$!; sleep 4
  echo "  $(date +%T) rollout restart"; $K rollout restart deploy/$1 -n $NS >/dev/null
  $K rollout status deploy/$1 -n $NS --timeout=120s >/dev/null; echo "  $(date +%T) rollout status 끝"
  wait $CP
  for t in ka new; do tot=$(grep -c "^$t" /tmp/ch05-32c-$1.log); ok=$(grep -c "^${t}200 " /tmp/ch05-32c-$1.log); echo "  $( [ $t = ka ] && echo 'keep-alive(4개)' || echo '새 연결(1개)  ') 요청 $tot, 실패 $((tot-ok))"; done
  echo "  실패 시각(초 단위 묶음): $(grep '^fail' /tmp/ch05-32c-$1.log | awk '{print $2"("$4")"}' | sort | uniq -c | awk '{printf "%s×%s ", $2, $1}')"
  echo "  파드 이벤트(시작·종료):"
  $K get events -n $NS --field-selector involvedObject.kind=Pod -o custom-columns='T:.lastTimestamp,R:.reason,P:.involvedObject.name' --no-headers | grep "$1-" | grep -E 'Started|Killing' | sort | awk '{split($1,a,"T"); sub("Z","",a[2]); n=$3; sub(/.*-/,"",n); print "    " a[2] " UTC " $2 " " n}'
  rm -f /tmp/ch05-32c-$1.log; $K delete deploy,svc $1 -n $NS >/dev/null
}
echo; echo "## (a) fast-exit, preStop 없음, readiness 없음"; deploy rb-fast "$FAST"; run rb-fast
echo; echo "## (b) fast-exit + preStop 5, readiness 없음"; deploy rb-pre "$FAST
$PRE"; run rb-pre
echo; echo "## (c) fast-exit + preStop 5 + readinessProbe"; deploy rb-pre-rp "$FAST
$PRE
$RP"; run rb-pre-rp
echo; echo "## (d) fast-exit + readinessProbe, preStop 없음"; deploy rb-rp "$FAST
$RP"; run rb-rp
$K delete pod client -n $NS --grace-period=1 --wait=false >/dev/null
echo; echo "(노드·Mac 시각은 KST, 이벤트는 UTC: KST = UTC+9)"
