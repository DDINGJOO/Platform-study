#!/usr/bin/env bash
# worker3 의 calico-node 안에서 BIRD 만 멈추면: 다른 노드의 경로, 노드 간 파드 통신, calico-node 상태가 어떻게 바뀌나 (Mac 에서 실행)
cd "$(dirname "$0")/../.."   # 실습 저장소 루트 (./lab 이 있는 곳)
K="./lab kubectl"; ts(){ date '+%T'; }
CN3=$($K -n kube-system get pod -l k8s-app=calico-node --field-selector spec.nodeName=k8s-worker3 -o jsonpath='{.items[0].metadata.name}')
CN1=$($K -n kube-system get pod -l k8s-app=calico-node --field-selector spec.nodeName=k8s-worker1 -o jsonpath='{.items[0].metadata.name}')
BLK=$($K get blockaffinities.crd.projectcalico.org -o jsonpath='{range .items[?(@.spec.node=="k8s-worker3")]}{.spec.cidr}{end}')
P3=$($K get pod -l app=myweb --field-selector spec.nodeName=k8s-worker3 -o jsonpath='{.items[0].status.podIP}')
snap(){
  e=$(( $(date +%s) - T0 ))
  r=$(./lab ssh 1 -- ip route show $BLK 2>/dev/null | tr -s ' ' | cut -c1-60)
  b=$($K -n kube-system exec $CN1 -c calico-node -- birdcl -s /var/run/calico/bird.ctl show protocols 2>/dev/null | awk '/Mesh_192_168_104_5/{print $4, $6}')
  c=$(./lab ssh 1 -- curl -s -o /dev/null -w "%{http_code}" --max-time 3 http://$P3/ 2>/dev/null)
  s=$($K -n kube-system get pod $CN3 --no-headers 2>/dev/null | awk '{print $2, "restarts="$4}')
  echo "$(ts) +${e}s | worker1 의 $BLK 경로: ${r:-없음} | worker1 BIRD→worker3: ${b:-?} | curl $P3 → $c | $CN3 $s"
}
echo "# E8b worker3 의 BIRD 를 멈추면 ($(date '+%F %T %Z'))"
echo "worker3 파드 블록 $BLK, worker3 의 myweb 파드 $P3"
T0=$(date +%s); snap
echo "$(ts) worker3 calico-node\$ sv stop bird"; $K -n kube-system exec $CN3 -c calico-node -- sv stop bird
for i in $(seq 1 9); do sleep 8; snap; done
echo "$(ts) worker3 calico-node\$ sv start bird"; $K -n kube-system exec $CN3 -c calico-node -- sv start bird 2>&1
for i in $(seq 1 5); do sleep 5; snap; done
echo "$(ts) calico-node 이벤트:"; $K -n kube-system get events --field-selector involvedObject.name=$CN3 --sort-by=.lastTimestamp --no-headers 2>/dev/null | tail -5 | cut -c1-200
