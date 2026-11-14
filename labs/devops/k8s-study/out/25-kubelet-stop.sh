#!/usr/bin/env bash
# 워커 한 대(k8s-worker3)의 kubelet 을 멈추고 노드 상태·taint·파드 응답을 10초마다 기록한 뒤 되살린다 (Mac 에서 실행)
cd "$(dirname "$0")/../.."   # 실습 저장소 루트 (./lab 이 있는 곳)
K="./lab kubectl"; ts(){ date '+%T'; }
P=$($K get pod -l app=myweb --field-selector spec.nodeName=k8s-worker3 -o jsonpath='{.items[0].metadata.name}')
IP=$($K get pod $P -o jsonpath='{.status.podIP}')
echo "# E4 워커 kubelet 을 멈추면: 노드는? 그 위 파드는? ($(date '+%F %T %Z'))"
echo "$(ts) 대상: k8s-worker3, 파드 $P ($IP)"
echo "$(ts) mac\$ kubectl get pod $P -o jsonpath='{.spec.tolerations}'  (쿠버네티스가 기본으로 붙인 toleration)"
$K get pod $P -o jsonpath='{range .spec.tolerations[*]}{.key}{" "}{.effect}{" "}{.tolerationSeconds}{"\n"}{end}'
T0=$(date +%s)
echo "$(ts) worker3\$ sudo systemctl stop kubelet"; ./lab ssh 3 -- sudo systemctl stop kubelet
for i in $(seq 1 16); do
  sleep 10; e=$(( $(date +%s) - T0 ))
  st=$($K get node k8s-worker3 -o jsonpath='{range .status.conditions[?(@.type=="Ready")]}{.status}/{.reason}{end}' 2>/dev/null)
  tn=$($K get node k8s-worker3 -o jsonpath='{range .spec.taints[*]}{.key}:{.effect} {end}' 2>/dev/null)
  ps=$($K get pod $P -o jsonpath='{.status.phase}/ready={.status.conditions[?(@.type=="Ready")].status}' 2>/dev/null)
  cc=$(./lab ssh master -- curl -s -o /dev/null -w "%{http_code}" --max-time 3 http://$IP/ 2>/dev/null)
  echo "$(ts) +${e}s  노드 Ready=$st | taints: ${tn:-없음} | 파드(API 기준) $ps | curl $IP → $cc"
done
echo "$(ts) worker3\$ sudo systemctl start kubelet"; ./lab ssh 3 -- sudo systemctl start kubelet
for i in $(seq 1 18); do
  sleep 5; st=$($K get node k8s-worker3 -o jsonpath='{range .status.conditions[?(@.type=="Ready")]}{.status}/{.reason}{end}' 2>/dev/null)
  [ "${st%%/*}" = True ] && break
done
echo "$(ts) 되살린 뒤 노드 Ready=$st | taints: $($K get node k8s-worker3 -o jsonpath='{range .spec.taints[*]}{.key}:{.effect} {end}')"
$K get pod $P -o wide 2>&1 | awk '{print $1,$2,$3,$4,$7}'
