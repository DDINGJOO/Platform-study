#!/usr/bin/env bash
# CCM 이 없는 클러스터에서 ccm-demo / lb-demo 를 만들었을 때 Calico kube-controllers 의 LoadBalancer 컨트롤러가 무엇을 했나 (Mac 에서 실행, 조회만)
# calico-kube-controllers 로그 시각은 UTC(노드 시계 기준)이고 KST 는 +9시간이다.
cd "$(dirname "$0")/../.."   # 실습 저장소 루트 (./lab 이 있는 곳)
K="./lab kubectl"
echo "# 24편 감사 보강: calico-kube-controllers 로그의 LoadBalancer 컨트롤러 기록 ($(date '+%F %T %Z'), Mac 에서 ./lab kubectl 로, 조회만)"
echo "# 로그 시각은 UTC. 06:18:57 UTC = 15:18:57 KST (24-ccm.txt 의 ccm-demo), 07:08:35 UTC = 16:08:35 KST (24-calico-lb.txt 의 lb-demo)"
$K -n kube-system get pod -l k8s-app=calico-kube-controllers -o custom-columns='NAME:.metadata.name,RESTARTS:.status.containerStatuses[0].restartCount,STARTED:.status.containerStatuses[0].state.running.startedAt' 
echo
$K -n kube-system logs deploy/calico-kube-controllers --since=24h 2>&1 | grep -E 'Starting controller ControllerType="LoadBalancer"|default/ccm-demo|default/lb-demo|172\.30\.0\.0'
