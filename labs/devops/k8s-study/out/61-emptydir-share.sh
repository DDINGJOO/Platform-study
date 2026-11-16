#!/usr/bin/env bash
# 같은 파드의 두 컨테이너가 파일을 나누려면: 각자 만든 /www 는 따로 보이고, emptyDir 볼륨을 양쪽에 마운트하면 같이 보이는가 (Mac 에서 실행)
# 실습 저장소 루트에서 실행한다(./lab kubectl). 네임스페이스 blog-61 만 쓰고 지운다.
K="./lab kubectl"; NS=blog-61
echo "# 61 emptyDir 로 파일 나누기 ($(date '+%F %T %Z'))"
$K create ns $NS >/dev/null 2>&1 || $K get ns $NS >/dev/null
cat <<'Y' | $K apply -n $NS -f - >/dev/null
apiVersion: v1
kind: Pod
metadata: {name: share-files}
spec:
  terminationGracePeriodSeconds: 1
  volumes:
  - {name: shared, emptyDir: {}}
  containers:
  - name: c1
    image: busybox:1.37
    command: [sh, -c, 'mkdir -p /www && exec sleep 3600']
    volumeMounts: [{name: shared, mountPath: /shared}]
  - name: c2
    image: busybox:1.37
    command: [sh, -c, 'mkdir -p /www && exec sleep 3600']
    volumeMounts: [{name: shared, mountPath: /shared}]
Y
$K wait -n $NS pod/share-files --for=condition=Ready --timeout=90s >/dev/null
echo; echo "## c1 이 두 곳에 파일을 쓴다"
echo '  $ kubectl exec share-files -c c1 -- sh -c "echo from-c1 > /www/a.txt; echo from-c1 > /shared/a.txt"'
$K exec -n $NS share-files -c c1 -- sh -c 'echo from-c1 > /www/a.txt; echo from-c1 > /shared/a.txt'
echo; echo "## c2 에서 본다"
echo "  c2 의 /www   : [$($K exec -n $NS share-files -c c2 -- ls /www/ | tr '\n' ' ')]"
echo "  c2 의 /shared: [$($K exec -n $NS share-files -c c2 -- ls /shared/ | tr '\n' ' ')]  내용: $($K exec -n $NS share-files -c c2 -- cat /shared/a.txt)"
echo; echo "## 두 컨테이너의 /shared 마운트 (mount 표에서)"
for c in c1 c2; do echo "  [$c] $($K exec -n $NS share-files -c $c -- sh -c "grep ' /shared ' /proc/mounts | cut -d' ' -f1-3")"; done
$K delete ns $NS --wait=false >/dev/null
echo; echo "  네임스페이스 $NS 삭제 요청"
