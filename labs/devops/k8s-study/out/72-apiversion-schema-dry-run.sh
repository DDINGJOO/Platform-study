#!/usr/bin/env bash
# 확인: 같은 kind(HorizontalPodAutoscaler)라도 apiVersion이 받아 주는 필드를 정하는지, api-versions·api-resources·explain이 각각 무엇을 보여 주는지 본다. 서버 dry-run만 쓰고 객체는 만들지 않는다 (Mac 에서 실행)
# 실행: bash labs/devops/k8s-study/out/72-apiversion-schema-dry-run.sh 2>&1 | tee labs/devops/k8s-study/out/72-apiversion-schema-dry-run.txt  (cwd 는 블로그 저장소)
set -u
cd /Users/dding/orca/workspaces/k8s/tang
K="./lab kubectl"; NS=blog-72

echo "# 72 apiVersion이 고르는 스키마 ($(date '+%F %T %Z'))"
$K create namespace $NS --dry-run=client -o yaml | $K apply -f - >/dev/null

echo; echo "## 1. kubectl api-versions: 서버가 지금 서빙하는 group/version 목록 (전체 개수와 autoscaling 줄)"
echo "  전체 $($K api-versions | wc -l | tr -d ' ')줄"
$K api-versions | grep -E '^autoscaling/' | sed 's/^/  /'

echo; echo "## 2. kubectl api-resources: kind 하나에 preferred 버전 하나만 보여 준다"
$K api-resources --api-group=autoscaling | sed 's/^/  /'

echo; echo "## 3. kubectl explain: 같은 kind의 spec 필드가 버전마다 다르다"
for v in autoscaling/v1 autoscaling/v2; do
  echo "  \$ kubectl explain horizontalpodautoscalers.spec --api-version=$v"
  $K explain horizontalpodautoscalers.spec --api-version=$v | awk '/^FIELDS:/{f=1;next} f && /^  [a-zA-Z]/{print "    "$1}'
done

body(){ cat <<Y
apiVersion: $1
kind: HorizontalPodAutoscaler
metadata: {name: web, namespace: $NS}
spec:
  scaleTargetRef: {apiVersion: apps/v1, kind: Deployment, name: web}
  minReplicas: 1
  maxReplicas: 3
$2
Y
}
V2SPEC='  metrics:
  - type: Resource
    resource: {name: cpu, target: {type: Utilization, averageUtilization: 50}}'
V1SPEC='  targetCPUUtilizationPercentage: 50'

echo; echo "## 4. v2 모양 본문(spec.metrics)을 apiVersion만 바꿔 서버 dry-run"
for v in autoscaling/v2 autoscaling/v1; do
  echo "  apiVersion: $v"
  body $v "$V2SPEC" | $K apply --dry-run=server -f - 2>&1 | sed 's/^/    → /'
done

echo; echo "## 5. v1 모양 본문(spec.targetCPUUtilizationPercentage)을 apiVersion만 바꿔 서버 dry-run"
for v in autoscaling/v1 autoscaling/v2; do
  echo "  apiVersion: $v"
  body $v "$V1SPEC" | $K apply --dry-run=server -f - 2>&1 | sed 's/^/    → /'
done

echo; echo "## 6. 정리"
echo "  HPA 남은 수: $($K -n $NS get hpa --no-headers 2>/dev/null | wc -l | tr -d ' ')"
$K delete namespace $NS --wait=true 2>&1 | sed 's/^/  /'
