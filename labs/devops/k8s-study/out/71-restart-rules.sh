#!/usr/bin/env bash
# 보통 컨테이너에 붙은 restartPolicy / restartPolicyRules (KEP-5307, 1.35 beta)는 사이드카와 무엇이 다른가 (Mac 에서 실행)
# 네임스페이스 why-sidecar만 쓴다. 파드 restartPolicy는 모두 Never.
#   rules-pod : app이 처음 두 번은 exit 42, 세 번째 exit 0. restartPolicy: Never + restartPolicyRules(42 → Restart)
#   always-pod: 보통 컨테이너 helper에 restartPolicy: Always (3초마다 exit 0), app은 10초 뒤 exit 0
cd "$(dirname "$0")/../../.."   # 실습 저장소 루트
K="./lab kubectl"; NS=why-sidecar
$K create ns $NS >/dev/null 2>&1 || true
echo "# 컨테이너 수준 restartPolicy와 restartPolicyRules ($(date '+%F %T %Z'))"
cat <<'Y' | $K apply -n $NS -f - >/dev/null || exit 1
apiVersion: v1
kind: Pod
metadata: {name: rules-pod}
spec:
  restartPolicy: Never
  volumes: [{name: w, emptyDir: {}}]
  containers:
  - name: app
    image: busybox:1.37
    volumeMounts: [{name: w, mountPath: /w}]
    command: [sh, -c, 'n=$(cat /w/n 2>/dev/null || echo 0); n=$((n+1)); echo $n > /w/n; echo "run $n"; if [ $n -lt 3 ]; then echo exit-42; exit 42; fi; echo exit-0']
    restartPolicy: Never
    restartPolicyRules:
    - action: Restart
      exitCodes: {operator: In, values: [42]}
---
apiVersion: v1
kind: Pod
metadata: {name: always-pod}
spec:
  restartPolicy: Never
  containers:
  - {name: app, image: busybox:1.37, command: [sh, -c, 'sleep 10; echo app exit-0']}
  - {name: helper, image: busybox:1.37, restartPolicy: Always, command: [sh, -c, 'sleep 3; echo helper exit-0']}
Y
st(){ $K get pod $1 -n $NS -o json | jq -r '
  "    phase=\(.status.phase)",
  ((.status.containerStatuses // [])[]
  | "    \(.name): restartCount=\(.restartCount) state=\(.state | keys[0])\(if .state.waiting.reason then "(\(.state.waiting.reason))" elif .state.terminated then "(exit=\(.state.terminated.exitCode))" else "" end) lastExit=\(.lastState.terminated.exitCode // "-")")'; }
echo; echo "## 적용된 스펙 확인 (API 서버가 필드를 받아들였나)"
$K get pod rules-pod -n $NS -o jsonpath='  rules-pod app: restartPolicy={.spec.containers[0].restartPolicy} restartPolicyRules={.spec.containers[0].restartPolicyRules}{"\n"}'
$K get pod always-pod -n $NS -o jsonpath='  always-pod helper: restartPolicy={.spec.containers[1].restartPolicy}{"\n"}'
for t in 30 75; do
  sleep $(( t == 30 ? 30 : 45 ))
  echo; echo "## 생성 후 약 ${t}초"
  for p in rules-pod always-pod; do echo "  $p"; st $p; done
done
echo; echo "## rules-pod 로그 (마지막 실행)"; $K logs rules-pod -n $NS | sed 's/^/  /'
echo; echo "## kubectl get pod"
$K get pod rules-pod always-pod -n $NS | sed 's/^/  /'
$K delete pod rules-pod always-pod -n $NS --wait=false >/dev/null
