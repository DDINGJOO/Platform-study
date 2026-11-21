#!/usr/bin/env bash
# 명령형으로 Pod·Service 만들기: kubectl run 이 붙이는 라벨, expose 가 고르는 셀렉터, 다른 노드에서도 ClusterIP 가 닿나 (Mac 에서 실행)
cd "$(dirname "$0")/../.."
K="./lab kubectl"; NS=ch05
echo "# 22 kubectl run · expose ($(date '+%F %T %Z'))"
echo; echo "## kubectl run myweb2 --image=nginx:1.25.3-alpine --port=80 --dry-run=client -o yaml"
$K run myweb2 -n $NS --image=nginx:1.25.3-alpine --port=80 --dry-run=client -o yaml | sed 's/^/  /'
$K run myweb2 -n $NS --image=nginx:1.25.3-alpine --port=80 >/dev/null
$K wait pod/myweb2 -n $NS --for=condition=Ready --timeout=120s >/dev/null
echo; echo "## kubectl expose pod myweb2 --name=myweb2-svc --port=8002 --target-port=80 --dry-run=client -o yaml (셀렉터를 어디서 가져오나)"
$K expose pod myweb2 -n $NS --name=myweb2-svc --port=8002 --target-port=80 --dry-run=client -o yaml | sed -n '/^spec:/,$p' | sed 's/^/  /'
$K expose pod myweb2 -n $NS --name=myweb2-svc --port=8002 --target-port=80 >/dev/null
echo; echo "## kubectl get po,svc -o wide"
$K get po,svc -n $NS -o wide | sed 's/^/  /'
PIP=$($K get pod myweb2 -n $NS -o jsonpath='{.status.podIP}'); CIP=$($K get svc myweb2-svc -n $NS -o jsonpath='{.spec.clusterIP}')
for i in $(seq 1 25); do limactl shell k8s-master -- curl -s -m 1 -o /dev/null http://$CIP:8002 && break; sleep 0.2; done
echo; echo "## 노드마다 파드 IP:80 과 ClusterIP:8002 (파드 노드: $($K get pod myweb2 -n $NS -o jsonpath='{.spec.nodeName}'))"
for n in k8s-master k8s-worker1 k8s-worker2 k8s-worker3; do
  a=$(limactl shell $n -- curl -sS -m 3 http://$PIP:80 2>&1 | grep -o '<title>[^<]*</title>\|curl: ([0-9]*)' | head -1)
  b=$(limactl shell $n -- curl -sS -m 3 http://$CIP:8002 2>&1 | grep -o '<title>[^<]*</title>\|curl: ([0-9]*)' | head -1)
  printf '  %-12s 파드IP → %-34s ClusterIP → %s\n' $n "$a" "$b"
done
echo; echo "## 이름이 다른 파드를 지우면: kubectl delete pod myweb2-pod"
$K delete pod myweb2-pod -n $NS 2>&1 | sed 's/^/  /'
echo; echo "## 실제 이름으로 지우기"
$K delete pod myweb2 -n $NS --wait=false 2>&1 | sed 's/^/  /'; $K delete svc myweb2-svc -n $NS 2>&1 | sed 's/^/  /'
