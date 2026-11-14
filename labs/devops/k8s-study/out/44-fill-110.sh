#!/usr/bin/env bash
# 실습 저장소의 shared/why/03-max-pods-110/02-fill-110.sh 를 옮긴 것. 실습 저장소 루트에서 실행한다.
# worker3 에 파드를 110개까지 채우면: 111번째는 어떻게 거절되나, kubelet PLEG·메모리, Calico IP 블록은 어떻게 늘어나나 (Mac 에서 실행)
# 네임스페이스 w2-fill 만 쓰고 지운다. pause 이미지, requests 없음.
cd "$(dirname "$0")/../../.."   # 실습 저장소 루트
K="./lab kubectl"; ts(){ date '+%T'; }; NS=w2-fill; N=k8s-worker3
now(){ python3 -c 'import time;print("%.1f"%time.time())'; }
km(){ $K get --raw /api/v1/nodes/$N/proxy/metrics | grep -E '^(kubelet_pleg_relist_duration_seconds_(sum|count)|process_resident_memory_bytes|kubelet_running_pods) '; }
pleg(){ # 두 스냅숏 사이 평균 relist 시간(ms), 마지막 RSS(MiB), running_pods
python3 - "$1" "$2" <<'P'
import sys
def ld(s): return {l.split()[0]:float(l.split()[1]) for l in s.strip().splitlines()}
a,b=ld(sys.argv[1]),ld(sys.argv[2])
ds=b["kubelet_pleg_relist_duration_seconds_sum"]-a["kubelet_pleg_relist_duration_seconds_sum"]; dc=b["kubelet_pleg_relist_duration_seconds_count"]-a["kubelet_pleg_relist_duration_seconds_count"]
print("PLEG relist %d번 평균 %.2fms | kubelet RSS %.0fMiB | kubelet_running_pods %d" % (dc, ds/dc*1000, b["process_resident_memory_bytes"]/2**20, b["kubelet_running_pods"]))
P
}
blocks(){ $K get blockaffinities.crd.projectcalico.org -o jsonpath='{range .items[*]}{.spec.node} {.spec.cidr}{"\n"}{end}' | grep "^$N " | awk '{print $2}' | paste -sd' ' -; }
echo "# worker3 에 파드 110개 채우기 ($(date '+%F %T %Z'))"
CUR=$($K get pod -A --field-selector spec.nodeName=$N,status.phase!=Succeeded,status.phase!=Failed --no-headers | wc -l | tr -d ' ')
CAP=$($K get node $N -o jsonpath='{.status.allocatable.pods}')
R=$((CAP-CUR+1))
echo; echo "## 0. 시작 상태"
echo "  allocatable.pods=$CAP, 지금 $N 의 파드 ${CUR}개(DaemonSet 포함) → 이 노드에만 파드 ${R}개를 요청하면 1개가 남아야 함"
echo "  Calico 블록(blockaffinity): $(blocks)"
S0=$(km); sleep 30; S1=$(km); echo "  $(ts) 30초 동안: $(pleg "$S0" "$S1")"
$K create ns $NS >/dev/null
cat <<Y | $K -n $NS apply -f - >/dev/null
apiVersion: apps/v1
kind: Deployment
metadata: {name: fill}
spec:
  replicas: $R
  selector: {matchLabels: {app: fill}}
  template:
    metadata: {labels: {app: fill}}
    spec:
      nodeSelector: {kubernetes.io/hostname: $N}
      terminationGracePeriodSeconds: 0
      containers: [{name: c, image: registry.k8s.io/pause:3.10.2}]
Y
T0=$(now); echo; echo "## 1. Deployment fill replicas=$R (nodeSelector $N) 생성 $(ts)"
while :; do
  run=$($K -n $NS get pod --field-selector status.phase=Running --no-headers 2>/dev/null | wc -l | tr -d ' ')
  el=$(python3 -c "print(int($(now)-$T0))")
  echo "  +${el}s Running $run / $R"
  [ "$run" -ge $((R-1)) ] && break; [ "$el" -gt 600 ] && { echo "  10분 초과, 중단"; break; }
  sleep 10
done
echo "$(ts) 파드 상태별 수:"; $K -n $NS get pod --no-headers | awk '{print $3}' | sort | uniq -c | sed 's/^/   /'
P=$($K -n $NS get pod --field-selector status.phase=Pending -o jsonpath='{.items[0].metadata.name}')
echo "$(ts) 남은 파드 $P 의 FailedScheduling:"
$K -n $NS get events --field-selector involvedObject.name=$P,reason=FailedScheduling -o jsonpath='{.items[-1:].message}' | sed 's/^/    /'; echo
echo "$(ts) $N 의 파드 수: $($K get pod -A --field-selector spec.nodeName=$N,status.phase!=Succeeded,status.phase!=Failed --no-headers | wc -l | tr -d ' ')"
S2=$(km); sleep 30; S3=$(km); echo "$(ts) 30초 동안: $(pleg "$S2" "$S3")"
echo "$(ts) Calico 블록: $(blocks)"
echo; echo "## 2. 정리"
T0=$(now); $K delete ns $NS --wait=true >/dev/null; echo "  $(ts) 네임스페이스 $NS 삭제 ($(python3 -c "print(int($(now)-$T0))")초)"
echo "  $(ts) Calico 블록: $(blocks) (빈 블록은 calico-kube-controllers 가 유예 뒤 반납, 34편)"
