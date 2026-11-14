#!/usr/bin/env bash
# CRI 의 두 서비스(RuntimeService / ImageService)와 노드의 이미지 저장소 (Mac 에서 실행)
cd "$(dirname "$0")/../.."   # 실습 저장소 루트 (./lab 이 있는 곳)
K="./lab kubectl"
echo "# E17 CRI ImageService 와 이미지 저장소 ($(date '+%F %T %Z'))"
echo; echo "## 1. 엔드포인트가 두 개로 나뉘어 있다 (지금은 같은 소켓)"
./lab ssh 1 -- sudo cat /etc/crictl.yaml
echo "kubelet 설정: $(./lab ssh 1 -- sudo grep -E 'containerRuntimeEndpoint|imageServiceEndpoint' /var/lib/kubelet/config.yaml | paste -sd' ' -)"
echo "kubelet --help: $(./lab ssh 1 -- kubelet --help 2>&1 | grep -E -- '--image-service-endpoint' | sed 's/^ *//' | cut -c1-200)"
echo; echo "## 2. 이미지 목록과 이미지 저장 공간 (ImageService: ListImages, ImageFsInfo)"
./lab ssh 1 -- sudo crictl images | awk '{print $1":"$2, $NF}' | column -t
./lab ssh 1 -- sudo crictl imagefsinfo | python3 -c 'import json,sys;d=json.load(sys.stdin)["status"]
for k in ("imageFilesystems","containerFilesystems"):
  for f in d.get(k,[]): print(k, f["fsId"]["mountpoint"], "used", round(int(f["usedBytes"]["value"])/1048576), "MiB")'
echo; echo "## 3. 이미지 → 컨테이너: overlayfs 스냅숏 (myweb 컨테이너 루트 파일시스템)"
P=$($K get pod -l app=myweb --field-selector spec.nodeName=k8s-worker1 -o jsonpath='{.items[0].metadata.name}')
CID=$($K get pod $P -o jsonpath='{.status.containerStatuses[0].containerID}'); CID=${CID#containerd://}
./lab ssh 1 -- sudo CID=$CID bash -s <<'R'
m=$(mount | grep "/k8s.io/$CID/rootfs")
echo "$m" | awk '{print "mount:", $1, $3, $5}'
echo "$m" | grep -oE 'lowerdir=[^,]+' | tr ':' '\n' | sed 's/lowerdir=//' | awk '{print "  읽기 전용 레이어(lowerdir):", $0}'
echo "$m" | grep -oE 'upperdir=[^,]+' | sed 's/upperdir=/  쓰기 레이어(upperdir): /'
R
echo; echo "## 4. 이미지 정리 기준 (kubelet 이미지 GC, /configz)"
$K get --raw /api/v1/nodes/k8s-worker1/proxy/configz | python3 -c 'import json,sys;c=json.load(sys.stdin)["kubeletconfig"];[print(f"  {k} = {c.get(k)}") for k in ("imageGCHighThresholdPercent","imageGCLowThresholdPercent","imageMinimumGCAge","imageMaximumGCAge","serializeImagePulls")]'
