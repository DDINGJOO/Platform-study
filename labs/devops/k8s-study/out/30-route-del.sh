#!/usr/bin/env bash
# worker1 에서 worker3 파드 블록 경로를 손으로 지우면: 노드 간 파드 통신은? BIRD 가 다시 넣나? (Mac 에서 실행)
cd "$(dirname "$0")/../.."   # 실습 저장소 루트 (./lab 이 있는 곳)
K="./lab kubectl"
BLK=$($K get blockaffinities.crd.projectcalico.org -o jsonpath='{range .items[?(@.spec.node=="k8s-worker3")]}{.spec.cidr}{end}')
P3=$($K get pod -l app=myweb --field-selector spec.nodeName=k8s-worker3 -o jsonpath='{.items[0].status.podIP}')
echo "# E8c 경로 하나를 지우면 ($(date '+%F %T %Z')), 블록 $BLK, 대상 파드 $P3"
echo "(BIRD 설정: kernel 프로토콜 'learn; persist; scan time 2;')"
./lab ssh 1 -- sudo BLK="$BLK" P3="$P3" bash -s <<'REMOTE'
t(){ date '+%T.%3N'; }
rt(){ ip route show $BLK | tr -s ' ' | cut -c1-70; }
cu(){ curl -s -o /dev/null -w "%{http_code}" --max-time 1 http://$P3/; }
echo "$(t) 지우기 전: 경로 [$(rt)] curl → $(cu)"
echo "$(t) worker1# ip route del $BLK"; ip route del $BLK
echo "$(t) 지운 직후: 경로 [$(rt)] ip route get → $(ip route get $P3 | head -1 | tr -s ' ')"
echo "$(t) 지운 직후 curl → $(cu)"
for i in $(seq 1 10); do sleep 0.5; r=$(rt); echo "$(t) 경로 [${r:-없음}]"; [ -n "$r" ] && break; done
echo "$(t) 복구 뒤 curl → $(cu)"
REMOTE
