#!/usr/bin/env bash
# lifecycle.stopSignal이 v1.37.2 클러스터에서 실제로 먹히나: 기능 게이트 상태, 저장된 spec, 삭제 시간, containerd가 보낸 신호 (Mac 에서 실행)
# 네임스페이스 why-pid1만 쓴다. 기능 게이트는 읽기만 한다(metrics). 이미지: busybox:1.37
cd "$(dirname "$0")/../../.."   # 실습 저장소 루트
K="./lab kubectl"; NS=why-pid1
now(){ perl -MTime::HiRes=time -e 'printf "%.3f", time'; }
$K get ns $NS >/dev/null 2>&1 || $K create ns $NS >/dev/null
echo "# lifecycle.stopSignal 시험 ($(date '+%F %T %Z'))"

echo; echo "## 1. 기능 게이트 ContainerStopSignals (각 컴포넌트 /metrics의 kubernetes_feature_enabled)"
printf "  %-22s %s\n" "kube-apiserver" "$($K get --raw /metrics 2>/dev/null | grep 'kubernetes_feature_enabled{name="ContainerStopSignals"')"
for n in k8s-master k8s-worker1 k8s-worker2 k8s-worker3; do
  printf "  %-22s %s\n" "kubelet@$n" "$($K get --raw /api/v1/nodes/$n/proxy/metrics 2>/dev/null | grep 'kubernetes_feature_enabled{name="ContainerStopSignals"')"
done

echo; echo "## 2. API 스키마에는 필드가 있다 (kubectl explain의 FIELD·DESCRIPTION. alpha라는 말은 없다)"
$K explain pod.spec.containers.lifecycle.stopSignal 2>&1 | grep -E '^FIELD' | sed 's/^/  /'
$K explain pod.spec.containers.lifecycle.stopSignal 2>&1 | sed -n '/^DESCRIPTION/,/Possible enum/p' | sed 's/^/  /'
echo "  (뒤로 SIGABRT ~ SIGXFSZ, SIGRTMIN+n, SIGRTMAX-n 열거값 $($K explain pod.spec.containers.lifecycle.stopSignal 2>&1 | grep -c '^ *- `"SIG')개)"

echo; echo "## 3. stopSignal: SIGKILL을 넣어 만들면 무엇이 저장되나"
cat > /tmp/why-pid1-s-kill.yaml <<'Y'
apiVersion: v1
kind: Pod
metadata: {name: s-kill, labels: {exp: stopsig}}
spec:
  os: {name: linux}
  terminationGracePeriodSeconds: 30
  containers:
  - name: c
    image: busybox:1.37
    command: [sleep, infinity]
    lifecycle:
      stopSignal: SIGKILL
Y
echo "  보낸 매니페스트의 lifecycle: $(grep -A1 'lifecycle:' /tmp/why-pid1-s-kill.yaml | tail -1 | sed 's/^ *//')"
echo "  kubectl create 출력:"; $K -n $NS create -f /tmp/why-pid1-s-kill.yaml 2>&1 | sed 's/^/    /'
echo "  저장된 .spec.containers[0].lifecycle = '$($K -n $NS get pod s-kill -o jsonpath='{.spec.containers[0].lifecycle}')'  (비어 있으면 API 서버가 버린 것)"
echo "  저장된 .spec.os = $($K -n $NS get pod s-kill -o jsonpath='{.spec.os}')"

echo; echo "## 4. 검증도 안 하고 버리나: 리눅스에 없는 이름(SIGFOO) + spec.os 없이 server-side dry-run"
sed -e 's/SIGKILL/SIGFOO/' -e '/os: {name: linux}/d' -e 's/name: s-kill/name: s-foo/' /tmp/why-pid1-s-kill.yaml \
  | $K -n $NS create --dry-run=server -o jsonpath='{"  결과: 생성 허용, lifecycle=\x27"}{.spec.containers[0].lifecycle}{"\x27\n"}' -f - 2>&1 | sed 's/^  결과/  결과/'
rm -f /tmp/why-pid1-s-kill.yaml

echo; echo "## 5. s-kill을 지우면 몇 초 걸리나 (stopSignal이 먹혔다면 SIGKILL로 바로 끝나야 한다)"
$K -n $NS wait --for=condition=Ready pod/s-kill --timeout=120s >/dev/null
N=$($K -n $NS get pod s-kill -o jsonpath='{.spec.nodeName}')
CID=$($K -n $NS get pod s-kill -o jsonpath='{.status.containerStatuses[0].containerID}' | sed 's#containerd://##')
echo "  status.containerStatuses[0].stopSignal = '$($K -n $NS get pod s-kill -o jsonpath='{.status.containerStatuses[0].stopSignal}')'"
a=$(now); v=$(limactl shell $N -- date +%s.%N); b=$(now); OFF=$(perl -e "printf '%.3f', $v - ($a+$b)/2")
T0=$(now); $K -n $NS delete pod s-kill --wait=false >/dev/null
until ! $K -n $NS get pod s-kill >/dev/null 2>&1; do sleep 0.3; done
perl -e "printf \"  +%.1fs 객체 사라짐 (노드 $N, 노드-Mac=${OFF}s)\n\", $(now)-$T0"
limactl shell $N -- sudo journalctl -u containerd --since "$(date -r $(( ${T0%.*} - 3 )) '+%F %T')" --no-pager -o short-unix 2>/dev/null | grep "$CID" \
  | grep -E 'StopContainer for .* with timeout|Stop container|Kill container' | while read -r ts rest; do
    perl -e "printf \"  node +%5.1fs  \", $ts - $OFF - $T0"; echo "$rest" | sed -E 's/.*msg="//; s/"$//; s/[0-9a-f]{64}/<cid>/g; s/\\"/"/g'
  done
