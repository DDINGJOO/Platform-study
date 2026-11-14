#!/usr/bin/env bash
# 36편: 같은 요청이 보낸 사용자에 따라 어느 FlowSchema·우선순위 수준(APF)으로 분류되는지 응답 헤더로 확인하고,
# kubeadm 이 API 서버 매니페스트를 만들 때 쓴 ClusterConfiguration 을 본다. 조회(GET)만 한다.
# 실습 저장소 루트(./lab 이 있는 곳)에서 bash <이 스크립트> 로 실행
set -u
K="./lab kubectl"
echo "# 요청 분류(APF)와 kubeadm ClusterConfiguration ($(date '+%F %T %Z'))"
MAP=$($K get flowschema,prioritylevelconfiguration -o jsonpath='{range .items[*]}{.metadata.uid} {.kind}/{.metadata.name}{"\n"}{end}')
name(){ echo "$MAP" | awk -v u="$1" '$1==u{print $2}'; }
show(){
  desc=$1; shift
  hdr=$("$@" -v=8 2>&1 | grep -i 'x-kubernetes-pf-\(flowschema\|prioritylevel\)-uid')
  code=$("$@" -v=6 2>&1 | grep -o 'status="[0-9][^"]*"' | head -1)
  fs=$(name "$(echo "$hdr" | grep -i flowschema | awk '{print $2}')")
  pl=$(name "$(echo "$hdr" | grep -i prioritylevel | awk '{print $2}')")
  echo "  $desc  $code"
  echo "      → ${fs/FlowSchema\//FlowSchema }  |  ${pl/PriorityLevelConfiguration\//우선순위 수준 }"
}
echo; echo "## 1. 같은 GET 이라도 누가 보내느냐에 따라 서는 줄이 다르다 (응답 헤더 X-Kubernetes-PF-*-UID 를 이름으로 바꿈)"
show "관리자 kubeconfig: GET pods" $K get pods -n default
show "관리자 kubeconfig: GET /readyz" $K get --raw /readyz
show "--as=system:kube-scheduler: GET pods" $K get pods -n default --as=system:kube-scheduler
show "--as=system:node:k8s-worker1 (그룹 system:nodes): GET node" $K get node k8s-worker1 --as=system:node:k8s-worker1 --as-group=system:nodes
show "--as=system:serviceaccount:monitoring:default: GET pods" $K get pods -n default --as=system:serviceaccount:monitoring:default
echo; echo "## 2. 관리자 kubeconfig 의 사용자와 그룹"
$K auth whoami | sed 's/^/  /'
echo; echo "## 3. kubeadm 이 매니페스트를 만들 때 쓴 ClusterConfiguration (kube-system/kubeadm-config)"
$K -n kube-system get cm kubeadm-config -o jsonpath='{.data.ClusterConfiguration}' | sed 's/^/  /'
