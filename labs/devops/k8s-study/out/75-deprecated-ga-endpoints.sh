#!/usr/bin/env bash
# 확인: 1.37에서 기본으로 켜진 내장 API 중 deprecated인 것(v1 Endpoints)이 경고·메트릭으로 어떻게 보이나. 조회만 한다 (Mac 에서 실행)
# 실행: bash shared/why/08-api-versions-deprecation/05-deprecated-ga-endpoints.sh 2>&1 | tee shared/why/08-api-versions-deprecation/05-deprecated-ga-endpoints.txt
set -u
cd /Users/dding/orca/workspaces/k8s/tang
K="./lab kubectl"

echo "# 05 GA인데 deprecated인 v1 Endpoints: 경고와 메트릭 ($(date '+%F %T %Z'))"

echo; echo "## 1. kubectl로 읽기만 해도 경고가 stderr로 나온다"
echo "  \$ kubectl get endpoints -n default kubernetes"
$K get endpoints -n default kubernetes 2>&1 | sed 's/^/    /'
echo "  \$ kubectl get endpointslices -n default -l kubernetes.io/service-name=kubernetes"
$K get endpointslices -n default -l kubernetes.io/service-name=kubernetes 2>&1 | sed 's/^/    /'

echo; echo "## 2. --warnings-as-errors를 주면 같은 조회가 실패 코드로 끝난다"
$K get endpoints -n default kubernetes --warnings-as-errors >/dev/null 2>&1; echo "  종료 코드: $?"

echo; echo "## 3. apiserver_requested_deprecated_apis (값 1 = 이 API 서버 프로세스가 뜬 뒤 한 번이라도 요청됨)"
$K get --raw /metrics | grep -E '^apiserver_requested_deprecated_apis' | sed 's/^/  /'
echo "  → removed_release가 비어 있다: GA는 deprecated여도 제거 예정 릴리스가 없다(Rule #4a)."
echo "  → widgets 줄은 04 실험에서 지운 CRD의 것이다. 이 gauge는 API 서버가 재시작할 때까지 1로 남는다."
echo "    CRD 존재 여부: $($K get crd widgets.why-api.example.com 2>&1 | grep -c NotFound | sed 's/1/NotFound/')"

echo; echo "## 4. 같은 group/version/resource로 apiserver_request_total을 묶어 동사별 요청 수 보기"
$K get --raw /metrics | python3 -c '
import sys,re,collections
dep=set(); tot=collections.Counter(); lines=sys.stdin.readlines()
for l in lines:
    if l.startswith("apiserver_requested_deprecated_apis{"):
        lab=dict(re.findall(r"(\w+)=\"([^\"]*)\"", l)); dep.add((lab["group"],lab["version"],lab["resource"]))
for l in lines:
    if l.startswith("apiserver_request_total{"):
        lab=dict(re.findall(r"(\w+)=\"([^\"]*)\"", l))
        k=(lab.get("group",""),lab.get("version",""),lab.get("resource",""))
        if k in dep: tot[(k,lab["verb"],lab["code"])]+=float(l.rsplit(" ",1)[1])
for (k,verb,code),n in sorted(tot.items()):
    print("  %-30s %-7s code=%s  %d" % ("/".join(x or "core" for x in k), verb, code, n))'
echo "  (누가 불렀는지는 이 메트릭으로 알 수 없다. 클라이언트를 찾으려면 감사 로그의 k8s.io/deprecated annotation이 필요)"
echo "  API 서버 --audit-policy-file 플래그 수: $($K -n kube-system get pod kube-apiserver-k8s-master -o jsonpath='{.spec.containers[0].command}' | grep -o audit-policy-file | wc -l | tr -d ' ')"
