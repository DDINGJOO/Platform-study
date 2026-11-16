#!/usr/bin/env bash
# kind · apiVersion: 같은 종류가 어느 그룹/버전에 있고, 옛 apiVersion 을 쓰면 어떻게 되나 (Mac 에서 실행)
cd "$(dirname "$0")/../.."
K="./lab kubectl"
echo "# 06 kind · apiVersion ($(date '+%F %T %Z'))"
echo; echo "## 자주 쓰는 종류의 APIVERSION"
$K api-resources | awk 'NR==1 || $1~/^(pods|services|configmaps|deployments|replicasets|cronjobs|ingresses|horizontalpodautoscalers)$/'
echo; echo "## 그룹마다 서빙 중인 버전 (autoscaling 은 v1·v2 둘 다)"
$K api-versions | grep -E '^(v1|apps/|batch/|autoscaling/|networking.k8s.io/)'
echo; echo "## 요청 경로: core 그룹은 /api/v1, 나머지는 /apis/<그룹>/<버전>"
$K get pods -n ch05 -v=6 2>&1 | grep -oE 'url="https://[^"]+' | sed 's#url="https://[^/]*##' | head -1
$K get deploy -n ch05 -v=6 2>&1 | grep -oE 'url="https://[^"]+' | sed 's#url="https://[^/]*##' | head -1
echo; echo "## api-resources 는 고정 목록이 아니다: 그룹별 종류 수 (Calico 가 설치한 CRD 그룹이 가장 많다)"
$K api-resources --no-headers | awk '{print $(NF-2)}' | sort | uniq -c | sort -rn | head -6
echo; echo "## 옛 apiVersion 으로 Deployment 를 보내면 (extensions/v1beta1)"
cat <<'Y' | $K apply --dry-run=server -f - 2>&1 | sed 's/^/  /'
apiVersion: extensions/v1beta1
kind: Deployment
metadata: {name: old, namespace: ch05}
spec:
  selector: {matchLabels: {app: old}}
  template:
    metadata: {labels: {app: old}}
    spec: {containers: [{name: c, image: nginx:1.27-alpine}]}
Y
