#!/usr/bin/env bash
# IP 풀 크기 계산에 쓰는 값: 컨트롤러 매니저의 노드 CIDR 플래그, 노드 podCIDR, IPPool blockSize, 노드당 파드 수 상한(maxPods) (조회만 한다)
# 실습 저장소 루트(./lab 이 있는 곳)에서 bash <이 파일> 로 실행 (Mac)
K="./lab kubectl"
echo "# 31편 보강: IP 풀 크기 계산에 쓰는 값 ($(date '+%F %T %Z')), Mac 에서 ./lab 으로 조회"
echo; echo "## 1. kube-controller-manager 의 노드 CIDR 관련 플래그 (master /etc/kubernetes/manifests/kube-controller-manager.yaml)"
./lab ssh master -- sudo grep -E -- '--(allocate-node-cidrs|cluster-cidr|node-cidr-mask-size)' /etc/kubernetes/manifests/kube-controller-manager.yaml
echo "(--node-cidr-mask-size 줄이 없으면 기본값을 쓴다)"
echo; echo "## 2. 노드별 podCIDR 과 파드 수 상한(capacity.pods)"
$K get nodes -o custom-columns='NODE:.metadata.name,PODCIDR:.spec.podCIDR,CAPACITY_PODS:.status.capacity.pods,ALLOCATABLE_PODS:.status.allocatable.pods'
echo "worker2 /var/lib/kubelet/config.yaml 의 maxPods 줄: [$(./lab ssh 2 -- sudo grep -i maxPods /var/lib/kubelet/config.yaml)] (비어 있으면 기본값)"
echo; echo "## 3. IPPool"
$K get ippools.crd.projectcalico.org -o custom-columns='POOL:.metadata.name,CIDR:.spec.cidr,BLOCKSIZE:.spec.blockSize'
