#!/usr/bin/env bash
# 27편 보강: 같은 이미지를 쓰는 컨테이너들이 읽기 전용 레이어(lowerdir)를 같이 쓰고 쓰기 레이어(upperdir)만 따로 갖는가
# Mac 에서 실행. 네임스페이스 w27 만 만들고 끝나면 지운다. worker1 의 myweb 은 조회만 한다.
cd "${LAB:?실습 저장소(./lab 이 있는 곳) 경로를 LAB 에 넣는다}"
K="./lab kubectl"; ts(){ date '+%T'; }
echo "# 27편 보강 overlayfs 레이어 공유 ($(date '+%F %T %Z'))"
$K create ns w27 >/dev/null
for n in share-a share-b; do
cat <<Y | $K -n w27 apply -f - >/dev/null
apiVersion: v1
kind: Pod
metadata: {name: $n}
spec:
  nodeSelector: {kubernetes.io/hostname: k8s-worker1}
  terminationGracePeriodSeconds: 5
  containers:
  - {name: web, image: nginx:1.25.1-alpine}
Y
done
$K -n w27 wait --for=condition=Ready pod/share-a pod/share-b --timeout=120s >/dev/null
echo "$(ts) w27/share-a, w27/share-b Ready (둘 다 worker1, nginx:1.25.1-alpine)"
$K -n w27 exec share-a -- sh -c 'echo hello > /only-in-a.txt'
echo "$(ts) share-a 안에서만 /only-in-a.txt 를 만듦"

layers(){ # $1=네임스페이스 $2=파드
  local CID; CID=$($K -n $1 get pod $2 -o jsonpath='{.status.containerStatuses[0].containerID}'); CID=${CID#containerd://}
  ./lab ssh 1 -- sudo CID=$CID bash -s <<'R'
m=$(mount | grep "/k8s.io/$CID/rootfs")
up=$(echo "$m" | grep -oE 'upperdir=[^,]+' | sed 's/upperdir=//')
echo "  lowerdir 스냅숏: $(echo "$m" | grep -oE 'lowerdir=[^,]+' | tr ':' '\n' | grep -oE 'snapshots/[0-9]+' | sed 's#snapshots/##' | paste -sd' ' -)"
echo "  upperdir 스냅숏: $(echo "$up" | grep -oE 'snapshots/[0-9]+' | sed 's#snapshots/##')  (안의 파일: $(ls -A $up | paste -sd' ' -))"
R
}
M=$($K get pod -l app=myweb --field-selector spec.nodeName=k8s-worker1 -o jsonpath='{.items[0].metadata.name}')
echo; echo "## default/$M (worker1, nginx:1.25.1-alpine)"; layers default $M
echo; echo "## w27/share-a"; layers w27 share-a
echo; echo "## w27/share-b"; layers w27 share-b

echo; echo "## 정리"
$K delete ns w27 --wait=true >/dev/null && echo "$(ts) 네임스페이스 w27 삭제"
