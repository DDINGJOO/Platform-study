#!/usr/bin/env bash
# e28(2초 타임아웃)은 어디서 오나: client 노드에서 SYN·RST(tcpdump)와 conntrack 항목(nfnetlink 읽기 전용 덤프), 노드마다 멈춤(50ms 잠들기의 지연), client 파드 소켓 수를 같이 기록하고 실패한 전송의 시각과 맞춘다 (Mac 에서 실행)
# 부하·앱은 80-rollout-drop-repeat.sh(=32c)와 같다. 바꾼 것: curl 이 전송마다 time_total·time_connect·num_connects 를 남기고, 출력은 파드 안 파일에 쓴 뒤 끝나고 가져온다
# (32c 와 같이 -o /dev/null 은 첫 URL 에만 걸려 나머지 9개의 응답 본문도 출력에 섞인다. 요약 awk 는 curl -w 줄만 센다)
# 노드에는 아무것도 설치하지 않는다: tcpdump·python3 는 원래 있다(conntrack CLI 와 /proc/net/nf_conntrack 은 없음). 네임스페이스 blog-80 만 쓴다
# 인자: 돌릴 조건들 (a b c d 중, 기본 "a d a")
cd "${LAB:-$(dirname "$0")/../..}"   # 실습 저장소 루트 (./lab 이 있는 곳)
HERE=${HERE:-$(cd "$(dirname "$0")" && pwd)}   # 80-node-mon.py, 80-e28-analyze.py 가 있는 곳
K="./lab kubectl"; NS=blog-80; DUR=35; CONDS=${*:-a d a}
T=${W80_TMP:-$(mktemp -d)}; mkdir -p "$T"
now(){ perl -MTime::HiRes=time -e 'printf "%.3f", time'; }
echo "# 80 e28 추적 ($(date '+%F %T %Z')), 조건: $CONDS"
$K get ns $NS >/dev/null 2>&1 || $K create ns $NS >/dev/null
$K run e28-client -n $NS --image=curlimages/curl:8.11.1 --command -- sleep 7200 >/dev/null 2>&1
$K wait pod/e28-client -n $NS --for=condition=Ready --timeout=120s >/dev/null
CN=$($K get pod e28-client -n $NS -o jsonpath='{.spec.nodeName}'); CLI=$($K get pod e28-client -n $NS -o jsonpath='{.status.podIP}')
echo "client 파드: 노드 $CN"
echo "노드 시계 - Mac 시계(초):"
for n in k8s-master k8s-worker1 k8s-worker2 k8s-worker3; do a=$(now); v=$(limactl shell $n -- date +%s.%N); b=$(now); o=$(echo "$v - ($a + $b) / 2" | bc -l); printf '  %-12s %+.3f\n' $n $o; [ $n = $CN ] && OFF=$o; done
cat > $T/load.sh <<'L'
S=$1; DUR=$2
U=""; for i in 1 2 3 4 5 6 7 8 9 10; do U="$U http://$S/"; done
W='%{http_code} e%{exitcode} t%{time_total} c%{time_connect} n%{num_connects}\n'
ka(){ end=$(( $(date +%s)+DUR )); while [ $(date +%s) -lt $end ]; do read u0 x < /proc/uptime; o=$(curl -s -o /dev/null --max-time 2 -w "$W" $U); printf 'B %s\n%s\n' "$u0" "$o"; done > /tmp/$1; }
nc(){ end=$(( $(date +%s)+DUR )); while [ $(date +%s) -lt $end ]; do read u0 x < /proc/uptime; o=$(curl -s -o /dev/null --max-time 2 -w "$W" http://$S/); printf 'B %s\n%s\n' "$u0" "$o"; sleep 0.02; done > /tmp/$1; }
so(){ end=$(( $(date +%s)+DUR+2 )); while [ $(date +%s) -lt $end ]; do read u0 x < /proc/uptime; printf 'S %s %s\n' "$u0" "$(grep '^TCP:' /proc/net/sockstat)"; sleep 1; done > /tmp/so; }
rm -f /tmp/ka1 /tmp/ka2 /tmp/ka3 /tmp/ka4 /tmp/nc1 /tmp/so
ka ka1 & ka ka2 & ka ka3 & ka ka4 & nc nc1 & so & wait
L
cat > $T/summ.sh <<'L'
for f in ka1 ka2 ka3 ka4 nc1; do awk -v f=$f '/^B /{u=$2; c=0; next} /^[0-9][0-9][0-9] e[0-9]+ t[0-9.]+ c[0-9.]+ n[0-9]+$/ {n++; t=substr($3,2); if($1=="200") ok++; else printf "F %s %s %s %.2f %s %s %s\n", f, $1, $2, u+c, t, substr($4,2), substr($5,2); c+=t} END{printf "N %s %d %d\n", f, n, ok}' /tmp/$f; done; cat /tmp/so
L
$K exec -i e28-client -n $NS -- sh -c 'cat > /tmp/load.sh' < $T/load.sh
$K exec -i e28-client -n $NS -- sh -c 'cat > /tmp/summ.sh' < $T/summ.sh
GAP='import time,sys
end=time.time()+float(sys.argv[1]); last=time.monotonic(); mx=0
while time.time()<end:
    time.sleep(0.05); n=time.monotonic(); g=n-last; last=n; mx=max(mx,g)
    if g>0.3: print("G %.3f %.3f" % (time.time(), g), flush=True)
print("M %.3f" % mx)'
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
podlist(){ $K get pod -n $NS -l app=$1 -o jsonpath='{range .items[*]}{.metadata.name}={.status.podIP}@{.spec.nodeName} {end}'; }
i=0
for c in $CONDS; do
  i=$((i+1)); case $c in
    a) B="$FAST"; D="fast-exit, preStop 없음, readiness 없음";;
    b) B="$FAST
$PRE"; D="fast-exit + preStop 5, readiness 없음";;
    c) B="$FAST
$PRE
$RP"; D="fast-exit + preStop 5 + readinessProbe";;
    d) B="$FAST
$RP"; D="fast-exit + readinessProbe, preStop 없음";;
  esac
  NAME=e28-$c-$i; echo; echo "## ($c) $D  [$NAME]"
  deploy $NAME "$B"
  CIP=$($K get svc $NAME -n $NS -o jsonpath='{.spec.clusterIP}')
  printf 'CLI=%s\nCIP=%s\nOFF=%s\nOLD=%s\n' "$CLI" "$CIP" "$OFF" "$(podlist $NAME)" > $T/$NAME.meta
  limactl shell $CN -- sudo timeout $((DUR+12)) tcpdump -i any -nn -tt -S -l -s 128 "tcp port 80 and (host $CLI or host $CIP) and ((tcp[13] & 0x12) == 0x02 or (tcp[13] & 0x04) != 0)" > $T/$NAME.tcpd 2> $T/$NAME.tcpd.err &
  limactl shell $CN -- sudo python3 - $((DUR+10)) $CLI $CIP 3 < $HERE/80-node-mon.py > $T/$NAME.mon 2>&1 &
  for n in k8s-worker1 k8s-worker2 k8s-worker3; do limactl shell $n -- python3 -c "$GAP" $((DUR+10)) > $T/$NAME.gap.$n 2>&1 & done
  sleep 2
  $K exec e28-client -n $NS -- sh /tmp/load.sh $CIP $DUR > /dev/null 2>&1 &
  LP=$!; sleep 4
  RS=$(now); $K rollout restart deploy/$NAME -n $NS >/dev/null; echo "RESTART=$RS" >> $T/$NAME.meta
  $K rollout status deploy/$NAME -n $NS --timeout=120s >/dev/null; RE=$(now)
  wait $LP; sleep 1
  echo "NEW=$(podlist $NAME)" >> $T/$NAME.meta
  $K exec e28-client -n $NS -- sh /tmp/summ.sh > $T/$NAME.pod
  wait
  printf '  rollout restart -> status 끝 %.1f초, tcpdump: %s\n' "$(echo "$RE - $RS" | bc -l)" "$(grep -h 'dropped by kernel\|captured' $T/$NAME.tcpd.err | tr '\n' ' ')"
  python3 $HERE/80-e28-analyze.py $T $NAME
  for n in k8s-worker1 k8s-worker2 k8s-worker3; do
    printf '  %s 멈춤(50ms 잠들기가 0.3초 넘게 걸린 때, restart 기준): %s 최대 %ss\n' $n "$(awk -v r=$(echo "$RS + $OFF" | bc -l) '/^G/{printf "%+.1fs(%.2fs) ", $2-r, $3}' $T/$NAME.gap.$n)" "$(awk '/^M/{print $2}' $T/$NAME.gap.$n)"
  done
  echo "  파드 이벤트(시작·종료):"
  $K get events -n $NS --field-selector involvedObject.kind=Pod -o custom-columns='T:.lastTimestamp,R:.reason,P:.involvedObject.name' --no-headers | grep " $NAME-" | grep -E 'Started|Killing' | sort | awk '{split($1,a,"T"); sub("Z","",a[2]); n=$3; sub(/.*-/,"",n); print "    " a[2] " UTC " $2 " " n}'
  $K delete deploy,svc $NAME -n $NS >/dev/null
done
$K delete pod e28-client -n $NS --grace-period=1 --wait=false >/dev/null
echo; echo "(이벤트는 UTC, KST = UTC+9. restart 기준 +초는 client 노드 시계)"
