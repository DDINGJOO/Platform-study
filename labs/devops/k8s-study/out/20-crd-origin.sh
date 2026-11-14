#!/usr/bin/env bash
# 20편 보충: CRD 23개가 언제 생겼고 Calico 가 아닌 것은 무엇인가 (Mac 에서 실행, 조회만)
cd "$(dirname "$0")/../.."   # 실습 저장소 루트 (./lab 이 있는 곳)
K="./lab kubectl"
echo "# 20편 보충: CRD 의 그룹과 만든 시각 ($(date '+%F %T %Z'))"
echo; echo "## 1. 그룹별 CRD 개수"
$K get crd -o jsonpath='{range .items[*]}{.spec.group}{"\n"}{end}' | sort | uniq -c
echo; echo "## 2. 만든 시각(creationTimestamp, UTC)별 CRD 개수"
$K get crd -o jsonpath='{range .items[*]}{.metadata.creationTimestamp}{"\n"}{end}' | sort | uniq -c
echo; echo "## 3. Calico 가 아닌 CRD"
$K get crd clusternetworkpolicies.policy.networking.k8s.io -o custom-columns=NAME:.metadata.name,SCOPE:.spec.scope,KIND:.spec.names.kind,CREATED:.metadata.creationTimestamp,BUNDLE:'.metadata.annotations.policy\.networking\.k8s\.io/bundle-version',APPROVED:'.metadata.annotations.api-approved\.kubernetes\.io'
echo; echo "## 4. calico-node DaemonSet 을 만든 시각 (같은 매니페스트로 설치했는지 견주기)"
$K -n kube-system get ds calico-node -o custom-columns=NAME:.metadata.name,CREATED:.metadata.creationTimestamp
