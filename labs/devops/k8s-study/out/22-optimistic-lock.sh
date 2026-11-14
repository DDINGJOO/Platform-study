#!/usr/bin/env bash
# 22편 보충: resourceVersion 으로 하는 낙관적 동시성 제어. 같은 버전을 읽은 두 쓰기 가운데 늦은 쪽이 409 를 받는가
# w22 네임스페이스 안에서만 ConfigMap 하나를 만들고 끝나면 네임스페이스째 지운다. (Mac 에서 실행)
cd "$(dirname "$0")/../.."   # 실습 저장소 루트 (./lab 이 있는 곳)
K="./lab kubectl"; ts(){ date '+%T'; }; NS=w22; T=$(mktemp -d)
E=(-n kube-system exec etcd-k8s-master -- etcdctl --endpoints=https://127.0.0.1:2379 --cacert=/etc/kubernetes/pki/etcd/ca.crt --cert=/etc/kubernetes/pki/etcd/server.crt --key=/etc/kubernetes/pki/etcd/server.key)
trap '$K delete ns $NS --ignore-not-found --wait=false >/dev/null 2>&1; rm -rf $T' EXIT
etcdkv(){ $K "${E[@]}" get /registry/configmaps/$NS/occ-demo -w json | python3 -c 'import json,sys;k=json.load(sys.stdin)["kvs"][0];print("create_revision=%s mod_revision=%s version=%s"%(k["create_revision"],k["mod_revision"],k["version"]))'; }
echo "# 22편 보충: resourceVersion 과 409 Conflict ($(date '+%F %T %Z'))"
$K create ns $NS >/dev/null
echo "$(ts) mac\$ kubectl -n $NS create configmap occ-demo --from-literal=v=1"; $K -n $NS create configmap occ-demo --from-literal=v=1
echo "$(ts) kubectl resourceVersion=$($K -n $NS get cm occ-demo -o jsonpath='{.metadata.resourceVersion}') | etcd $(etcdkv)"
echo; echo "$(ts) 사용자 A 와 B 가 같은 버전을 읽어 둔다: kubectl get cm occ-demo -o json > a.json, b.json"
$K -n $NS get cm occ-demo -o json > $T/a.json; cp $T/a.json $T/b.json
echo "  a.json·b.json 의 resourceVersion: $(python3 -c "import json;print(json.load(open('$T/a.json'))['metadata']['resourceVersion'])")"
python3 - "$T" <<'PY'
import json,sys; T=sys.argv[1]
for f,v in (("a","2"),("b","3")):
    d=json.load(open(f"{T}/{f}.json")); d["data"]["v"]=v; json.dump(d,open(f"{T}/{f}.json","w"))
PY
echo; echo "$(ts) A: v=2 로 고쳐 kubectl replace -f a.json"; $K replace -f $T/a.json 2>&1 | sed 's/^/  /'
echo "$(ts) kubectl resourceVersion=$($K -n $NS get cm occ-demo -o jsonpath='{.metadata.resourceVersion}') | etcd $(etcdkv)"
echo; echo "$(ts) B: 예전 버전을 들고 v=3 으로 고쳐 kubectl replace -f b.json"; $K replace -f $T/b.json 2>&1 | sed 's/^/  /'
echo "$(ts) 지금 값: v=$($K -n $NS get cm occ-demo -o jsonpath='{.data.v}') | kubectl resourceVersion=$($K -n $NS get cm occ-demo -o jsonpath='{.metadata.resourceVersion}') | etcd $(etcdkv)"
echo; echo "$(ts) 같은 요청을 resourceVersion 없이 보내면 (B 가 버전을 지우고 다시 보낸 경우)"
python3 -c "import json;d=json.load(open('$T/b.json'));d['metadata'].pop('resourceVersion');json.dump(d,open('$T/c.json','w'))"
$K replace -f $T/c.json 2>&1 | sed 's/^/  /'
echo "$(ts) 지금 값: v=$($K -n $NS get cm occ-demo -o jsonpath='{.data.v}') | etcd $(etcdkv)"
$K delete ns $NS --wait=true >/dev/null && echo "$(ts) 네임스페이스 $NS 삭제"
trap - EXIT; rm -rf $T
