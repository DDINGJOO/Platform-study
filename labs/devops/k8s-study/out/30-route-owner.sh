#!/usr/bin/env bash
# 노드 간 파드 경로(cluster route)는 누가 넣나: Felix 와 BIRD 양쪽 설정, BIRD 필터, 경로의 proto 표시, calico-node 검사 주기 (조회만 한다)
# 실습 저장소 루트(./lab 이 있는 곳)에서 bash <이 파일> 로 실행 (Mac)
K="./lab kubectl"
CN1=$($K -n kube-system get pod -l k8s-app=calico-node --field-selector spec.nodeName=k8s-worker1 -o jsonpath='{.items[0].metadata.name}')
echo "# 30편 보강: cluster route 의 주인 ($(date '+%F %T %Z')), Mac 에서 ./lab 으로 조회, 대상 calico-node 파드: $CN1 (k8s-worker1)"
echo; echo "## 1. FelixConfiguration default 와 BGPConfiguration default 의 programClusterRoutes"
echo "FelixConfiguration default: programClusterRoutes=$($K get felixconfigurations.crd.projectcalico.org default -o jsonpath='{.spec.programClusterRoutes}') routeRefreshInterval=$($K get felixconfigurations.crd.projectcalico.org default -o jsonpath='{.spec.routeRefreshInterval}')(비어 있으면 기본값)"
echo "BGPConfiguration default:   programClusterRoutes=$($K get bgpconfigurations.crd.projectcalico.org default -o jsonpath='{.spec.programClusterRoutes}')"
echo; echo "## 2. BIRD 설정(confd 가 만든 bird_ipam.cfg): BGP 상대에게 내보내는 필터와 커널에 넣는 필터"
$K -n kube-system exec $CN1 -c calico-node -- grep -n -E '^function calico_export_to_bgp_peers|^filter calico_kernel_programming|if \(net ~ 10\.244\.0\.0/16\)' /etc/calico/confd/config/bird_ipam.cfg
echo; echo "## 3. worker1 라우팅 표: proto 80(Felix 가 넣은 경로) 과 proto bird(BIRD 가 넣은 경로)"
echo "--- ip route show proto 80"
./lab ssh 1 -- ip route show proto 80
echo "--- ip route show proto bird ($(./lab ssh 1 -- ip route show proto bird | wc -l | tr -d ' ')줄)"
./lab ssh 1 -- ip route show proto bird
echo; echo "## 4. calico-node 의 준비·생존 검사 주기"
$K -n kube-system get ds calico-node -o jsonpath='readiness: {.spec.template.spec.containers[0].readinessProbe}{"\n"}liveness:  {.spec.template.spec.containers[0].livenessProbe}{"\n"}'
