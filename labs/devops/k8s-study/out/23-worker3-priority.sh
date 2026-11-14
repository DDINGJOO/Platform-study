#!/usr/bin/env bash
# 23편 감사 보강: worker3 위 파드의 우선순위와 클러스터의 PriorityClass (Mac 에서 실행, 조회만)
# req-4(우선순위 0)가 선점할 대상이 없던 이유를 보려고 worker3 의 파드 우선순위를 찍는다. 실험 시각(16:28)이 아니라 이 스크립트를 돌린 시각의 상태다.
cd "$(dirname "$0")/../.."   # 실습 저장소 루트 (./lab 이 있는 곳)
K="./lab kubectl"
echo "# 23편 감사 보강: k8s-worker3 파드 우선순위 ($(date '+%F %T %Z'), Mac 에서 ./lab kubectl 로, 조회만)"
$K get pods -A --field-selector spec.nodeName=k8s-worker3 -o custom-columns='NS:.metadata.namespace,NAME:.metadata.name,PRIORITY:.spec.priority,PRIORITYCLASS:.spec.priorityClassName,OWNER:.metadata.ownerReferences[0].kind'
echo; $K get priorityclass
