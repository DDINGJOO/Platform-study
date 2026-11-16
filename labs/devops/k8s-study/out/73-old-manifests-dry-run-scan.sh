#!/usr/bin/env bash
# 확인: 업그레이드 전에 매니페스트의 옛 apiVersion을 서버 dry-run으로 걸러 내고, 제거 예정 없는 deprecated API(v1 Endpoints)의 경고와 메트릭이 지금 어떻게 남아 있는지 본다. 객체는 만들지 않는다 (Mac 에서 실행)
# 실행: bash labs/devops/k8s-study/out/73-old-manifests-dry-run-scan.sh 2>&1 | tee labs/devops/k8s-study/out/73-old-manifests-dry-run-scan.txt  (cwd 는 블로그 저장소)
set -u
cd /Users/dding/orca/workspaces/k8s/tang
K="./lab kubectl"; NS=blog-75
M=$(mktemp)

echo "# 75 업그레이드 전 매니페스트 점검과 deprecated 메트릭 ($(date '+%F %T %Z'))"
$K create namespace $NS --dry-run=client -o yaml | $K apply -f - >/dev/null

cat > "$M" <<Y
apiVersion: apps/v1
kind: Deployment
metadata: {name: new-deploy, namespace: $NS}
spec:
  selector: {matchLabels: {app: scan}}
  template:
    metadata: {labels: {app: scan}}
    spec: {containers: [{name: c, image: nginx:1.27-alpine}]}
---
apiVersion: extensions/v1beta1
kind: Deployment
metadata: {name: old-deploy, namespace: $NS}
spec:
  template:
    metadata: {labels: {app: scan}}
    spec: {containers: [{name: c, image: nginx:1.27-alpine}]}
---
apiVersion: policy/v1beta1
kind: PodDisruptionBudget
metadata: {name: old-pdb, namespace: $NS}
spec:
  minAvailable: 1
  selector: {matchLabels: {app: scan}}
---
apiVersion: autoscaling/v2beta2
kind: HorizontalPodAutoscaler
metadata: {name: old-hpa, namespace: $NS}
spec:
  scaleTargetRef: {apiVersion: apps/v1, kind: Deployment, name: new-deploy}
  minReplicas: 1
  maxReplicas: 3
---
apiVersion: v1
kind: Endpoints
metadata: {name: legacy-ep, namespace: $NS}
---
apiVersion: discovery.k8s.io/v1
kind: EndpointSlice
metadata: {name: new-eps, namespace: $NS}
addressType: IPv4
endpoints: []
Y

echo; echo "## 1. 매니페스트 6개(지금 버전 2, 서빙이 끝난 옛 버전 3, deprecated GA 1)를 한 번에 서버 dry-run"
grep -E '^(apiVersion|kind):' "$M" | paste - - | sed 's/^/  /'
echo "  \$ kubectl apply --dry-run=server -f manifests.yaml"
$K apply --dry-run=server -f "$M" 2>&1 | sed "s#$M#manifests.yaml#g; s/^/    /"
echo "  종료 코드: ${PIPESTATUS[0]}"

echo; echo "## 2. 각 groupVersion을 discovery에 직접 물으면"
for gv in apps/v1 extensions/v1beta1 policy/v1beta1 autoscaling/v2beta2 discovery.k8s.io/v1; do
  printf '  GET /apis/%-22s → %s\n' "$gv" "$($K get --raw /apis/$gv >/dev/null 2>&1 && echo 서빙 중 || echo "$($K get --raw /apis/$gv 2>&1 | head -1 | sed 's/^Error from server //')")"
done

echo; echo "## 3. deprecated GA(v1 Endpoints)만 따로: 경고는 성공 응답에 붙고, --warnings-as-errors면 실패 코드"
printf 'apiVersion: v1\nkind: Endpoints\nmetadata: {name: legacy-ep, namespace: %s}\n' $NS > "$M.ep"
echo "  \$ kubectl apply --dry-run=server -f endpoints.yaml"
$K apply --dry-run=server -f "$M.ep" 2>&1 | sed 's/^/    /'; echo "    종료 코드: ${PIPESTATUS[0]}"
echo "  \$ kubectl apply --dry-run=server -f endpoints.yaml --warnings-as-errors"
$K apply --dry-run=server -f "$M.ep" --warnings-as-errors 2>&1 | sed 's/^/    /'; echo "    종료 코드: ${PIPESTATUS[0]}"

echo; echo "## 4. 지금 apiserver_requested_deprecated_apis와 API 서버 프로세스 시작 시각"
$K get --raw /metrics | grep -E '^apiserver_requested_deprecated_apis' | sed 's/^/  /'
$K get --raw /metrics | awk '/^process_start_time_seconds /{print $2}' | python3 -c 'import sys,datetime; t=float(sys.stdin.read()); print("  kube-apiserver process_start_time_seconds →", datetime.datetime.fromtimestamp(t).strftime("%F %T"), "(로컬 시각)")'
echo "  kube-apiserver 컨테이너 restartCount: $($K -n kube-system get pod kube-apiserver-k8s-master -o jsonpath='{.status.containerStatuses[0].restartCount}')"
echo "  widgets CRD(앞 실험에서 지움) 존재 여부: $($K get crd widgets.why-api.example.com 2>&1 | grep -c NotFound | sed 's/1/NotFound/')"
echo "  API 서버 --audit-policy-file 플래그 수: $($K -n kube-system get pod kube-apiserver-k8s-master -o jsonpath='{.spec.containers[0].command}' | grep -o audit-policy-file | wc -l | tr -d ' ')"

echo; echo "## 5. 정리"
rm -f "$M" "$M.ep"
$K delete namespace $NS --wait=true 2>&1 | sed 's/^/  /'
