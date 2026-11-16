#!/usr/bin/env bash
# 확인: 시험용 CRD로 저장 버전을 v1→v2로 바꾸고, deprecated 경고·메트릭을 보고, StorageVersionMigration(1.37 GA)으로 etcd의 옛 버전 객체를 다시 쓰게 한다 (Mac 에서 실행)
# 실행: bash shared/why/08-api-versions-deprecation/04-crd-storage-migration-and-deprecation.sh 2>&1 | tee shared/why/08-api-versions-deprecation/04-crd-storage-migration-and-deprecation.txt
# 만드는 것: CRD widgets.why-api.example.com(클러스터 범위 객체), 네임스페이스 why-api 안의 Widget 2개, StorageVersionMigration 1개.
# 마이그레이션 대상은 이 CRD의 리소스(widgets)뿐이라 다른 객체는 건드리지 않는다. 끝에서 셋 다 지우고 why-api 네임스페이스도 지운다. etcd는 읽기만 한다.
set -u
cd /Users/dding/orca/workspaces/k8s/tang
K="./lab kubectl"; NS=why-api; G=why-api.example.com; CRD=widgets.$G; SVM=why-api-widgets
E=(-n kube-system exec etcd-k8s-master -- etcdctl --endpoints=https://127.0.0.1:2379
   --cacert=/etc/kubernetes/pki/etcd/ca.crt --cert=/etc/kubernetes/pki/etcd/server.crt --key=/etc/kubernetes/pki/etcd/server.key)
DECODE='
import json,sys,base64
def varint(b,i):
    r=s=0
    while True:
        c=b[i]; i+=1; r|=(c&0x7f)<<s; s+=7
        if c<0x80: return r,i
def fields(b):
    i=0; out={}
    while i<len(b):
        k,i=varint(b,i); f,t=k>>3,k&7
        if t==2:
            l,i=varint(b,i); out.setdefault(f,[]).append(b[i:i+l]); i+=l
        elif t==0:
            v,i=varint(b,i); out.setdefault(f,[]).append(v)
        else: break
    return out
d=json.load(sys.stdin); kv=(d.get("kvs") or [None])[0]
if kv is None: print("  %-55s (키 없음)" % sys.argv[1]); sys.exit()
v=base64.b64decode(kv["value"])
if v.startswith(b"k8s\x00"):
    tm=fields(fields(v[4:])[1][0]); print("  %-55s protobuf apiVersion=%s (mod_revision %s)" % (sys.argv[1], tm[1][0].decode(), kv["mod_revision"]))
else:
    o=json.loads(v); print("  %-55s JSON     apiVersion=%s (mod_revision %s)" % (sys.argv[1], o["apiVersion"], kv["mod_revision"]))
'
etcd_show(){ $K "${E[@]}" get "$1" -w json | python3 -c "$DECODE" "$1"; }
ts(){ date '+%T'; }
hash(){ python3 -c 'import hashlib,base64,sys; print(base64.b64encode(hashlib.sha256(sys.argv[1].encode()).digest()[:8]).decode())' "$1"; }
svh(){ $K get --raw /apis/$G/$1 2>/dev/null | python3 -c 'import json,sys; print(next((r.get("storageVersionHash","") for r in json.load(sys.stdin)["resources"] if r["name"]=="widgets"),"(없음)"))'; }
stored(){ $K get crd $CRD -o jsonpath='{.status.storedVersions}'; }
storage(){ $K get crd $CRD -o jsonpath='{range .spec.versions[*]}{.name}(served={.served},storage={.storage}{.deprecated}) {end}'; }
depmetric(){ $K get --raw /metrics | grep -E '^apiserver_requested_deprecated_apis' | sed 's/^/    /'; }

echo "# 04 CRD 저장 버전 변경 · deprecated 경고 · StorageVersionMigration ($(date '+%F %T %Z'))"
$K create namespace $NS --dry-run=client -o yaml | $K apply -f - >/dev/null
$K delete storageversionmigration $SVM --ignore-not-found >/dev/null; $K delete crd $CRD --ignore-not-found >/dev/null

echo; echo "## 0. 시작 전 apiserver_requested_deprecated_apis (내장 API 중 deprecated를 누가 불렀나)"
B=$(depmetric); echo "${B:-    (없음)}"

echo; echo "## 1. $(ts) CRD 생성: v1(storage) + v2, 두 버전 스키마 같음, conversion은 기본 None(apiVersion만 바꿈)"
cat <<Y | $K apply -f - | sed 's/^/  → /'
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata: {name: $CRD}
spec:
  group: $G
  scope: Namespaced
  names: {plural: widgets, singular: widget, kind: Widget}
  versions:
  - name: v1
    served: true
    storage: true
    schema: {openAPIV3Schema: {type: object, properties: {spec: {type: object, properties: {size: {type: string}}}}}}
  - name: v2
    served: true
    storage: false
    schema: {openAPIV3Schema: {type: object, properties: {spec: {type: object, properties: {size: {type: string}}}}}}
Y
$K wait --for=condition=Established crd/$CRD --timeout=60s | sed 's/^/  → /'
echo "  versions: $(storage)"; echo "  status.storedVersions: $(stored)"

echo; echo "## 2. $(ts) w1을 v1으로 생성 → etcd는 v1, v2 경로로 읽으면 v2"
printf 'apiVersion: %s/v1\nkind: Widget\nmetadata: {name: w1, namespace: %s}\nspec: {size: small}\n' $G $NS | $K create -f - | sed 's/^/  → /'
etcd_show /registry/$G/widgets/$NS/w1
for v in v1 v2; do echo "  GET /apis/$G/$v/.../w1 → apiVersion $($K get --raw /apis/$G/$v/namespaces/$NS/widgets/w1 | python3 -c 'import json,sys; print(json.load(sys.stdin)["apiVersion"])')"; done
echo "  discovery storageVersionHash: v1 경로 $(svh v1), v2 경로 $(svh v2) | 계산 v1=$(hash $G/v1/Widget) v2=$(hash $G/v2/Widget)"

echo; echo "## 3. $(ts) 저장 버전을 v2로 바꾼다 (v1 storage=false, v2 storage=true)"
$K patch crd $CRD --type=json -p '[{"op":"replace","path":"/spec/versions/0/storage","value":false},{"op":"replace","path":"/spec/versions/1/storage","value":true}]' | sed 's/^/  → /'
sleep 3
echo "  versions: $(storage)"; echo "  status.storedVersions: $(stored)   ← etcd에 v1 객체가 남아 있을 수 있으니 v1을 지우지 않는다"
echo "  discovery storageVersionHash: $(svh v1) (계산 v2=$(hash $G/v2/Widget))"
printf 'apiVersion: %s/v1\nkind: Widget\nmetadata: {name: w2, namespace: %s}\nspec: {size: large}\n' $G $NS | $K create -f - | sed 's/^/  → w2를 v1으로 생성: /'
etcd_show /registry/$G/widgets/$NS/w1
etcd_show /registry/$G/widgets/$NS/w2
echo "  → 같은 리소스인데 etcd에 v1 객체와 v2 객체가 섞여 있다. 저장 버전을 바꿔도 기존 객체는 다시 쓰이기 전까지 옛 버전 그대로."

echo; echo "## 4. $(ts) 이 상태에서 v1을 CRD에서 빼려고 하면"
$K patch crd $CRD --type=json -p '[{"op":"remove","path":"/spec/versions/0"}]' 2>&1 | sed 's/^/  → /'

echo; echo "## 5. $(ts) v1을 deprecated로 표시 → 요청마다 Warning 헤더, 메트릭"
$K patch crd $CRD --type=json -p '[{"op":"add","path":"/spec/versions/0/deprecated","value":true}]' | sed 's/^/  → /'
sleep 3
echo "  \$ kubectl get widgets.v1.$G -n $NS   (stderr 포함)"
$K get widgets.v1.$G -n $NS 2>&1 | sed 's/^/    /'
echo "  \$ kubectl get widgets.v2.$G -n $NS   (stderr 포함)"
$K get widgets.v2.$G -n $NS 2>&1 | sed 's/^/    /'
echo "  응답 헤더 (curl로 직접, 마스터의 admin.conf 인증서 사용):"
./lab ssh master -- sudo bash -s <<R 2>/dev/null | sed 's/^/    /'
KC=/etc/kubernetes/admin.conf
grep client-certificate-data \$KC | awk '{print \$2}' | base64 -d > /tmp/why-api.crt
grep client-key-data \$KC | awk '{print \$2}' | base64 -d > /tmp/why-api.key
curl -s -D - -o /dev/null --cacert /etc/kubernetes/pki/ca.crt --cert /tmp/why-api.crt --key /tmp/why-api.key https://127.0.0.1:6443/apis/$G/v1/namespaces/$NS/widgets | grep -iE '^(HTTP|warning|content-type)'
rm -f /tmp/why-api.crt /tmp/why-api.key
R
echo "  kube-apiserver /metrics:"
depmetric
$K get --raw /metrics | grep -E "^apiserver_request_total\{.*group=\"$G\"" | sed 's/^/    /'

echo; echo "## 6. $(ts) StorageVersionMigration 생성 (storagemigration.k8s.io/v1, 대상 group=$G resource=widgets)"
cat <<Y | $K create -f - | sed 's/^/  → /'
apiVersion: storagemigration.k8s.io/v1
kind: StorageVersionMigration
metadata: {name: $SVM}
spec:
  resource: {group: $G, resource: widgets}
Y
for i in $(seq 1 90); do
  s=$($K get storageversionmigration $SVM -o jsonpath='{.status.conditions[?(@.type=="Succeeded")].status}' 2>/dev/null)
  f=$($K get storageversionmigration $SVM -o jsonpath='{.status.conditions[?(@.type=="Failed")].status}' 2>/dev/null)
  [ "$s" = "True" ] || [ "$f" = "True" ] && break; sleep 2
done
echo "  $(ts) 상태:"
$K get storageversionmigration $SVM -o json | python3 -c '
import json,sys; o=json.load(sys.stdin); st=o.get("status",{})
for c in st.get("conditions",[]): print("    condition %-10s %-6s %s %s" % (c["type"], c["status"], c.get("reason",""), c.get("message","")[:120]))
print("    status의 다른 필드:", {k:v for k,v in st.items() if k!="conditions"})'

echo; echo "## 7. 마이그레이션 뒤 etcd와 storedVersions"
etcd_show /registry/$G/widgets/$NS/w1
etcd_show /registry/$G/widgets/$NS/w2
echo "  status.storedVersions: $(stored)"
echo "  StorageVersionMigration 객체 자체는 어떤 버전으로 저장됐나 (v1으로 만들었지만):"
etcd_show /registry/storageversionmigrations/$SVM

echo; echo "## 8. $(ts) 이제 v1 서빙을 끄고 CRD에서 v1을 뺀다"
$K patch crd $CRD --type=json -p '[{"op":"replace","path":"/spec/versions/0/served","value":false}]' | sed 's/^/  → /'
sleep 2
echo "  GET /apis/$G/v1/namespaces/$NS/widgets → $($K get --raw /apis/$G/v1/namespaces/$NS/widgets 2>&1 | head -1)"
$K patch crd $CRD --type=json -p '[{"op":"remove","path":"/spec/versions/0"}]' 2>&1 | sed 's/^/  → /'
echo "  versions: $(storage) | storedVersions: $(stored)"
echo "  $(ts) w1을 v2로 읽기: $($K get widgets.v2.$G -n $NS w1 -o jsonpath='{.apiVersion} size={.spec.size}')"

echo; echo "## 9. 정리"
$K delete storageversionmigration $SVM 2>&1 | sed 's/^/  /'
$K delete crd $CRD 2>&1 | sed 's/^/  /'
$K delete namespace $NS --wait=true 2>&1 | sed 's/^/  /'
echo "  남은 것: crd $($K get crd $CRD 2>&1 | grep -c NotFound)=NotFound, ns $($K get ns $NS 2>&1 | grep -c NotFound)=NotFound"
