#!/usr/bin/env bash
# rollout status 가 끝난 뒤 옛 파드가 다 내려갈 때까지 기다리려면: kubectl wait 로 status.terminatingReplicas 가 0 이 되기를 기다려 본다 (Mac 에서 실행)
# 실습 저장소 루트에서 실행한다(./lab kubectl). 네임스페이스 blog-62 만 쓰고 지운다.
# 옛 파드가 오래 종료 중이도록 컨테이너가 SIGTERM 을 받으면 15초 뒤 exit 0 으로 끝나게 했다(terminationGracePeriodSeconds 30 안).
K="./lab kubectl"; NS=blog-62; D=wait-demo
now(){ perl -MTime::HiRes=time -e 'printf "%.1f", time'; }
echo "# 62 rollout status 뒤 terminatingReplicas 기다리기 ($(date '+%F %T %Z'))"
$K create ns $NS >/dev/null 2>&1 || $K get ns $NS >/dev/null
cat <<Y | $K apply -n $NS -f - >/dev/null
apiVersion: apps/v1
kind: Deployment
metadata: {name: $D}
spec:
  replicas: 2
  selector: {matchLabels: {app: $D}}
  template:
    metadata: {labels: {app: $D}}
    spec:
      containers:
      - name: app
        image: busybox:1.37
        env: [{name: V, value: "1"}]
        command: [sh, -c, 'trap "sleep 15; exit 0" TERM; while true; do sleep 1; done']
Y
$K rollout status deploy/$D -n $NS --timeout=120s >/dev/null
echo; echo "## kubectl set env deploy/$D V=2 → kubectl rollout status"
$K set env deploy/$D -n $NS V=2 >/dev/null
T0=$(now); $K rollout status deploy/$D -n $NS --timeout=120s | tail -1 | sed 's/^/  /'
echo "  +$(perl -e "printf '%.1f', $(now)-$T0")s rollout status 끝남, terminatingReplicas=$($K get deploy $D -n $NS -o jsonpath='{.status.terminatingReplicas}')"
$K get pod -n $NS -l app=$D -o custom-columns='  POD:.metadata.name,V:.spec.containers[0].env[0].value,PHASE:.status.phase,DELETION:.metadata.deletionTimestamp' | sed 's/^/  /'
echo; echo "## kubectl wait --for=jsonpath='{.status.terminatingReplicas}'=0"
$K wait deploy/$D -n $NS --for=jsonpath='{.status.terminatingReplicas}'=0 --timeout=60s 2>&1 | sed 's/^/  /'; rc=${PIPESTATUS[0]}
echo "  exit=$rc  +$(perl -e "printf '%.1f', $(now)-$T0")s"
$K get pod -n $NS -l app=$D -o custom-columns='  POD:.metadata.name,V:.spec.containers[0].env[0].value,PHASE:.status.phase,DELETION:.metadata.deletionTimestamp' | sed 's/^/  /'
$K delete ns $NS --wait=false >/dev/null
echo; echo "  네임스페이스 $NS 삭제 요청"
