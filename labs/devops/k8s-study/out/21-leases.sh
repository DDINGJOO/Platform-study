#!/usr/bin/env bash
# 21편 보충: 컨트롤 플레인 구성 요소의 Lease (누가 리더인가, API 서버는 몇 대인가). 조회만 한다 (Mac 에서 실행)
cd "$(dirname "$0")/../.."   # 실습 저장소 루트 (./lab 이 있는 곳)
K="./lab kubectl"
echo "# 21편 보충: kube-system 의 Lease ($(date '+%F %T %Z'))"
echo; echo "## 1. 리더 선출 Lease (kube-controller-manager, kube-scheduler)"
$K -n kube-system get lease kube-controller-manager kube-scheduler -o custom-columns=NAME:.metadata.name,HOLDER:.spec.holderIdentity,DURATION:.spec.leaseDurationSeconds,RENEW:.spec.renewTime
echo; echo "## 2. API 서버 identity Lease (label apiserver.kubernetes.io/identity=kube-apiserver)"
$K -n kube-system get lease -l apiserver.kubernetes.io/identity=kube-apiserver -o custom-columns=NAME:.metadata.name,HOLDER:.spec.holderIdentity,DURATION:.spec.leaseDurationSeconds
echo; echo "## 3. 리더 선출 플래그 (정적 파드 매니페스트의 command)"
for c in kube-controller-manager kube-scheduler; do
  echo "  $c: $($K -n kube-system get pod $c-k8s-master -o jsonpath='{.spec.containers[0].command}' | tr ',' '\n' | grep -o 'leader-elect[^"]*' | paste -sd' ' -)"
done
