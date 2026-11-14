#!/usr/bin/env bash
# 실습 저장소의 shared/why/04-dockershim-removal/02-docker-sock.sh 를 옮긴 것. 실습 저장소 루트에서 실행한다.
# dockershim 이 빠진 노드에서 docker.sock 을 마운트하던 파드는 어떻게 되나 (Mac 에서 실행, 네임스페이스 w3-sock 만 쓰고 지움)
# ① hostPath type: Socket 으로 요구 → 마운트 실패  ② type 없이 → containerd 가 빈 디렉터리를 만들어 붙임, 클라이언트는 연결 실패
cd "$(dirname "$0")/../../.."   # 실습 저장소 루트
K="./lab kubectl"; ts(){ date '+%T'; }; NS=w3-sock
echo "# docker.sock 을 마운트하는 파드 ($(date '+%F %T %Z'))"
echo; echo "## 0. 노드에 docker.sock 이 있나 (worker2)"
./lab ssh worker2 -- sudo bash -s <<'R'
ls -l /var/run/docker.sock 2>&1 | sed 's/^/  /'; ls -l /run/containerd/containerd.sock | sed 's/^/  /'
R
$K create ns $NS >/dev/null
cat <<Y | $K -n $NS apply -f - >/dev/null
apiVersion: v1
kind: Pod
metadata: {name: sock-typed}
spec:
  nodeName: k8s-worker2
  terminationGracePeriodSeconds: 0
  containers: [{name: c, image: nginx:1.25.1-alpine, command: [sleep, "3600"], volumeMounts: [{name: s, mountPath: /var/run/docker.sock}]}]
  volumes: [{name: s, hostPath: {path: /var/run/docker.sock, type: Socket}}]
---
apiVersion: v1
kind: Pod
metadata: {name: sock-untyped}
spec:
  nodeName: k8s-worker2
  terminationGracePeriodSeconds: 0
  containers: [{name: c, image: nginx:1.25.1-alpine, command: [sleep, "3600"], volumeMounts: [{name: s, mountPath: /var/run/docker.sock}]}]
  volumes: [{name: s, hostPath: {path: /var/run/docker.sock}}]
Y
echo; echo "## 1. 파드 두 개 (둘 다 worker2, hostPath /var/run/docker.sock)"
echo "  sock-typed: type: Socket / sock-untyped: type 없음"
sleep 12
$K -n $NS get pod -o wide
echo "$(ts) sock-typed 이벤트:"
$K -n $NS get events --field-selector involvedObject.name=sock-typed -o jsonpath='{range .items[*]}    {.reason}: {.message}{"\n"}{end}' | sort -u | cut -c1-200
echo "$(ts) sock-untyped 안에서: ls -ld /var/run/docker.sock"
$K -n $NS exec sock-untyped -- ls -ld /var/run/docker.sock 2>&1 | sed 's/^/    /'
echo "$(ts) sock-untyped 안에서: [ -S /var/run/docker.sock ] (유닉스 소켓인가)"
$K -n $NS exec sock-untyped -- sh -c '[ -S /var/run/docker.sock ] && echo "소켓" || echo "소켓 아님 (Docker 클라이언트가 붙을 데몬이 없음)"' 2>&1 | sed 's/^/    /'
echo "$(ts) worker2 에 남은 것:"
./lab ssh worker2 -- sudo bash -s <<'R'
ls -ld /var/run/docker.sock 2>&1 | sed 's/^/    /'
R
echo; echo "## 2. 정리"
$K delete ns $NS --wait=true >/dev/null
./lab ssh worker2 -- sudo bash -s <<'R'
[ -d /var/run/docker.sock ] && rmdir /var/run/docker.sock && echo "  worker2: 파드가 만든 빈 디렉터리 /var/run/docker.sock 삭제"
ls -ld /var/run/docker.sock 2>&1 | sed 's/^/  /'
R
echo "$(ts) 네임스페이스 $NS 삭제"
