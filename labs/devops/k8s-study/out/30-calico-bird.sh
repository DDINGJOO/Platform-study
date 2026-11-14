#!/usr/bin/env bash
# Calico 의 BIRD 가 하는 일: 노드마다 BGP 로 파드 대역(/26 블록) 경로를 주고받아 커널 라우팅 표에 넣는다 (Mac 에서 실행)
cd "$(dirname "$0")/../.."   # 실습 저장소 루트 (./lab 이 있는 곳)
K="./lab kubectl"
CN1=$($K -n kube-system get pod -l k8s-app=calico-node --field-selector spec.nodeName=k8s-worker1 -o jsonpath='{.items[0].metadata.name}')
echo "# E8 Calico 와 BIRD ($(date '+%F %T %Z')), 대상 calico-node 파드: $CN1 (k8s-worker1)"
echo; echo "## 1. Calico 설정: 백엔드와 캡슐화"
$K -n kube-system get cm calico-config -o jsonpath='calico_backend={.data.calico_backend}{"\n"}'
$K get ippools.crd.projectcalico.org -o custom-columns='POOL:.metadata.name,CIDR:.spec.cidr,IPIP:.spec.ipipMode,VXLAN:.spec.vxlanMode,NAT:.spec.natOutgoing'
echo; echo "## 2. calico-node 파드 안의 프로세스 (bird = BGP, felix = 정책·인터페이스, confd = bird 설정 생성)"
./lab ssh 1 -- sh -c "ps -eo pid,ppid,args | grep -E 'bird|felix|confd|runsv' | grep -v grep | cut -c1-110"
echo; echo "## 3. calico-node 준비 상태 검사에 bird 가 들어 있음"
$K -n kube-system get ds calico-node -o jsonpath='readiness: {.spec.template.spec.containers[0].readinessProbe.exec.command}{"\n"}liveness:  {.spec.template.spec.containers[0].livenessProbe.exec.command}{"\n"}'
echo; echo "## 4. BIRD 의 BGP 세션 (birdcl show protocols): 노드 4대 full mesh → 상대 3개"
$K -n kube-system exec $CN1 -c calico-node -- birdcl -s /var/run/calico/bird.ctl show protocols
echo; echo "## 5. 노드별 파드 대역 블록 (Calico IPAM blockaffinity)"
$K get blockaffinities.crd.projectcalico.org -o custom-columns='NODE:.spec.node,CIDR:.spec.cidr,STATE:.spec.state' | sort
echo; echo "## 6. BIRD 가 받은 경로 (birdcl show route)"
$K -n kube-system exec $CN1 -c calico-node -- birdcl -s /var/run/calico/bird.ctl show route
echo; echo "## 7. worker1 커널 라우팅 표: 다른 노드의 /26 블록은 tunl0(IPIP) 로, 자기 블록은 blackhole"
./lab ssh 1 -- ip route | grep -E 'bird|blackhole|tunl0'
echo; echo "## 8. BGP TCP 179 연결 (worker1)"
./lab ssh 1 -- sudo ss -tn state established '( sport = :179 or dport = :179 )'
echo; echo "## 9. worker1 → worker3 의 파드로 가는 길"
P3=$($K get pod -l app=myweb --field-selector spec.nodeName=k8s-worker3 -o jsonpath='{.items[0].status.podIP}')
echo "worker3 의 myweb 파드 IP: $P3"
./lab ssh 1 -- ip route get $P3
./lab ssh 1 -- curl -s -o /dev/null -w "worker1 → $P3:80 HTTP %{http_code}\n" --max-time 3 http://$P3/
