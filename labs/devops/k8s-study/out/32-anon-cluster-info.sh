#!/usr/bin/env bash
# 32편 보강: 공개 경로 네 곳 말고 익명 사용자가 읽을 수 있는 것 (kubeadm 의 cluster-info). 조회만 한다.
# 실습 저장소 루트(./lab 이 있는 곳)에서 bash <이 스크립트> 로 실행
set -u
K="./lab kubectl"
echo "# 32편 보강: kubeadm 이 익명 사용자에게 열어 둔 cluster-info ($(date '+%F %T %Z'), Mac 에서 실습 저장소 루트로 bash 32-anon-cluster-info.sh 실행, 조회만)"
echo; echo "## 1. kube-public 네임스페이스의 Role 과 RoleBinding"
echo "mac\$ kubectl -n kube-public get rolebinding kubeadm:bootstrap-signer-clusterinfo -o wide"
$K -n kube-public get rolebinding kubeadm:bootstrap-signer-clusterinfo -o wide
echo "mac\$ kubectl -n kube-public get role kubeadm:bootstrap-signer-clusterinfo -o jsonpath='{.rules}'"
echo "  $($K -n kube-public get role kubeadm:bootstrap-signer-clusterinfo -o jsonpath='{.rules}')"
echo; echo "## 2. worker1 에서 자격 없이 (CA 확인은 함)"
./lab ssh 1 -- bash -s <<'R'
u=https://192.168.104.1:6443/api/v1/namespaces/kube-public/configmaps
c=$(curl -sS --cacert /etc/kubernetes/pki/ca.crt -o /tmp/ci.json -w '%{http_code}' $u/cluster-info)
echo "worker1\$ curl --cacert /etc/kubernetes/pki/ca.crt $u/cluster-info"
echo "  HTTP $c | $(python3 -c 'import json;d=json.load(open("/tmp/ci.json"));print(d.get("kind"), d["metadata"]["name"], "data 키:", sorted(d.get("data",{}).keys()))')"
c=$(curl -sS --cacert /etc/kubernetes/pki/ca.crt -o /tmp/ci.json -w '%{http_code}' $u)
echo "worker1\$ curl --cacert /etc/kubernetes/pki/ca.crt $u   (같은 네임스페이스의 ConfigMap 목록)"
echo "  HTTP $c | $(python3 -c 'import json;print(json.load(open("/tmp/ci.json")).get("message"))')"
rm -f /tmp/ci.json
R
