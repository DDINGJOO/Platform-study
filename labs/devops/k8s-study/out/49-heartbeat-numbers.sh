#!/usr/bin/env bash
# 실습 저장소의 shared/why/01-node-heartbeat-and-eviction-timeouts/01-heartbeat-numbers.sh 를 옮긴 것. 실습 저장소 루트에서 실행한다.
# (조회만) 노드 장애 감지 숫자 4개(Lease 40/10초, NodeStatus 5분, grace 50초, toleration 300초)가 우리 클러스터에서 실제로 어떤 값인지, 누가 그 값을 정하는지 확인한다 (Mac 에서 실행)
cd "$(dirname "$0")/../../.."   # 실습 저장소 루트 (./lab 이 있는 곳)
K="./lab kubectl"; ts(){ date '+%T'; }
N=k8s-worker1
echo "# 01 노드 하트비트·축출 숫자 확인 ($(date '+%F %T %Z'))"

echo; echo "## 1. kubelet 쪽 (configz, $N)"
$K get --raw /api/v1/nodes/$N/proxy/configz | python3 -c 'import json,sys;c=json.load(sys.stdin)["kubeletconfig"];[print(f"  {k} = {c.get(k)}") for k in ("nodeStatusUpdateFrequency","nodeStatusReportFrequency","nodeLeaseDurationSeconds")]'
echo "  /var/lib/kubelet/config.yaml 에 직접 적힌 값(없으면 기본값):"
./lab ssh $N -- sudo grep -E 'nodeStatus|nodeLease' /var/lib/kubelet/config.yaml 2>/dev/null | sed 's/^/    /' || true

echo; echo "## 2. Lease renewTime 을 2초마다 26초 동안 ($N) — 10초(=40 x 0.25)마다 바뀌는지"
prev=""
for i in $(seq 1 14); do
  r=$($K -n kube-node-lease get lease $N -o jsonpath='{.spec.renewTime}')
  mark=""; [ -n "$prev" ] && [ "$r" != "$prev" ] && mark="  <- 갱신"
  echo "  $(ts) renewTime=$r$mark"; prev=$r; sleep 2
done

echo; echo "## 3. 같은 순간 Node.status 의 Ready lastHeartbeatTime vs Lease renewTime (노드별)"
now=$(date -u +%s)
for n in k8s-master k8s-worker1 k8s-worker2 k8s-worker3; do
  hb=$($K get node $n -o jsonpath='{.status.conditions[?(@.type=="Ready")].lastHeartbeatTime}')
  rn=$($K -n kube-node-lease get lease $n -o jsonpath='{.spec.renewTime}')
  python3 - "$n" "$hb" "$rn" "$now" <<'PY'
import sys,datetime as d
n,hb,rn,now=sys.argv[1],sys.argv[2],sys.argv[3],int(sys.argv[4])
p=lambda s:d.datetime.fromisoformat(s.replace('Z','+00:00')).timestamp()
print(f"  {n:12s} NodeStatus 하트비트 {now-p(hb):6.0f}초 전 | Lease 갱신 {now-p(rn):5.1f}초 전")
PY
done

echo; echo "## 4. 판단하는 쪽: KCM 정적 파드 매니페스트의 관련 플래그 (없으면 기본값 사용)"
./lab ssh master -- sudo grep -n -E 'node-monitor|pod-eviction|node-eviction|feature-gates|controllers=' /etc/kubernetes/manifests/kube-controller-manager.yaml | sed 's/^/  /' || echo "  (관련 플래그 없음 = 기본값: node-monitor-grace-period 50s, node-monitor-period 5s)"
echo "  KCM 이 --pod-eviction-timeout 플래그를 아직 아는가:"
$K -n kube-system exec kube-controller-manager-k8s-master -- kube-controller-manager --help 2>/dev/null | grep -c -- '--pod-eviction-timeout' | sed 's/^/    help 출력에서 찾은 줄 수 = /'
$K -n kube-system exec kube-controller-manager-k8s-master -- kube-controller-manager --help 2>/dev/null | grep -o -E 'NodeControllerLeaseCircuitBreaker=true\|false \(BETA - default=true\)|NodeControllerLeaseCircuitBreaker=[^ ]+ \([^)]*\)' | head -1 | sed 's/^/    feature gate: /'

echo; echo "## 5. 기본 toleration 300초를 넣는 쪽: kube-apiserver"
./lab ssh master -- sudo grep -n -E 'admission-plugins|toleration-seconds' /etc/kubernetes/manifests/kube-apiserver.yaml | sed 's/^/  /' || true
echo "  (default-not-ready/unreachable-toleration-seconds 플래그가 없으면 300)"
P=$($K get pod -l app=myweb -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
if [ -n "$P" ]; then
  echo "  파드 $P 의 tolerations:"
  $K get pod "$P" -o jsonpath='{range .spec.tolerations[*]}    {.key} {.effect} {.tolerationSeconds}{"\n"}{end}'
fi
echo "  DaemonSet 파드(calico-node)의 같은 toleration (tolerationSeconds 없음 = 무기한):"
CP=$($K -n kube-system get pod -l k8s-app=calico-node -o jsonpath='{.items[0].metadata.name}')
$K -n kube-system get pod "$CP" -o jsonpath='{range .spec.tolerations[*]}    {.key} {.operator} {.effect} {.tolerationSeconds}{"\n"}{end}' | grep -E 'not-ready|unreachable|Exists  *$' || true

echo; echo "## 6. Lease 객체 한 개 전체 (leaseDurationSeconds 는 KCM 판단에 쓰이지 않는다는 점 확인용)"
$K -n kube-node-lease get lease $N -o yaml | sed -n '/^spec:/,$p' | sed 's/^/  /'
