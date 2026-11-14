#!/usr/bin/env bash
# 스케줄러의 필터 단계가 노드를 왜 걸러냈는지 FailedScheduling 이벤트로 본다 (Mac 에서 실행)
cd "$(dirname "$0")/../.."   # 실습 저장소 루트 (./lab 이 있는 곳)
k(){ ./lab kubectl "$@"; }; ts(){ date '+%T'; }
echo "# E5 스케줄러 필터: 어떤 노드에도 못 들어가는 파드 ($(date '+%F %T %Z'))"
echo "$(ts) 노드마다 할당 가능 CPU: $(k get nodes -o jsonpath='{range .items[*]}{.metadata.name}={.status.allocatable.cpu} {end}')"
cat <<'Y' > /tmp/filter-test.yaml
apiVersion: v1
kind: Pod
metadata: {name: filter-cpu3}
spec:
  containers:
  - name: nginx
    image: nginx:1.25.1-alpine
    resources: {requests: {cpu: "3"}}
---
apiVersion: v1
kind: Pod
metadata: {name: filter-nodeselector}
spec:
  nodeSelector: {disktype: ssd}
  containers:
  - name: nginx
    image: nginx:1.25.1-alpine
Y
echo "$(ts) mac\$ kubectl apply -f filter-test.yaml   (filter-cpu3: CPU 3개 요청 / filter-nodeselector: disktype=ssd 라벨이 있는 노드만)"
sed 's/^/# | /' /tmp/filter-test.yaml
k apply -f /tmp/filter-test.yaml
sleep 12
echo "$(ts) mac\$ kubectl get pods filter-cpu3 filter-nodeselector -o wide"; k get pods filter-cpu3 filter-nodeselector -o wide
for p in filter-cpu3 filter-nodeselector; do
  echo "$(ts) mac\$ kubectl get events --field-selector involvedObject.name=$p -o custom-columns=REASON:.reason,MESSAGE:.message"
  k get events --field-selector involvedObject.name=$p -o 'custom-columns=REASON:.reason,MESSAGE:.message' | cat
done
echo "$(ts) mac\$ kubectl label node k8s-worker2 disktype=ssd   (조건을 맞춰 주면?)"; k label node k8s-worker2 disktype=ssd
sleep 10
echo "$(ts) mac\$ kubectl get pod filter-nodeselector -o wide"; k get pod filter-nodeselector -o wide
k get events --field-selector involvedObject.name=filter-nodeselector -o 'custom-columns=REASON:.reason,MESSAGE:.message' | tail -2
echo "$(ts) 정리"; k delete -f /tmp/filter-test.yaml --wait=false; k label node k8s-worker2 disktype-
