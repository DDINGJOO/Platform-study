#!/usr/bin/env bash
# OCI 표준이 노드 안에서 어디에 보이는지 확인한다: 이미지 형식(image-spec), 런타임(runtime-spec, runc), 번들 config.json (Mac 에서 실행)
cd "$(dirname "$0")/../.."   # 실습 저장소 루트 (./lab 이 있는 곳)
K="./lab kubectl"
P=$($K get pod -l app=myweb --field-selector spec.nodeName=k8s-worker1 -o jsonpath='{.items[0].metadata.name}')
CID=$($K get pod $P -o jsonpath='{.status.containerStatuses[0].containerID}'); CID=${CID#containerd://}
IMG=$($K get pod $P -o jsonpath='{.spec.containers[0].image}')
echo "# OCI 는 어디에 있나 ($(date '+%F %T %Z')), 대상: k8s-worker1 의 $P (이미지 $IMG)"
echo; echo "## 0. API 서버가 아는 런타임"
$K get node k8s-worker1 -o jsonpath='{.status.nodeInfo.containerRuntimeVersion}{"\n"}'
./lab ssh 1 -- sudo CID="$CID" bash -s <<'REMOTE'
echo; echo "## 1. 노드의 containerd 와 runc 버전 (runc 의 spec = 따르는 OCI runtime-spec 버전)"
containerd --version; runc --version
echo; echo "## 2. containerd 가 컨테이너를 만들 때 부르는 런타임 (containerd config dump)"
containerd config dump | grep -nE 'default_runtime_name|runtime_type|BinaryName|SystemdCgroup' | head
echo; echo "## 3. 파드마다 shim 프로세스 (containerd-shim-runc-v2)"
echo "shim 수: $(ps -eo args | grep -c '[c]ontainerd-shim-runc-v2')"
ps -eo pid,args | grep '[c]ontainerd-shim-runc-v2' | head -2 | cut -c1-110
echo; echo "## 4. 이미지 형식: 매니페스트 mediaType (OCI image-spec 인지 Docker v2 인지)"
ctr -n k8s.io images ls | awk 'NR==1 || (/nginx|calico\/node|kube-proxy|pause/ && $1 !~ /^sha256/) {print $1, $2}' | grep -v @sha256 | head -8
echo; echo "## 5. runc 가 읽는 OCI 번들 (runtime-spec 의 config.json + rootfs)"
B=/run/containerd/io.containerd.runtime.v2.task/k8s.io/$CID
echo "\$ ls $B"; ls $B
python3 - "$B/config.json" <<'PY'
import json,sys
c=json.load(open(sys.argv[1]))
print("ociVersion   =", c["ociVersion"])
print("process.args =", c["process"]["args"])
print("root.path    =", c["root"]["path"])
print("namespaces   =", [n["type"] for n in c["linux"]["namespaces"]])
print("cgroupsPath  =", c["linux"].get("cgroupsPath"))
print("resources    =", {k: c["linux"]["resources"].get(k) for k in ("cpu","memory")})
PY
REMOTE
