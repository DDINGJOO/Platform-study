#!/usr/bin/env bash
# kubelet 을 70초 멈춘 동안 Service 의 EndpointSlice 에서 그 노드 파드가 어떻게 표시되는지 본다 (Mac 에서 실행)
cd "$(dirname "$0")/../.."   # 실습 저장소 루트 (./lab 이 있는 곳)
k(){ ./lab kubectl "$@"; }; ts(){ date '+%T'; }
P=myweb-859c4764d4-5xtpv; IP=$(k get pod $P -o jsonpath='{.status.podIP}')
es(){ k get endpointslices -l kubernetes.io/service-name=myweb -o json | python3 -c "
import json,sys
for s in json.load(sys.stdin)['items']:
    for e in s['endpoints']:
        if e['addresses'][0]=='$IP': print('   ',e['addresses'][0],'ready=',e['conditions'].get('ready'),'serving=',e['conditions'].get('serving'),'terminating=',e['conditions'].get('terminating'))"; }
echo "# E4b kubelet 정지 중 EndpointSlice 에서 그 파드는? ($(date '+%F %T %Z'))"
echo "$(ts) 대상 파드 $P ($IP, k8s-worker3). 멈추기 전 EndpointSlice:"; es
echo "$(ts) worker3\$ sudo systemctl stop kubelet"; ./lab ssh 3 -- sudo systemctl stop kubelet
sleep 65
echo "$(ts) +65s 노드 Ready=$(k get node k8s-worker3 -o jsonpath='{range .status.conditions[?(@.type=="Ready")]}{.status}/{.reason}{end}')"
echo "$(ts) +65s EndpointSlice:"; es
echo "$(ts) +65s 파드 IP 로 직접 curl: $(./lab ssh master -- curl -s -o /dev/null -w '%{http_code}' --max-time 3 http://$IP/)"
echo "$(ts) +65s kubectl logs (API 서버 → kubelet 경로): $(k logs $P --tail=1 2>&1 | head -c 160)"
echo "$(ts) worker3\$ sudo systemctl start kubelet"; ./lab ssh 3 -- sudo systemctl start kubelet
sleep 20
echo "$(ts) 되살린 뒤 노드 Ready=$(k get node k8s-worker3 -o jsonpath='{range .status.conditions[?(@.type=="Ready")]}{.status}{end}'), EndpointSlice:"; es
