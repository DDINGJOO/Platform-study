#!/usr/bin/env bash
# 32편: Node 인가자와 NodeRestriction 어드미션이 kubelet 을 자기 노드로 묶는 모습.
# worker1 의 kubelet 자격(/etc/kubernetes/kubelet.conf)으로 직접 요청한다. 쓰기 요청은 모두 --dry-run=server 라 저장되지 않는다.
# w32 네임스페이스 안에서만 만들고 끝에 네임스페이스째 지운다. 노드 객체는 건드리지 않는다.
# 실습 저장소 루트(./lab 이 있는 곳)에서 bash <이 스크립트> 로 실행
set -u
K="./lab kubectl"
echo "# 32편: Node 인가자와 NodeRestriction ($(date '+%F %T %Z'), Mac 에서 실습 저장소 루트로 bash 32-node-authz.sh 실행, w32 네임스페이스만 쓰고 지움)"

echo; echo "## 1. 준비: Secret 두 개와, 각 Secret 을 쓰는 파드를 worker1·worker2 에 하나씩"
$K create namespace w32
$K -n w32 create secret generic s-w1 --from-literal=k=v1
$K -n w32 create secret generic s-w2 --from-literal=k=v2
for n in 1 2; do
cat <<Y | $K apply -f -
apiVersion: v1
kind: Pod
metadata: {name: p-w$n, namespace: w32}
spec:
  nodeName: k8s-worker$n
  containers: [{name: c, image: nginx:1.25.1-alpine, volumeMounts: [{name: s, mountPath: /s}]}]
  volumes: [{name: s, secret: {secretName: s-w$n}}]
Y
done
$K -n w32 wait --for=condition=Ready pod/p-w1 pod/p-w2 --timeout=90s
$K -n w32 get pods -o wide | awk '{print $1, $3, $7}' | column -t

echo; echo "## 2. worker1 의 kubelet 자격으로 읽기 (Node 인가자)"
./lab ssh 1 -- sudo bash -s <<'R'
k() { kubectl --kubeconfig /etc/kubernetes/kubelet.conf "$@" 2>&1; }
echo "worker1\$ alias k='kubectl --kubeconfig /etc/kubernetes/kubelet.conf'"
echo "worker1\$ k auth whoami"; k auth whoami -o jsonpath='Username {.status.userInfo.username}{"\n"}'
for args in "-n w32 get secret s-w1 -o name" "-n w32 get secret s-w2 -o name" \
            "get node k8s-worker1 -o name" "get node k8s-worker2 -o name" \
            "-n w32 get pod p-w1 -o name" "-n w32 get pod p-w2 -o name" \
            "-n w32 get pods --field-selector spec.nodeName=k8s-worker1 -o name" "-n w32 get pods -o name"; do
  echo "worker1\$ k $args"; k $args
done
R

echo; echo "## 3. worker1 의 kubelet 자격으로 쓰기 (인가는 통과하는가, 어드미션은 통과하는가). 모두 --dry-run=server"
./lab ssh 1 -- sudo bash -s <<'R'
k() { kubectl --kubeconfig /etc/kubernetes/kubelet.conf "$@" 2>&1; }
echo "worker1\$ k auth can-i create pods -n w32";  k auth can-i create pods -n w32
echo "worker1\$ k auth can-i delete pods -n w32";  k auth can-i delete pods -n w32
echo "worker1\$ k -n w32 run hijack --image=nginx:1.25.1-alpine --dry-run=server   # 미러 파드가 아닌 보통 파드를 만들려 하면"
k -n w32 run hijack --image=nginx:1.25.1-alpine --dry-run=server
echo "worker1\$ k -n w32 delete pod p-w2 --dry-run=server   # worker2 에 배정된 파드를 지우려 하면"
k -n w32 delete pod p-w2 --dry-run=server
echo "worker1\$ k -n w32 delete pod p-w1 --dry-run=server   # 자기 노드(worker1)에 배정된 파드는"
k -n w32 delete pod p-w1 --dry-run=server
R

echo; echo "## 4. 참고: 기본 ClusterRoleBinding system:node 의 subjects (kubelet 권한은 이 바인딩이 아니라 Node 인가자가 준다)"
echo "mac\$ kubectl get clusterrolebinding system:node -o jsonpath='{.subjects}'"
echo "  [$($K get clusterrolebinding system:node -o jsonpath='{.subjects}')]"

echo; echo "## 5. 정리"
$K delete namespace w32 --wait=true
