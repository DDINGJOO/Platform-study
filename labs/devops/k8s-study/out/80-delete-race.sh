#!/usr/bin/env bash
# 파드 삭제 때 컨테이너 정지(A)와 엔드포인트 제거(B)가 경쟁하면 요청이 실패하나: Service 로 50ms 마다 curl 하며 파드 하나를 지운다, preStop 없음 vs preStop sleep 5 (Mac 에서 실행)
cd "$(dirname "$0")/../.."
K="./lab kubectl"; NS=ch05
now(){ perl -MPOSIX=strftime -MTime::HiRes=time -e '$t=time; printf "%s.%03d", strftime("%H:%M:%S", localtime $t), ($t-int $t)*1000'; }
echo "# 28 삭제 경쟁 ($(date '+%F %T %Z'))"
run_case(){ # $1 이름, $2 preStop 블록
  D=race-$1
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
      - name: web
        image: nginx:1.27-alpine
$2
---
apiVersion: v1
kind: Service
metadata: {name: $D}
spec: {selector: {app: $D}, ports: [{port: 80}]}
Y
  $K rollout status deploy/$D -n $NS --timeout=120s >/dev/null
  CIP=$($K get svc $D -n $NS -o jsonpath='{.spec.clusterIP}')
  until limactl shell k8s-master -- curl -s -m 1 -o /dev/null http://$CIP/; do sleep 0.2; done
  VICTIM=$($K get pod -n $NS -l app=$D -o jsonpath='{.items[0].metadata.name}')
  echo; echo "## $1: 대상 $VICTIM, ClusterIP $CIP"
  limactl shell k8s-master -- bash -c "end=\$((SECONDS+14)); while [ \$SECONDS -lt \$end ]; do c=\$(curl -s -m 1 -o /dev/null -w '%{http_code}' http://$CIP/ 2>/dev/null); echo \"\$(date +%T.%3N) \${c:-ERR}\"; sleep 0.05; done" > /tmp/ch05-28-$1.log &
  CP=$!
  ( for i in $(seq 1 60); do echo "$(now) $($K get endpointslice -n $NS -l kubernetes.io/service-name=$D -o jsonpath='{range .items[*].endpoints[*]}{.targetRef.name}:r={.conditions.ready},s={.conditions.serving},t={.conditions.terminating} {end}' | sed "s/$D-[a-z0-9]*-//g")"; sleep 0.2; done ) > /tmp/ch05-28-$1-eps.log &
  EP=$!
  sleep 3; echo "  $(now) kubectl delete pod $VICTIM"; $K delete pod $VICTIM -n $NS --wait=false >/dev/null
  wait $CP; kill $EP 2>/dev/null; wait $EP 2>/dev/null
  tot=$(wc -l < /tmp/ch05-28-$1.log); ok=$(grep -c ' 200$' /tmp/ch05-28-$1.log)
  echo "  요청 $tot 번 중 200: $ok, 실패: $((tot-ok))"
  echo "  실패한 요청(시각 결과):"; grep -v ' 200$' /tmp/ch05-28-$1.log | head -8 | sed 's/^/    /'
  echo "  EndpointSlice 변화(바뀔 때만, r=ready s=serving t=terminating):"
  awk '{k=$0; sub(/^[^ ]+ /,"",k); if (k!=last) {print "    "$0; last=k}}' /tmp/ch05-28-$1-eps.log
  rm -f /tmp/ch05-28-$1.log /tmp/ch05-28-$1-eps.log
  $K delete deploy,svc $D -n $NS >/dev/null
}
run_case no-prestop ""
run_case prestop-sleep5 "        lifecycle: {preStop: {sleep: {seconds: 5}}}"
