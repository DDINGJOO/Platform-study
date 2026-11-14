#!/usr/bin/env bash
# 실습 저장소의 shared/components/19-scheduler-steps.sh 를 옮긴 것. 실습 저장소 루트에서 실행한다.
# 스케줄러 동작 순서 확인: 노드 정보를 매번 API 서버에 묻나(캐시), 바인딩은 누가 etcd 에 쓰나, 런타임 쪽 OCI 스펙 (Mac 에서 실행)
# 실험 전용 네임스페이스 st-demo 에서만 파드를 만들고 지운다.
cd "$(dirname "$0")/../.."   # 실습 저장소 루트 (./lab 이 있는 곳)
K="./lab kubectl"; ts(){ date '+%T'; }
NS=st-demo; IMG=registry.k8s.io/pause:3.10.2
smetrics(){ ./lab ssh master -- sudo bash -s <<'R'
d=$(mktemp -d); grep client-certificate-data /etc/kubernetes/admin.conf | awk '{print $2}' | base64 -d > $d/c; grep client-key-data /etc/kubernetes/admin.conf | awk '{print $2}' | base64 -d > $d/k
curl -sk --cert $d/c --key $d/k https://127.0.0.1:10259/metrics; rm -rf $d
R
}
# API 서버가 받은 nodes 요청 수 (verb 별) 와 pods/binding POST 수
areq(){ $K get --raw /metrics | python3 -c '
import sys,re,collections
c=collections.Counter()
for l in sys.stdin:
    if not l.startswith("apiserver_request_total{"): continue
    lab=dict(re.findall(r"(\w+)=\"([^\"]*)\"",l)); v=float(l.rsplit(" ",1)[1])
    if lab.get("resource")=="nodes" and lab.get("subresource","")=="": c["nodes "+lab["verb"]]+=v
    if lab.get("resource")=="pods" and lab.get("subresource")=="binding": c["pods/binding "+lab["verb"]]+=v
print(" ".join("%s=%d"%(k,c[k]) for k in sorted(c)))'; }

echo "# 스케줄러 동작 순서 확인 ($(date '+%F %T %Z'))"
echo; echo "## 1. 스케줄러가 들고 있는 캐시 (scheduler_cache_size)"
smetrics | grep '^scheduler_cache_size' | sed 's/^/  /'

$K create ns $NS >/dev/null
echo; echo "## 2. 파드 5개를 스케줄하는 동안 API 서버가 받은 nodes 요청과 바인딩 요청"
A0=$(areq); echo "$(ts) 전: $A0"
for i in 1 2 3 4 5; do
cat <<Y | $K -n $NS apply -f - >/dev/null
apiVersion: v1
kind: Pod
metadata: {name: st-$i}
spec: {containers: [{name: c, image: $IMG}]}
Y
done
sleep 6
A1=$(areq); echo "$(ts) 후: $A1"
$K -n $NS get pod -o wide --no-headers | awk '{print "  "$1, $3, "NODE="$7}'
echo "  (nodes get 은 kubelet 들이 자기 노드를 주기적으로 읽는 요청도 섞인 수. list 가 늘지 않으면 스케줄러가 파드마다 노드 목록을 다시 받지 않았다는 뜻)"

echo; echo "## 3. 컨테이너 런타임 쪽: 이미지 서비스·런타임 서비스(CRI) 와 OCI 런타임 스펙"
W=$($K -n $NS get pod st-1 -o jsonpath='{.spec.nodeName}'); CID=$($K -n $NS get pod st-1 -o jsonpath='{.status.containerStatuses[0].containerID}' | sed 's#containerd://##')
echo "$(ts) st-1 → $W, 컨테이너 ID ${CID:0:13}"
./lab ssh ${W#k8s-} -- sudo bash -s <<R
echo "$W\$ crictl version";  crictl version 2>/dev/null | sed 's/^/  /'
echo "$W\$ crictl images | grep pause  (CRI ImageService: ListImages)"; crictl images 2>/dev/null | grep -E 'IMAGE|pause' | sed 's/^/  /'
f=/run/containerd/io.containerd.runtime.v2.task/k8s.io/$CID/config.json
echo "$W\$ ls \$(dirname \$f)  (containerd 가 runc 에 넘기는 OCI 번들)"; ls \$(dirname \$f) | sed 's/^/  /'
echo "$W\$ config.json 의 ociVersion·process.args·root"; python3 -c "import json;c=json.load(open('\$f'));print('  ociVersion',c['ociVersion'],'| args',c['process']['args'],'| root',c['root'])"
echo "$W\$ runc --version"; runc --version | head -2 | sed 's/^/  /'
R

echo; echo "## 4. 정리"
$K delete ns $NS --wait=true >/dev/null; echo "$(ts) 네임스페이스 $NS 삭제"
