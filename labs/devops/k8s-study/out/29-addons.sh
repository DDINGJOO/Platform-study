#!/usr/bin/env bash
# 클러스터 Add-on: 본체 바이너리가 아니라 클러스터 위에 파드로 올라가는 구성 요소. 우리 클러스터의 상태 (Mac 에서 실행)
cd "$(dirname "$0")/../.."   # 실습 저장소 루트 (./lab 이 있는 곳)
K="./lab kubectl"
echo "# E18 Add-on 구성 요소 ($(date '+%F %T %Z'))"
echo; echo "## 0. kubeadm 이 'addon' 으로 설치하는 것"
./lab ssh master -- kubeadm init phase addon --help 2>&1 | sed -n '/Available Commands/,/^$/p'
echo; echo "## 1. CNI plugin: Calico (DaemonSet + 컨트롤러)"
$K -n kube-system get ds,deploy -l 'k8s-app in (calico-node,calico-kube-controllers)' -o wide --no-headers | awk '{print $1, $2, $3, $4}'
echo; echo "## 2. CoreDNS (DNS 기반 서비스 디스커버리)"
$K -n kube-system get deploy coredns --no-headers | awk '{print "deploy/coredns READY", $2}'
$K -n kube-system get svc kube-dns --no-headers | awk '{print "svc/kube-dns", $3, $5}'
echo "Corefile:"; $K -n kube-system get cm coredns -o jsonpath='{.data.Corefile}' | sed 's/^/  /' 
echo "파드의 /etc/resolv.conf (myweb):"; $K exec deploy/myweb -- cat /etc/resolv.conf | sed 's/^/  /'
echo "myweb 파드에서 nslookup myweb.default.svc.cluster.local → $($K exec deploy/myweb -- nslookup myweb.default.svc.cluster.local 2>/dev/null | awk '/^Address/{a=$2} END{print a}') (Service myweb ClusterIP $($K get svc myweb -o jsonpath='{.spec.clusterIP}'))"
echo; echo "## 3. Metrics Server"
echo "APIService v1beta1.metrics.k8s.io: $($K get apiservice v1beta1.metrics.k8s.io 2>&1 | tail -1 | cut -c1-90)"
echo "kubectl top node: $($K top node 2>&1 | head -1)"
echo "HPA 목록: $($K get hpa -A --no-headers 2>&1 | head -1)"
echo; echo "## 4. Web UI"
echo "kubernetes-dashboard 네임스페이스: $($K get ns kubernetes-dashboard --no-headers 2>&1 | cut -c1-60)"
echo "Headlamp: $($K get deploy -A --no-headers | grep -i headlamp | awk '{print $1"/"$2, "READY", $3}')"
echo "Portainer: $($K get deploy -A --no-headers | grep -i portainer | awk '{print $1"/"$2, "READY", $3}')"
echo; echo "## 5. 그 밖에 우리가 올린 Add-on 성격의 것"
$K get deploy,ds -A --no-headers | awk '{print $1, $2}' | grep -vE '^(kube-system|default) ' | column -t
