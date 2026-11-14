#!/usr/bin/env bash
# 실습 저장소의 shared/components/21-etcd-restore-rehearsal.sh 를 옮긴 것. 실습 저장소 루트에서 실행한다.
# etcd 복원 리허설: 스냅숏 → API 서버 정지 → etcdutl 로 새 data-dir 에 복원 → etcd 매니페스트 hostPath 교체 → API 서버 재시작 → 스냅숏 뒤에 만든 객체가 사라졌는지 확인
# 마지막에 복원본을 원래 경로(/var/lib/etcd)로 옮겨 매니페스트·kubeadm-config 를 원래대로 둔다. 원래 데이터는 /var/lib/etcd-before-rehearsal 에 남긴다.
# 문서: kubernetes.io "Operating etcd clusters for Kubernetes" 의 Restoring an etcd cluster, etcd v3.6 op-guide/recovery (etcd-restore-sources/)
cd "$(dirname "$0")/../.."   # 실습 저장소 루트
K="./lab kubectl"; ts(){ date '+%T'; }; NS=w40-restore
E="--endpoints=127.0.0.1:2379 --cacert=/etc/kubernetes/pki/etcd/ca.crt --cert=/etc/kubernetes/pki/etcd/server.crt --key=/etc/kubernetes/pki/etcd/server.key"
rev(){ $K -n kube-system exec etcd-k8s-master -- etcdctl $E endpoint status -w json 2>/dev/null | python3 -c 'import json,sys;print(json.load(sys.stdin)[0]["Status"]["header"]["revision"])'; }
cms(){ $K -n $NS get cm -l lab/marker -o jsonpath='{range .items[*]}{.metadata.name} {end}'; }
restarts(){ $K -n kube-system get pod -l tier=control-plane -o jsonpath='{range .items[*]}{.metadata.labels.component}={.status.containerStatuses[0].restartCount} {end}'; }
waitapi(){ local t0=$SECONDS; until $K get --raw /readyz >/dev/null 2>&1; do sleep 2; done; echo "  $(ts) API 서버 /readyz ok ($((SECONDS-t0))초 기다림)"; }
echo "# etcd 복원 리허설 ($(date '+%F %T %Z'), etcd 3.7.0, 단일 멤버 stacked)"

echo; echo "## 1. 표식 → 스냅숏 → 표식"
$K create ns $NS >/dev/null
$K -n $NS create cm before-snapshot --from-literal=k=v >/dev/null; $K -n $NS label cm before-snapshot lab/marker=1 >/dev/null
echo "  $(ts) ConfigMap before-snapshot 생성, etcd revision $(rev)"
$K -n kube-system exec etcd-k8s-master -- etcdctl $E snapshot save /var/lib/etcd/rehearsal.db 2>&1 | grep -E 'Snapshot saved|Server version' | sed 's/^/  /'
$K -n kube-system exec etcd-k8s-master -- etcdutl snapshot status /var/lib/etcd/rehearsal.db -w table 2>&1 | sed 's/^/  /'
$K -n $NS create cm after-snapshot --from-literal=k=v >/dev/null; $K -n $NS label cm after-snapshot lab/marker=1 >/dev/null
echo "  $(ts) ConfigMap after-snapshot 생성(스냅숏 뒤), etcd revision $(rev)"
echo "  $(ts) 지금 표식: $(cms)"
echo "  $(ts) 컨트롤 플레인 재시작 수: $(restarts)"

echo; echo "## 2. 마스터: API 서버 정지 → etcdutl 복원 → hostPath 교체 → etcd 재시작 → API 서버 재시작"
./lab ssh master -- sudo bash -s <<'R'
ts(){ date '+%T'; }; B=/root/restore-rehearsal; mkdir -p $B
E="--endpoints=127.0.0.1:2379 --cacert=/etc/kubernetes/pki/etcd/ca.crt --cert=/etc/kubernetes/pki/etcd/server.crt --key=/etc/kubernetes/pki/etcd/server.key"
trap '[ -f $B/kube-apiserver.yaml ] && mv $B/kube-apiserver.yaml /etc/kubernetes/manifests/ && echo "  (trap) API 서버 매니페스트 되돌림"' EXIT
cp /etc/kubernetes/manifests/etcd.yaml $B/etcd.yaml.orig
mv /etc/kubernetes/manifests/kube-apiserver.yaml $B/
echo "  $(ts) master\$ mv /etc/kubernetes/manifests/kube-apiserver.yaml $B/"
until [ -z "$(crictl ps --name kube-apiserver -q)" ]; do sleep 1; done; echo "  $(ts) kube-apiserver 컨테이너 0개"
C=$(crictl ps --name '^etcd$' -q)
echo "  $(ts) master\$ crictl exec <etcd> etcdutl snapshot restore /var/lib/etcd/rehearsal.db --data-dir /var/lib/etcd/restored --name k8s-master --initial-cluster k8s-master=https://192.168.104.1:2380 --initial-advertise-peer-urls https://192.168.104.1:2380 --bump-revision 1000000000 --mark-compacted"
crictl exec $C etcdutl snapshot restore /var/lib/etcd/rehearsal.db --data-dir /var/lib/etcd/restored --name k8s-master --initial-cluster k8s-master=https://192.168.104.1:2380 --initial-advertise-peer-urls https://192.168.104.1:2380 --bump-revision 1000000000 --mark-compacted 2>&1 | tail -4 | cut -c1-220 | sed 's/^/    /'
mv /var/lib/etcd/restored /var/lib/etcd-restored
echo "  $(ts) 새 data-dir: $(find /var/lib/etcd-restored -maxdepth 3 | tr '\n' ' ')"
sed -i -E 's#^(\s+path: )/var/lib/etcd$#\1/var/lib/etcd-restored#' /etc/kubernetes/manifests/etcd.yaml
echo "  $(ts) etcd.yaml 바뀐 줄:"; diff $B/etcd.yaml.orig /etc/kubernetes/manifests/etcd.yaml | sed 's/^/    /'
systemctl restart kubelet; echo "  $(ts) master\$ systemctl restart kubelet"
until [ -n "$(crictl ps --name '^etcd$' -q)" ] && [ "$(crictl ps --name '^etcd$' -q)" != "$C" ] && crictl exec $(crictl ps --name '^etcd$' -q) etcdctl $E endpoint health >/dev/null 2>&1; do sleep 1; done
N=$(crictl ps --name '^etcd$' -q)
echo "  $(ts) 새 etcd 컨테이너 ${N:0:13} healthy"
crictl exec $N etcdctl $E endpoint status -w table 2>&1 | sed 's/^/    /'
crictl exec $N etcdctl $E member list -w table 2>&1 | sed 's/^/    /'
mv $B/kube-apiserver.yaml /etc/kubernetes/manifests/; echo "  $(ts) master\$ mv $B/kube-apiserver.yaml /etc/kubernetes/manifests/"
R
waitapi

echo; echo "## 3. 복원된 클러스터 확인"
echo "  $(ts) etcd revision $(rev)"
echo "  $(ts) 표식: $(cms)  (after-snapshot 이 없으면 스냅숏 시점으로 돌아간 것)"
sleep 20
echo "  $(ts) 노드: $($K get node --no-headers | awk '{print $1"="$2}' | tr '\n' ' ')"
echo "  $(ts) 컨트롤 플레인 재시작 수: $(restarts)"
echo "  $(ts) 컨트롤러 매니저 로그(복원 뒤, 410·relist·리더 관련):"
$K -n kube-system logs kube-controller-manager-k8s-master --since=3m 2>/dev/null | grep -i -E 'too old|compacted|Gone|leaderelection|lost|relist|watch.*closed' | cut -c1-200 | tail -6 | sed 's/^/    /'
echo "  $(ts) Running 아닌 파드: $($K get pod -A --no-headers | grep -v -E 'Running|Completed' | wc -l | tr -d ' ')개"

echo; echo "## 4. 복원본을 원래 경로로 옮겨 매니페스트를 원래대로 (원래 데이터는 /var/lib/etcd-before-rehearsal 로 보관)"
./lab ssh master -- sudo bash -s <<'R'
ts(){ date '+%T'; }; B=/root/restore-rehearsal
E="--endpoints=127.0.0.1:2379 --cacert=/etc/kubernetes/pki/etcd/ca.crt --cert=/etc/kubernetes/pki/etcd/server.crt --key=/etc/kubernetes/pki/etcd/server.key"
trap '[ -f $B/kube-apiserver.yaml ] && mv $B/kube-apiserver.yaml /etc/kubernetes/manifests/ && echo "  (trap) API 서버 매니페스트 되돌림"' EXIT
mv /etc/kubernetes/manifests/kube-apiserver.yaml $B/; until [ -z "$(crictl ps --name kube-apiserver -q)" ]; do sleep 1; done; echo "  $(ts) API 서버 정지"
mv /etc/kubernetes/manifests/etcd.yaml $B/etcd.yaml.restored; until [ -z "$(crictl ps --name '^etcd$' -q)" ]; do sleep 1; done; echo "  $(ts) etcd 정지"
rm -f /var/lib/etcd/rehearsal.db
mv /var/lib/etcd /var/lib/etcd-before-rehearsal && mv /var/lib/etcd-restored /var/lib/etcd && echo "  $(ts) /var/lib/etcd → /var/lib/etcd-before-rehearsal, /var/lib/etcd-restored → /var/lib/etcd"
cp $B/etcd.yaml.orig /etc/kubernetes/manifests/etcd.yaml; echo "  $(ts) 원래 etcd.yaml 복원 (hostPath /var/lib/etcd)"
until [ -n "$(crictl ps --name '^etcd$' -q)" ] && crictl exec $(crictl ps --name '^etcd$' -q) etcdctl $E endpoint health >/dev/null 2>&1; do sleep 1; done; echo "  $(ts) etcd healthy"
mv $B/kube-apiserver.yaml /etc/kubernetes/manifests/; echo "  $(ts) API 서버 매니페스트 되돌림"
R
waitapi
echo "  $(ts) etcd revision $(rev), 표식: $(cms)"
sleep 20
echo "  $(ts) 노드: $($K get node --no-headers | awk '{print $1"="$2}' | tr '\n' ' ')"
echo "  $(ts) Running 아닌 파드: $($K get pod -A --no-headers | grep -v -E 'Running|Completed' | wc -l | tr -d ' ')개"
echo "  $(ts) 컨트롤 플레인 재시작 수: $(restarts)"
echo; echo "## 5. 정리"
$K delete ns $NS --wait=true >/dev/null; echo "  $(ts) 네임스페이스 $NS 삭제 (원래 데이터 /var/lib/etcd-before-rehearsal 와 /root/restore-rehearsal 는 남겨 둠)"
