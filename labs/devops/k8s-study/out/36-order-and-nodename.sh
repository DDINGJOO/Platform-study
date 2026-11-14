#!/usr/bin/env bash
# 실습 저장소의 shared/components/22-order-and-nodename.sh 를 옮긴 것. 실습 저장소 루트에서 실행한다.
# ① 형식도 틀리고 쿼터도 넘긴 파드는 422(검증)와 403(쿼터 어드미션) 중 무엇을 받나 ② toleration 없이 spec.nodeName: k8s-master 만 적은 파드는 마스터에서 뜨나 (Mac 에서 실행)
# 네임스페이스 w36-order 만 쓰고 지운다.
cd "$(dirname "$0")/../.."   # 실습 저장소 루트
K="./lab kubectl"; ts(){ date '+%T'; }; NS=w36-order
code(){ grep -o -E 'Response" verb="POST" url="[^"]*" status="[^"]*"' | sed -E 's/.*url="https?:\/\/[^/]+([^"?]*)[^"]*" status="([^"]*)"/    POST \1 → \2/'; }
echo "# 검증과 어드미션의 순서, nodeName 과 NoSchedule taint ($(date '+%F %T %Z'))"
$K create ns $NS >/dev/null
$K -n $NS create quota zero-pods --hard=pods=0 >/dev/null
echo; echo "## 0. ResourceQuota zero-pods (pods=0)"; $K -n $NS get quota zero-pods --no-headers | sed 's/^/  /'
printf 'apiVersion: v1\nkind: Pod\nmetadata: {name: ok-pod}\nspec: {containers: [{name: c, image: registry.k8s.io/pause:3.10.2}]}\n' > /tmp/ok.$$.yaml
printf 'apiVersion: v1\nkind: Pod\nmetadata: {name: bad-pod}\nspec: {containers: [{name: Bad_Name, image: registry.k8s.io/pause:3.10.2}]}\n' > /tmp/bad.$$.yaml
echo; echo "## 1. 형식이 맞는 파드 (쿼터만 넘김)"
$K -n $NS create -f /tmp/ok.$$.yaml -v=6 2>&1 | tee /tmp/o.$$ | code; grep -E '^Error|^error' /tmp/o.$$ | sed 's/^/    /' | cut -c1-220
echo; echo "## 2. 컨테이너 이름이 틀린 파드 (형식도 틀리고 쿼터도 넘김)"
$K -n $NS create -f /tmp/bad.$$.yaml -v=6 2>&1 | tee /tmp/o.$$ | code; grep -E '^(The Pod|Error|error)' /tmp/o.$$ | sed 's/^/    /' | cut -c1-220
rm -f /tmp/ok.$$.yaml /tmp/bad.$$.yaml /tmp/o.$$
$K -n $NS delete quota zero-pods >/dev/null
echo; echo "## 3. toleration 없이 spec.nodeName: k8s-master 만 적은 파드"
echo "  마스터 taint: $($K get node k8s-master -o jsonpath='{range .spec.taints[*]}{.key}:{.effect} {end}')"
cat <<Y | $K -n $NS apply -f - >/dev/null
apiVersion: v1
kind: Pod
metadata: {name: pinned-master}
spec: {nodeName: k8s-master, terminationGracePeriodSeconds: 0, containers: [{name: c, image: registry.k8s.io/pause:3.10.2}]}
Y
sleep 8
$K -n $NS get pod pinned-master -o wide --no-headers | awk '{print "  "$1, $3, "NODE="$7}'
echo "  tolerations: $($K -n $NS get pod pinned-master -o jsonpath='{range .spec.tolerations[*]}{.key}:{.effect}({.tolerationSeconds}s) {end}')"
echo "  이벤트(보고한 컴포넌트, 이유):"; $K -n $NS get events --field-selector involvedObject.name=pinned-master -o jsonpath='{range .items[*]}    {.reportingComponent} {.reason}{"\n"}{end}'
echo; echo "## 4. 정리"; $K delete ns $NS --wait=true >/dev/null; echo "  $(ts) 네임스페이스 $NS 삭제"
