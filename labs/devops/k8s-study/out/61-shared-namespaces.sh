#!/usr/bin/env bash
# 한 파드의 두 컨테이너가 리눅스 네임스페이스 중 무엇을 같이 쓰나: 컨테이너 안에서 /proc/self/ns 비교, 기본값과 shareProcessNamespace: true (Mac 에서 실행)
# 실습 저장소 루트에서 실행한다(./lab kubectl). 노드 접속 없이 kubectl exec 만 쓴다. 네임스페이스 blog-61 만 쓰고 지운다.
K="./lab kubectl"; NS=blog-61
echo "# 61 한 파드 두 컨테이너의 네임스페이스 ($(date '+%F %T %Z'))"
$K create ns $NS >/dev/null
for share in false true; do
cat <<Y | $K apply -n $NS -f - >/dev/null
apiVersion: v1
kind: Pod
metadata: {name: ns-share-$share}
spec:
  shareProcessNamespace: $share
  terminationGracePeriodSeconds: 1
  containers:
  - {name: c1, image: busybox:1.37, command: [sleep, "3600"]}
  - {name: c2, image: busybox:1.37, command: [sleep, "3601"]}
Y
done
for share in false true; do $K wait -n $NS pod/ns-share-$share --for=condition=Ready --timeout=90s >/dev/null; done
for share in false true; do
  P=ns-share-$share
  echo; echo "## shareProcessNamespace: $share (파드 $P, 노드 $($K get pod -n $NS $P -o jsonpath='{.spec.nodeName}'))"
  echo "  ns      c1                      c2                      같은가"
  for ns in net ipc uts pid mnt cgroup; do
    a=$($K exec -n $NS $P -c c1 -- readlink /proc/self/ns/$ns)
    b=$($K exec -n $NS $P -c c2 -- readlink /proc/self/ns/$ns)
    [ "$a" = "$b" ] && same=같음 || same=다름
    printf '  %-7s %-23s %-23s %s\n' $ns "$a" "$b" $same
  done
  for c in c1 c2; do
    echo "  [$c] hostname=$($K exec -n $NS $P -c $c -- hostname)"
    echo "  [$c] ps 로 보이는 프로세스(PID 명령, ps 자신 제외):$($K exec -n $NS $P -c $c -- ps -o pid,args | awk 'NR>1 && $2!="ps" {printf "  %s %s %s;", $1, $2, $3}')"
  done
done
$K delete ns $NS --wait=false >/dev/null
echo; echo "  네임스페이스 $NS 삭제 요청"
