#!/usr/bin/env bash
# kube-proxy 가 없는 노드에서 파드 수가 바뀌면 그 노드의 iptables 규칙은 옛 상태로 남는가 (Mac 에서 실행)
# 방법: kube-proxy DaemonSet 에 worker1 을 빼는 nodeAffinity 를 잠시 넣어 worker1 의 kube-proxy 만 없앤다. 끝에서 되돌린다.
cd "$(dirname "$0")/../.."   # 실습 저장소 루트 (./lab 이 있는 곳)
K="./lab kubectl"; ts(){ date '+%T'; }
VIP=$($K get svc myweb -o jsonpath='{.spec.clusterIP}')
sep(){ ./lab ssh $1 -- sudo sh -c 'iptables-save -t nat 2>/dev/null' | grep -- "-A $SVC .*KUBE-SEP" | grep -oE '> [0-9.]+' | tr -d '> ' | sort | paste -sd' ' -; }
curls(){ ./lab ssh $1 -- sh -c "ok=0; bad=0; for i in \$(seq 1 30); do c=\$(curl -s -o /dev/null -w '%{http_code}' --max-time 1 http://$VIP/); [ \"\$c\" = 200 ] && ok=\$((ok+1)) || bad=\$((bad+1)); done; echo \"200=\$ok 실패=\$bad\""; }
pods(){ $K get pod -l app=myweb -o jsonpath='{range .items[*]}{.status.podIP} {end}' | tr ' ' '\n' | sort | paste -sd' ' -; }
SVC=$(./lab ssh 1 -- sudo sh -c 'iptables-save -t nat 2>/dev/null' | grep -- "-A KUBE-SERVICES -d $VIP/32" | grep -oE 'KUBE-SVC-[A-Z0-9]+' | head -1)
echo "# E25 kube-proxy 가 없는 동안의 규칙 ($(date '+%F %T %Z')), myweb ClusterIP $VIP ($SVC)"
echo; echo "## 1. 시작 전"
echo "$(ts) myweb 파드 IP: $(pods)"
echo "$(ts) worker1 규칙의 엔드포인트: $(sep 1)"
echo "$(ts) master  규칙의 엔드포인트: $(sep master)"
echo; echo "## 2. worker1 의 kube-proxy 만 없애기 (DaemonSet 에 nodeAffinity NotIn k8s-worker1)"
$K -n kube-system patch ds kube-proxy --type merge -p '{"spec":{"template":{"spec":{"affinity":{"nodeAffinity":{"requiredDuringSchedulingIgnoredDuringExecution":{"nodeSelectorTerms":[{"matchExpressions":[{"key":"kubernetes.io/hostname","operator":"NotIn","values":["k8s-worker1"]}]}]}}}}}}}'
$K -n kube-system rollout status ds/kube-proxy --timeout=180s
echo "$(ts) kube-proxy 파드: $($K -n kube-system get pod -l k8s-app=kube-proxy -o jsonpath='{range .items[*]}{.spec.nodeName} {end}')"
echo "$(ts) worker1 규칙의 엔드포인트(kube-proxy 없음): $(sep 1)"
echo; echo "## 3. myweb 5 → 2"
$K scale deploy myweb --replicas=2 >/dev/null; $K rollout status deploy/myweb --timeout=60s >/dev/null; sleep 5
echo "$(ts) myweb 파드 IP: $(pods)"
echo "$(ts) master  규칙: $(sep master)"
echo "$(ts) worker1 규칙: $(sep 1)"
echo "$(ts) master  → ClusterIP curl 30번: $(curls master)"
echo "$(ts) worker1 → ClusterIP curl 30번: $(curls 1)"
echo; echo "## 4. myweb 2 → 5"
$K scale deploy myweb --replicas=5 >/dev/null; $K rollout status deploy/myweb --timeout=90s >/dev/null; sleep 5
echo "$(ts) myweb 파드 IP: $(pods)"
echo "$(ts) master  규칙: $(sep master)"
echo "$(ts) worker1 규칙: $(sep 1)"
echo "$(ts) worker1 → ClusterIP curl 30번: $(curls 1)"
echo; echo "## 5. 되돌리기 (affinity 제거 → worker1 에 kube-proxy 다시 뜸)"
$K -n kube-system patch ds kube-proxy --type json -p '[{"op":"remove","path":"/spec/template/spec/affinity"}]'
$K -n kube-system rollout status ds/kube-proxy --timeout=180s
sleep 5
echo "$(ts) kube-proxy 파드: $($K -n kube-system get pod -l k8s-app=kube-proxy -o jsonpath='{range .items[*]}{.spec.nodeName} {end}')"
echo "$(ts) worker1 규칙: $(sep 1)"
echo "$(ts) worker1 → ClusterIP curl 30번: $(curls 1)"
echo "$(ts) DaemonSet affinity: $($K -n kube-system get ds kube-proxy -o jsonpath='{.spec.template.spec.affinity}')(비어 있으면 원래대로)"
