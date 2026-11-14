#!/usr/bin/env bash
# IPAM 두 가지: ① 쿠버네티스 node.spec.podCIDR vs Calico IPAM 블록 ② 노드의 /26 블록(64칸)이 다 차면? (Mac 에서 실행)
cd "$(dirname "$0")/../.."   # 실습 저장소 루트 (./lab 이 있는 곳)
K="./lab kubectl"; ts(){ date '+%T'; }
cc(){ ./lab ssh master -- calicoctl "$@" 2>&1; }
aff(){ $K get blockaffinities.crd.projectcalico.org -o jsonpath='{range .items[?(@.spec.node=="k8s-worker2")]}{.spec.cidr}{" "}{end}'; }
echo "# E11 IPAM: 누가 파드 IP 대역을 정하나, 블록이 차면 어떻게 되나 ($(date '+%F %T %Z'))"
echo; echo "## 1. 쿠버네티스가 나눈 대역(node.spec.podCIDR, KCM 의 node-ipam-controller) vs Calico 가 실제로 준 블록"
$K get nodes -o custom-columns='NODE:.metadata.name,K8S_PODCIDR:.spec.podCIDR' > /tmp/e11a
$K get blockaffinities.crd.projectcalico.org -o custom-columns='NODE:.spec.node,CALICO_BLOCK:.spec.cidr' > /tmp/e11b
join <(sort /tmp/e11a) <(sort /tmp/e11b) | column -t
echo "myweb 파드 IP: $($K get pod -l app=myweb -o jsonpath='{range .items[*]}{.spec.nodeName}={.status.podIP} {end}')"
echo "CNI 의 ipam type: $(./lab ssh 2 -- sudo grep -o '"type": "calico-ipam"' /etc/cni/net.d/10-calico.conflist)  (podCIDR 를 쓰는 건 host-local IPAM)"
echo; echo "## 2. 블록 채우기 전 (worker2)"
echo "$(ts) worker2 블록: $(aff)"
cc ipam show --show-blocks | grep -E 'CIDR|Block'
echo; echo "## 3. worker2 에 pause 파드 62개 (블록 빈칸보다 많이)"
cat <<'Y' | $K apply -f - >/dev/null
apiVersion: apps/v1
kind: Deployment
metadata: {name: ipam-fill}
spec:
  replicas: 62
  selector: {matchLabels: {app: ipam-fill}}
  template:
    metadata: {labels: {app: ipam-fill}}
    spec:
      nodeSelector: {kubernetes.io/hostname: k8s-worker2}
      terminationGracePeriodSeconds: 0
      containers: [{name: pause, image: registry.k8s.io/pause:3.10.2, imagePullPolicy: IfNotPresent}]
Y
echo "$(ts) kubectl apply ipam-fill (replicas 62, nodeSelector worker2)"
for i in $(seq 1 30); do sleep 6; r=$($K get deploy ipam-fill -o jsonpath='{.status.readyReplicas}'); echo "$(ts) ready ${r:-0}/62 | worker2 블록: $(aff)"; [ "${r:-0}" = 62 ] && break; done
echo; echo "## 4. 다 뜬 뒤"
cc ipam show --show-blocks | grep -E 'CIDR|Block'
echo "ipam-fill 파드 IP 의 블록별 개수:"; $K get pod -l app=ipam-fill -o jsonpath='{range .items[*]}{.status.podIP}{"\n"}{end}' | awk -F. '{print $1"."$2"."$3".x"}' | sort | uniq -c
echo "worker1 라우팅 표의 worker2(192.168.104.4) 행:"; ./lab ssh 1 -- ip route | grep 192.168.104.4
echo; echo "## 5. 지우기"
$K delete deploy ipam-fill >/dev/null; echo "$(ts) kubectl delete deploy ipam-fill"
for i in $(seq 1 20); do sleep 5; n=$($K get pod -l app=ipam-fill --no-headers 2>/dev/null | wc -l | tr -d ' '); [ "$n" = 0 ] && break; done
echo "$(ts) ipam-fill 파드 0개 | worker2 블록: $(aff)"
cc ipam show --show-blocks | grep -E 'CIDR|Block'
rm -f /tmp/e11a /tmp/e11b
