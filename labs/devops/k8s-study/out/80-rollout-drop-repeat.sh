#!/usr/bin/env bash
# 롤링 업데이트 실패를 조건마다 여러 번: (a) 빠른 종료 (b) +preStop 5 (c) +preStop 5 +readinessProbe (d) +readinessProbe 를 회차마다 번갈아 돌려 (c) 0건이 우연인지, 조건별 실패 범위를 본다 (Mac 에서 실행)
# 32c-rollout-drop-kinds.sh 를 복사해 바꾼 것: 네임스페이스 blog-80, 회차마다 다른 이름, 이벤트는 그 회차 시작 이후 것만, 끝에 회차별 표
# 부하와 앱은 32c 와 같다: client 파드(curlimages/curl:8.11.1)에서 keep-alive 4개(curl 한 번에 URL 10개) + 새 연결 1개, ClusterIP 로 직접, 35초, nginx:1.27-alpine replicas 3
cd "${LAB:-$(dirname "$0")/../..}"   # 실습 저장소 루트 (./lab 이 있는 곳)
K="./lab kubectl"; NS=blog-80; DUR=35; REPS=${REPS:-3}
T=${W80_TMP:-$(mktemp -d)}; mkdir -p "$T"; SUM=$T/summary.txt; : > "$SUM"
echo "# 80 롤링 업데이트 실패 반복 ($(date '+%F %T %Z')), 조건 4개 x ${REPS}회, 회차마다 (a)(b)(c)(d) 순서"
$K get ns $NS >/dev/null 2>&1 || $K create ns $NS >/dev/null
$K run client -n $NS --image=curlimages/curl:8.11.1 --command -- sleep 7200 >/dev/null 2>&1
$K wait pod/client -n $NS --for=condition=Ready --timeout=120s >/dev/null
echo "client 파드 노드: $($K get pod client -n $NS -o jsonpath='{.spec.nodeName}')"
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
run(){ # $1 이름 $2 조건 $3 회차
  local S=$($K get svc $1 -n $NS -o jsonpath="{.spec.clusterIP}") L=$T/$1.log
  echo "  파드 노드(재시작 전): $($K get pod -n $NS -l app=$1 -o jsonpath='{range .items[*]}{.spec.nodeName} {end}')"
  $K exec client -n $NS -- sh -c "
    ka(){ end=\$((\$(date +%s)+$DUR)); while [ \$(date +%s) -lt \$end ]; do o=\$(curl -s -o /dev/null --max-time 2 -w 'ka%{http_code} e%{exitcode}\n' \$(for i in 1 2 3 4 5 6 7 8 9 10; do printf 'http://$S/ '; done)); echo \"\$o\"; echo \"\$o\" | grep ka000 | sed \"s/^/fail \$(date +%T) /\"; done; }
    nc(){ end=\$((\$(date +%s)+$DUR)); while [ \$(date +%s) -lt \$end ]; do o=\$(curl -s -o /dev/null --max-time 2 -w 'new%{http_code} e%{exitcode}' http://$S/); echo \"\$o\"; case \"\$o\" in new000*) echo \"fail \$(date +%T) \$o\";; esac; sleep 0.02; done; }
    ka & ka & ka & ka & nc & wait" > $L 2>&1 &
  local CP=$!; sleep 4
  echo "  $(date +%T) rollout restart"; $K rollout restart deploy/$1 -n $NS >/dev/null
  $K rollout status deploy/$1 -n $NS --timeout=120s >/dev/null; echo "  $(date +%T) rollout status 끝"
  wait $CP
  local all=0 bad=0
  for t in ka new; do tot=$(grep -c "^$t" $L); ok=$(grep -c "^${t}200 " $L); all=$((all+tot)); bad=$((bad+tot-ok)); echo "  $( [ $t = ka ] && echo 'keep-alive(4개)' || echo '새 연결(1개)  ') 요청 $tot, 실패 $((tot-ok))"; done
  echo "  실패 시각(초 단위 묶음, 시각은 curl 이 끝난 때): $(grep '^fail' $L | awk '{print $2"("$4")"}' | sort | uniq -c | awk '{printf "%s×%s ", $2, $1}')"
  echo "  파드 이벤트(시작·종료, 이 회차 시작 이후):"
  $K get events -n $NS --field-selector involvedObject.kind=Pod -o custom-columns='T:.lastTimestamp,R:.reason,P:.involvedObject.name' --no-headers | grep " $1-" | grep -E 'Started|Killing' | awk -v s="$RUN_START" '$1 >= s' | sort | awk '{split($1,a,"T"); sub("Z","",a[2]); n=$3; sub(/.*-/,"",n); print "    " a[2] " UTC " $2 " " n}'
  printf '%s %s %s %s %s %s %s %s\n' "$2" "$3" "$all" "$bad" "$(grep '^fail' $L | grep -c ' e7$')" "$(grep '^fail' $L | grep -c ' e56$')" "$(grep '^fail' $L | grep -c ' e28$')" "$(grep '^fail' $L | grep -vcE ' e(7|56|28)$')" >> "$SUM"
  rm -f $L; $K delete deploy,svc $1 -n $NS >/dev/null
}
one(){ # $1 조건 $2 회차 $3 이름 $4 컨테이너 추가 블록
  RUN_START=$(date -u -v-2S +%FT%TZ 2>/dev/null || date -u -d '-2 sec' +%FT%TZ)
  echo; echo "## ($1) 회차 $2: $5"; deploy $3 "$4"; run $3 $1 $2
}
for r in $(seq 1 $REPS); do
  one a $r rb80-fast-$r   "$FAST" "fast-exit, preStop 없음, readiness 없음"
  one b $r rb80-pre-$r    "$FAST
$PRE" "fast-exit + preStop 5, readiness 없음"
  one c $r rb80-pre-rp-$r "$FAST
$PRE
$RP" "fast-exit + preStop 5 + readinessProbe"
  one d $r rb80-rp-$r     "$FAST
$RP" "fast-exit + readinessProbe, preStop 없음"
done
$K delete pod client -n $NS --grace-period=1 --wait=false >/dev/null
echo; echo "## 회차별 실패 (요청 = keep-alive + 새 연결, 실패 종류는 curl 종료 코드: e7 연결 거부, e56 연결 리셋, e28 2초 타임아웃)"
printf '  %-4s %-4s %8s %6s %5s %5s %5s %5s\n' 조건 회차 요청 실패 e7 e56 e28 기타
sort -k1,1 -k2,2n "$SUM" | awk '{printf "  (%s)  %-4s %8s %6s %5s %5s %5s %5s\n", $1, $2, $3, $4, $5, $6, $7, $8}'
echo "  조건별 범위(실패 최소~최대, 합계/요청 합계):"
sort -k1,1 "$SUM" | awk '{c=$1; if(!(c in mn)||$4<mn[c])mn[c]=$4; if($4>mx[c])mx[c]=$4; s[c]+=$4; a[c]+=$3; n[c]++} END{for(c in n) printf "  (%s) %d회: %d~%d건, 합계 %d / %d\n", c, n[c], mn[c], mx[c], s[c], a[c]}' | sort
echo; echo "(노드·Mac 시각은 KST, 이벤트·client 의 실패 시각은 UTC: KST = UTC+9)"
