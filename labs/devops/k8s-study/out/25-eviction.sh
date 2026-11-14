#!/usr/bin/env bash
# 노드가 죽은 뒤 300초 toleration 이 끝나면 파드가 실제로 쫓겨나고 다른 노드에 새로 뜨는가 (Mac 에서 실행)
# 대상: myweb 파드가 있는 워커 한 대의 kubelet 을 멈춘다. 끝에서 kubelet 을 다시 켠다.
cd "$(dirname "$0")/../.."   # 실습 저장소 루트 (./lab 이 있는 곳)
K="./lab kubectl"; ts(){ date '+%T'; }
N=${1:-k8s-worker3}; NI=${N#k8s-worker}
echo "# E24 kubelet 을 300초 넘게 멈추면: 축출과 재생성 ($(date '+%F %T %Z')), 대상 $N"
echo; echo "## 0. 시작 전"
$K get pod -A -o wide --field-selector spec.nodeName=$N --no-headers | awk '{print "  "$1"/"$2, $4}'
echo "  myweb 파드: $($K get pod -l app=myweb -o jsonpath='{range .items[*]}{.metadata.name}@{.spec.nodeName} {end}')"
P=$($K get pod -l app=myweb --field-selector spec.nodeName=$N -o jsonpath='{.items[*].metadata.name}')
echo "  $N 의 myweb: $P"
echo "  toleration: $($K get pod $(echo $P | awk '{print $1}') -o jsonpath='{range .spec.tolerations[*]}{.key}:{.effect}:{.tolerationSeconds} {end}')"
T0=$(date +%s)
echo; echo "$(ts) +0s $N\$ sudo systemctl stop kubelet"; ./lab ssh $NI -- sudo systemctl stop kubelet
seen_new=""
for i in $(seq 1 40); do
  sleep 15; e=$(( $(date +%s) - T0 ))
  st=$($K get node $N -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}')
  tn=$($K get node $N -o jsonpath='{range .spec.taints[*]}{.key}:{.effect}@{.timeAdded} {end}' | sed 's/node.kubernetes.io\///g')
  pods=$($K get pod -l app=myweb -o jsonpath='{range .items[*]}{.metadata.name}|{.spec.nodeName}|{.status.phase}|{.metadata.deletionTimestamp}{"\n"}{end}' | awk -F'|' '{d=($4==""?"":" del="$4); print substr($1,length($1)-4)"@"$2"("$3 d")"}' | paste -sd' ' -)
  echo "$(ts) +${e}s Ready=$st | taints: ${tn:-없음}"
  echo "            myweb: $pods"
  if $K get pod -l app=myweb -o jsonpath='{range .items[*]}{.metadata.deletionTimestamp}{"\n"}{end}' | grep -q . ; then
    [ -z "$seen_new" ] && { echo "$(ts) +${e}s 축출 시작 관찰"; seen_new=1; }
  fi
  [ -n "$seen_new" ] && [ $e -gt 480 ] && break
  [ $e -gt 600 ] && break
done
echo; echo "## 축출 관련 이벤트"
$K get events -A --sort-by=.lastTimestamp --no-headers 2>/dev/null | grep -E 'TaintManagerEviction|Evict|NodeNotReady|SuccessfulCreate' | grep -E "myweb|$N" | tail -12 | cut -c1-200
echo; echo "## 새로 만들어진 myweb 파드"
$K get pod -l app=myweb -o custom-columns='NAME:.metadata.name,NODE:.spec.nodeName,PHASE:.status.phase,CREATED:.metadata.creationTimestamp,DELETED:.metadata.deletionTimestamp'
echo; echo "## IP 누수 관찰: 쫓겨난 옛 파드는 kubelet 이 없어 Terminating 으로 남는다. 강제로 지우면 API 에서는 사라지지만 노드의 컨테이너와 Calico IP 는?"
OLD=$($K get pod -l app=myweb -o jsonpath='{range .items[?(@.metadata.deletionTimestamp)]}{.metadata.name} {.status.podIP}{"\n"}{end}')
echo "$(ts) Terminating 파드와 IP: $OLD"
for x in $(echo "$OLD" | awk '{print $1}'); do echo "$(ts) mac\$ kubectl delete pod $x --grace-period=0 --force"; $K delete pod $x --grace-period=0 --force 2>&1 | tail -1; done
OIP=$(echo "$OLD" | awk 'NR==1{print $2}')
echo "$(ts) $N 에서 그 IP 의 컨테이너는 아직 도나: $(./lab ssh $NI -- sudo crictl ps --name nginx -q 2>/dev/null | wc -l | tr -d ' ')개 nginx 컨테이너, 경로 $(./lab ssh $NI -- ip route show $OIP 2>/dev/null | awk '{print $3}')"
TF=$(date +%s)
for i in $(seq 1 20); do
  e=$(( $(date +%s) - TF ))
  chk=$(./lab ssh master -- calicoctl ipam check 2>&1 | grep -E "allocated in IPAM but not actually in use|problems" | paste -sd' ' -)
  blk=$($K get ipamblocks.crd.projectcalico.org -o json | python3 -c "import json,sys,ipaddress
ip=ipaddress.ip_address('$OIP')
for b in json.load(sys.stdin)['items']:
  n=ipaddress.ip_network(b['spec']['cidr'])
  if ip in n:
    o=int(ip)-int(n.network_address); a=b['spec']['allocations'][o]
    print('할당됨' if a is not None else '비어 있음')" 2>/dev/null)
  echo "$(ts) 강제 삭제 +${e}s | IPAM 에서 $OIP: $blk | ipam check: $chk"
  [ "$blk" = "비어 있음" ] && break
  sleep 60
done
echo "kube-controllers 로그 (이 IP):"; $K -n kube-system logs deploy/calico-kube-controllers --since=40m 2>&1 | grep "$OIP" | cut -c1-200 | tail -6
echo; echo "$(ts) +$(( $(date +%s) - T0 ))s $N\$ sudo systemctl start kubelet"; ./lab ssh $NI -- sudo systemctl start kubelet
for i in $(seq 1 24); do sleep 5; st=$($K get node $N -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}'); [ "$st" = True ] && break; done
sleep 20
echo "$(ts) +$(( $(date +%s) - T0 ))s Ready=$st taints=$($K get node $N -o jsonpath='{.spec.taints}')"
$K get pod -l app=myweb -o custom-columns='NAME:.metadata.name,NODE:.spec.nodeName,PHASE:.status.phase,CREATED:.metadata.creationTimestamp'
echo "  $N 의 nginx 컨테이너: $(./lab ssh $NI -- sudo crictl ps --name nginx -q 2>/dev/null | wc -l | tr -d ' ')개, $OIP 경로: [$(./lab ssh $NI -- ip route show $OIP 2>/dev/null)]"
echo "  CNI 로그($OIP): $(./lab ssh $NI -- sudo grep "$OIP" /var/log/calico/cni/cni.log 2>/dev/null | tail -3 | cut -c1-160)"
echo "  ipam check: $(./lab ssh master -- calicoctl ipam check 2>&1 | tail -1)"
