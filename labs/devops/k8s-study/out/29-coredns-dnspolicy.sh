#!/usr/bin/env bash
# 29편 보강: CoreDNS 파드 자신은 어떤 DNS 설정으로 뜨나 (forward . /etc/resolv.conf 가 가리키는 곳) (Mac 에서 실행, 조회만)
cd "$(dirname "$0")/../.."   # 실습 저장소 루트 (./lab 이 있는 곳)
K="./lab kubectl"
RD=$(./lab ssh 1 -- bash -s <<'R' | sed 's/\./\\./g'
awk '/^search/{print $2}' /run/systemd/resolve/resolv.conf
R
)
{
echo "# CoreDNS 파드의 dnsPolicy ($(date '+%F %T %Z'), Mac 에서 ./lab 으로 조회)"
echo "\$ kubectl -n kube-system get deploy coredns -o jsonpath='{.spec.template.spec.dnsPolicy}'"
$K -n kube-system get deploy coredns -o jsonpath='{.spec.template.spec.dnsPolicy}'; echo
echo "\$ kubectl -n kube-system get pod -l k8s-app=kube-dns -o custom-columns=NAME:.metadata.name,IP:.status.podIP,NODE:.spec.nodeName"
$K -n kube-system get pod -l k8s-app=kube-dns -o custom-columns=NAME:.metadata.name,IP:.status.podIP,NODE:.spec.nodeName
echo "\$ kubectl -n kube-system get deploy coredns -o jsonpath='{.spec.template.spec.containers[0].image}'"
$K -n kube-system get deploy coredns -o jsonpath='{.spec.template.spec.containers[0].image}'; echo
} 2>&1 | sed "s/${RD:-__none__}/<router-domain>/g"
