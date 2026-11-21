#!/usr/bin/env bash
# status 는 손으로 고칠 수 있나: 본 리소스로 status 를 패치하면 / lastProbeTime 은 실제로 찍히나 (Mac 에서 실행)
cd "$(dirname "$0")/../.."
K="./lab kubectl"; NS=ch05
echo "# 31 status 와 lastProbeTime ($(date '+%F %T %Z'))"
$K run st-demo -n $NS --image=busybox:1.37 --command -- sleep 3600 >/dev/null
$K wait pod/st-demo -n $NS --for=condition=Ready --timeout=60s >/dev/null
echo; echo "## conditions 의 lastProbeTime / lastTransitionTime"
$K get pod st-demo -n $NS -o jsonpath='{range .status.conditions[*]}  {.type}: lastProbeTime={.lastProbeTime} lastTransitionTime={.lastTransitionTime}{"\n"}{end}'
echo; echo "## 본 리소스로 status.phase 를 Failed 로 패치 (kubectl edit 로 status 를 고치는 것과 같은 경로)"
$K patch pod st-demo -n $NS --type merge -p '{"status":{"phase":"Failed"}}' 2>&1 | sed 's/^/  /'
echo "  패치 뒤 phase: $($K get pod st-demo -n $NS -o jsonpath='{.status.phase}')"
echo; echo "## status 하위 리소스로 패치 (--subresource=status)"
$K patch pod st-demo -n $NS --subresource=status --type merge -p '{"status":{"conditions":[{"type":"lab/demo","status":"True"}]}}' 2>&1 | sed 's/^/  /'
echo "  패치 뒤 conditions type: $($K get pod st-demo -n $NS -o jsonpath='{.status.conditions[*].type}')"
sleep 12; echo "  12초 뒤 conditions type: $($K get pod st-demo -n $NS -o jsonpath='{.status.conditions[*].type}')"
$K delete pod st-demo -n $NS --grace-period=1 --wait=false >/dev/null
