#!/usr/bin/env bash
# 실습 저장소의 shared/why/02-pod-and-pause/02-pause-vs-app-kill.sh 를 옮긴 것. 실습 저장소 루트에서 실행한다.
# 앱 프로세스를 죽일 때와 pause 를 죽일 때 무엇이 달라지나 + shareProcessNamespace 에서 pause 가 좀비를 거두나 (Mac 에서 실행)
# 네임스페이스 w1-pause 만 쓰고 지운다. 프로세스는 worker1 에서 kill -9 로 죽인다.
cd "$(dirname "$0")/../../.."   # 실습 저장소 루트
K="./lab kubectl"; ts(){ date '+%T'; }; NS=w1-pause
now(){ python3 -c 'import time;print("%.1f"%time.time())'; }
state(){ # 파드 IP, 재시작 수, 샌드박스 ID·attempt
  local ip rc; ip=$($K -n $NS get pod $1 -o jsonpath='{.status.podIP}'); rc=$($K -n $NS get pod $1 -o jsonpath='{.status.containerStatuses[0].restartCount}')
  ./lab ssh worker1 -- sudo bash -s <<R | tr '\n' ' '
crictl pods --name '^$1\$' --namespace $NS -o json | jq -r '.items[] | "sandbox=\(.id[0:12]) attempt=\(.metadata.attempt) state=\(.state)"'
R
  echo "ip=$ip restartCount=$rc"
}
echo "# 앱 kill vs pause kill, 그리고 좀비 ($(date '+%F %T %Z'))"
$K create ns $NS >/dev/null
cat <<Y | $K -n $NS apply -f - >/dev/null
apiVersion: v1
kind: Pod
metadata: {name: sb-demo}
spec:
  nodeName: k8s-worker1
  terminationGracePeriodSeconds: 0
  containers: [{name: web, image: nginx:1.25.1-alpine}]
Y
$K -n $NS wait --for=condition=Ready pod/sb-demo --timeout=60s >/dev/null
echo; echo "## 1. 처음 상태"; echo "  $(ts) $(state sb-demo)"

echo; echo "## 2. 앱(nginx master) 프로세스를 kill -9"
./lab ssh worker1 -- sudo bash -s <<R
cid=\$(crictl ps --name web --pod \$(crictl pods --name '^sb-demo\$' --namespace $NS -q | head -1) -q | head -1)
pid=\$(crictl inspect \$cid | jq -r .info.pid); echo "  worker1\$ kill -9 \$pid   (\$(ps -o comm= -p \$pid))"; kill -9 \$pid
R
T0=$(now)
until [ "$($K -n $NS get pod sb-demo -o jsonpath='{.status.containerStatuses[0].restartCount}')" = 1 ] && [ "$($K -n $NS get pod sb-demo -o jsonpath='{.status.containerStatuses[0].ready}')" = true ]; do sleep 0.5; done
echo "  $(ts) 다시 Ready: $(python3 -c "print('%.1f' % ($(now)-$T0))")초 / $(state sb-demo)"

echo; echo "## 3. pause 프로세스를 kill -9"
./lab ssh worker1 -- sudo bash -s <<R
pid=\$(crictl inspectp \$(crictl pods --name '^sb-demo\$' --namespace $NS --state ready -q | head -1) | jq -r .info.pid); echo "  worker1\$ kill -9 \$pid   (\$(ps -o comm= -p \$pid))"; kill -9 \$pid
R
T0=$(now); sleep 2
until [ "$($K -n $NS get pod sb-demo -o jsonpath='{.status.containerStatuses[0].ready}')" = true ] && [ "$($K -n $NS get pod sb-demo -o jsonpath='{.status.containerStatuses[0].restartCount}')" = 2 ]; do sleep 0.5; [ $(python3 -c "print(int($(now)-$T0))") -gt 120 ] && break; done
echo "  $(ts) 다시 Ready: $(python3 -c "print('%.1f' % ($(now)-$T0))")초 / $(state sb-demo)"
echo "  worker1 의 이 파드 샌드박스 전부(죽은 것 포함):"
./lab ssh worker1 -- sudo bash -s <<R
crictl pods --name '^sb-demo\$' --namespace $NS -o json | jq -r '.items[] | "    \(.id[0:12]) attempt=\(.metadata.attempt) \(.state)"'
R
echo "  이벤트:"
$K -n $NS get events --field-selector involvedObject.name=sb-demo -o json | python3 -c '
import json,sys
for e in sorted(json.load(sys.stdin)["items"],key=lambda e:e.get("lastTimestamp") or ""):
    print("    %-20s x%-2s %s" % (e["reason"], e.get("count",1), e["message"][:120]))'

echo; echo "## 4. 고아 프로세스를 누가 거두나: shareProcessNamespace false vs true"
for share in false true; do
cat <<Y | $K -n $NS apply -f - >/dev/null
apiVersion: v1
kind: Pod
metadata: {name: zombie-$share}
spec:
  nodeName: k8s-worker1
  terminationGracePeriodSeconds: 0
  shareProcessNamespace: $share
  containers: [{name: c, image: nginx:1.25.1-alpine, command: [sh, -c, "(sleep 1 &); exec sleep 3600"]}]
Y
done
$K -n $NS wait --for=condition=Ready pod/zombie-false pod/zombie-true --timeout=60s >/dev/null; sleep 4
echo "  컨테이너 명령: sh -c \"(sleep 1 &); exec sleep 3600\"  → 1초 뒤 끝난 sleep 1 은 부모를 잃고 PID 1 에게 넘어감"
for share in false true; do
  echo "  $(ts) zombie-$share: ps -o pid,ppid,stat,comm"
  $K -n $NS exec zombie-$share -- ps -o pid,ppid,stat,comm 2>&1 | sed 's/^/    /'
done

echo; echo "## 5. 정리"
$K delete ns $NS --wait=true >/dev/null; echo "  $(ts) 네임스페이스 $NS 삭제"
