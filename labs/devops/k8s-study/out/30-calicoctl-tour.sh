#!/usr/bin/env bash
# calicoctl 로 Calico 상태 보기 (마스터 VM 안에서 실행: ./lab ssh master -- bash -s < 이 파일)
export DATASTORE_TYPE=kubernetes KUBECONFIG=$HOME/.kube/config
c(){ echo; echo "master\$ calicoctl $*"; calicoctl "$@" 2>&1; }
echo "# E10 calicoctl 둘러보기 ($(date '+%F %T %Z'))"
c version
echo; echo "master\$ sudo calicoctl node status   (이 노드의 BIRD 에 직접 물어봄)"
sudo DATASTORE_TYPE=kubernetes KUBECONFIG=/etc/kubernetes/admin.conf calicoctl node status 2>&1
c get nodes -o wide
c get ippool -o wide
c get bgpconfig
c get bgppeer
c ipam show
c ipam show --show-blocks
c ipam check
c get workloadendpoints -n default -o wide
echo; echo "master\$ calicoctl get felixconfiguration default -o yaml | grep -A12 '^spec:'"
calicoctl get felixconfiguration default -o yaml 2>&1 | grep -A12 '^spec:'
echo; echo "## 같은 IPPool 을 kubectl 과 calicoctl 로 볼 때 apiVersion"
echo "kubectl   : $(kubectl get ippools.crd.projectcalico.org default-ipv4-ippool -o jsonpath='{.apiVersion}')"
echo "calicoctl : $(calicoctl get ippool default-ipv4-ippool -o yaml 2>/dev/null | awk '/^apiVersion/{print $2}')"
echo "projectcalico.org/v3 API 가 쿠버네티스에 등록돼 있나: $(kubectl api-resources --api-group=projectcalico.org --no-headers 2>/dev/null | wc -l)개"
