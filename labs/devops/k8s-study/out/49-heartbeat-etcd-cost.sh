#!/usr/bin/env bash
# 49편: 노드 하트비트가 etcd 에 얼마나 쓰는지 Node 객체와 Lease 객체를 나란히 잰다 (조회만, Mac 에서 실행)
# 실습 저장소 루트(./lab 이 있는 곳)에서 실행한다.
K="./lab kubectl"
E=(-n kube-system exec etcd-k8s-master -- etcdctl --endpoints=https://127.0.0.1:2379 --cacert=/etc/kubernetes/pki/etcd/ca.crt --cert=/etc/kubernetes/pki/etcd/server.crt --key=/etc/kubernetes/pki/etcd/server.key)
NODES="k8s-master k8s-worker1 k8s-worker2 k8s-worker3"
# etcd 키 하나의 값 크기(바이트), version(만든 뒤 쓴 횟수), mod_revision
kv(){ $K "${E[@]}" get "$1" -w json | python3 -c '
import json,sys,base64
d=json.load(sys.stdin); k=d["kvs"][0]
print(len(base64.b64decode(k["value"])), k["version"], k["mod_revision"], d["header"]["revision"])'; }

echo "# 49 노드 하트비트가 etcd 에 쓰는 양: Node 와 Lease (조회만, $(date '+%F %T %Z'))"

echo; echo "## 1. etcd 에 저장된 값의 크기 (protobuf 그대로, 바이트)"
for n in $NODES; do
  read nb _ _ _ < <(kv /registry/minions/$n)
  read lb _ _ _ < <(kv /registry/leases/kube-node-lease/$n)
  printf "  %-12s Node %6s B | Lease %4s B\n" "$n" "$nb" "$lb"
done

echo; echo "## 2. Node 객체가 큰 이유: k8s-worker1 의 JSON 에서 칸별 크기"
$K get node k8s-worker1 -o json --show-managed-fields | python3 -c '
import json,sys
o=json.load(sys.stdin); st=o["status"]; md=o["metadata"]
L=lambda x: len(json.dumps(x,separators=(",",":")))
print("  Node 전체 JSON %d B" % L(o))
print("    status.images      %5d B (이미지 %d개)" % (L(st.get("images",[])), len(st.get("images",[]))))
print("    status.conditions  %5d B (%d개)" % (L(st.get("conditions",[])), len(st.get("conditions",[]))))
print("    status 나머지      %5d B" % (L({k:v for k,v in st.items() if k not in ("images","conditions")})))
print("    metadata.managedFields %5d B (쓰는 주체 %s)" % (L(md.get("managedFields",[])), sorted({m["manager"] for m in md.get("managedFields",[])})))
print("    metadata 나머지    %5d B" % (L({k:v for k,v in md.items() if k!="managedFields"})))
print("    spec               %5d B" % L(o.get("spec",{})))'
$K -n kube-node-lease get lease k8s-worker1 -o json --show-managed-fields | python3 -c '
import json,sys
o=json.load(sys.stdin); md=o["metadata"]
L=lambda x: len(json.dumps(x,separators=(",",":")))
print("  Lease 전체 JSON %d B, spec %d B (쓰는 주체 %s)" % (L(o), L(o["spec"]), sorted({m["manager"] for m in md.get("managedFields",[])})))'

echo; echo "## 3. 60초 동안 etcd 에 쓰인 횟수: 키의 version 이 몇 번 올랐나"
T=$(mktemp -d)
for n in $NODES; do
  echo "$n $(kv /registry/minions/$n) $(kv /registry/leases/kube-node-lease/$n)" >> "$T/a"
done
t0=$(date +%s); sleep 60; t1=$(date +%s)
for n in $NODES; do
  echo "$n $(kv /registry/minions/$n) $(kv /registry/leases/kube-node-lease/$n)" >> "$T/b"
done
python3 - "$T/a" "$T/b" $((t1-t0)) <<'PY'
import sys
def load(p):
    d={}
    for l in open(p):
        f=l.split(); d[f[0]]=dict(nb=int(f[1]),nv=int(f[2]),rev=int(f[4]),lb=int(f[5]),lv=int(f[6]))
    return d
a,b,sec=load(sys.argv[1]),load(sys.argv[2]),int(sys.argv[3])
print("  경과 %d초" % sec)
tn=tl=bn=bl=0
for n in a:
    dn=b[n]["nv"]-a[n]["nv"]; dl=b[n]["lv"]-a[n]["lv"]
    tn+=dn; tl+=dl; bn+=dn*b[n]["nb"]; bl+=dl*b[n]["lb"]
    print("  %-12s Node version %6d → %6d (%+d) | Lease version %6d → %6d (%+d)" % (n,a[n]["nv"],b[n]["nv"],dn,a[n]["lv"],b[n]["lv"],dl))
revs=[b[n]["rev"] for n in b]; reva=[a[n]["rev"] for n in a]
print("  합계: Node 쓰기 %d번(약 %d B) | Lease 쓰기 %d번(약 %d B)" % (tn,bn,tl,bl))
print("  같은 시간 etcd 전체 revision(키·값 변경 번호) 증가: %+d" % (max(revs)-min(reva)))
PY
rm -rf "$T"

echo; echo "## 4. API 서버가 받은 하트비트 요청 수 (kube-apiserver /metrics, 기동 뒤 누적)"
$K get --raw /metrics | python3 -c '
import sys,re,time
tot={}; start=None
for l in sys.stdin:
    if l.startswith("process_start_time_seconds "): start=float(l.split()[1])
    if not l.startswith("apiserver_request_total{"): continue
    lab=dict(re.findall(r"(\w+)=\"([^\"]*)\"",l)); v=float(l.rsplit(" ",1)[1])
    if lab.get("resource")=="leases" and lab.get("verb")=="PUT": key="leases PUT (Lease 갱신, 리더 선출 포함)"
    elif lab.get("resource")=="nodes" and lab.get("subresource")=="status" and lab.get("verb")=="PATCH": key="nodes/status PATCH (NodeStatus 보고)"
    else: continue
    tot[key]=tot.get(key,0)+v
up=time.time()-start if start else 0
print("  API 서버 기동 뒤 %.0f분" % (up/60))
for k,v in tot.items(): print("  %-45s %8.0f번" % (k,v))'
echo "  kube-node-lease 밖의 Lease (리더 선출 등):"
$K get lease -A --no-headers | awk '$1!="kube-node-lease"{print "    " $1 "/" $2}'

echo; echo "## 5. etcd 가 DB 크기 한도에 닿으면 (etcd --help, endpoint status)"
$K -n kube-system exec etcd-k8s-master -- etcd --help 2>&1 | grep -A1 -E -- '^ *--quota-backend-bytes ' | sed 's/^ */  /'
$K "${E[@]}" endpoint status -w json | python3 -c '
import json,sys
s=json.load(sys.stdin)[0]["Status"]
print("  지금 dbSize=%.1fMB dbSizeInUse=%.1fMB quota=%s" % (s["dbSize"]/1e6, s.get("dbSizeInUse",0)/1e6, ("%.2fGiB" % (s["dbSizeQuota"]/2**30)) if s.get("dbSizeQuota") else "(필드 없음)"))'
