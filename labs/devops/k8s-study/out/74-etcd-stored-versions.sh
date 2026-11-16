#!/usr/bin/env bash
# 확인: etcd의 /registry 아래 모든 값을 읽어 리소스마다 "어떤 apiVersion으로 저장돼 있나"를 센다. 조회만 한다 (Mac 에서 실행)
# 실행: bash shared/why/08-api-versions-deprecation/03-etcd-stored-versions.sh | tee shared/why/08-api-versions-deprecation/03-etcd-stored-versions.txt
# 객체 이름은 찍지 않고 리소스별 개수만 찍는다.
set -u
cd /Users/dding/orca/workspaces/k8s/tang
K="./lab kubectl"
E=(-n kube-system exec etcd-k8s-master -- etcdctl --endpoints=https://127.0.0.1:2379
   --cacert=/etc/kubernetes/pki/etcd/ca.crt --cert=/etc/kubernetes/pki/etcd/server.crt --key=/etc/kubernetes/pki/etcd/server.key)
J=$(mktemp)

echo "# 03 etcd에 실제로 저장된 apiVersion 집계 ($(date '+%F %T %Z'))"
echo "  API 서버 --encryption-provider-config 플래그 수: $($K -n kube-system get pod kube-apiserver-k8s-master -o jsonpath='{.spec.containers[0].command}' | grep -o encryption-provider-config | wc -l | tr -d ' ')"
echo "  API 서버 --storage-media-type 플래그 수: $($K -n kube-system get pod kube-apiserver-k8s-master -o jsonpath='{.spec.containers[0].command}' | grep -o storage-media-type | wc -l | tr -d ' ') (없으면 기본 protobuf)"
$K "${E[@]}" get /registry --prefix -w json > "$J"

python3 - "$J" <<'P'
import json,sys,base64,collections
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
kvs=json.load(open(sys.argv[1])).get("kvs",[])
by=collections.defaultdict(collections.Counter); fmt=collections.Counter()
for kv in kvs:
    key=base64.b64decode(kv["key"]).decode(errors="replace"); v=base64.b64decode(kv["value"])
    seg=key.split("/")
    label = seg[2]+"/"+seg[3] if ("." in seg[2] or seg[2] in ("services",)) and len(seg)>3 else seg[2]
    try:
        if v.startswith(b"k8s:enc:"):
            fmt["암호화"]+=1; by[label]["(암호화)"]+=1; continue
        if v.startswith(b"k8s\x00"):
            tm=fields(fields(v[4:])[1][0]); gv=tm[1][0].decode(); kind=tm[2][0].decode(); fmt["protobuf"]+=1
        else:
            o=json.loads(v); gv=o.get("apiVersion","?"); kind=o.get("kind","?"); fmt["JSON"]+=1
        by[label][gv+" "+kind]+=1
    except Exception as e:
        fmt["기타"]+=1; by[label]["(해석 못 함)"]+=1
print("\n## 1. 형식별 키 수 (총 %d)" % len(kvs))
for k,n in fmt.most_common(): print("  %-10s %d" % (k,n))
print("\n## 2. 키 접두어(리소스)별 저장 apiVersion")
print("  %-52s %5s  %s" % ("접두어 /registry/...", "개수", "저장된 apiVersion kind"))
for label in sorted(by):
    c=by[label]
    print("  %-52s %5d  %s" % (label, sum(c.values()), ", ".join("%s(%d)" % (g,n) if len(c)>1 else g for g,n in c.most_common())))
allgv=collections.Counter()
for c in by.values():
    for g,n in c.items(): allgv[g.split(" ")[0]]+=n
print("\n## 3. 저장 apiVersion 별 합계")
for g,n in sorted(allgv.items()): print("  %-40s %d" % (g,n))
pre=[g for g in allgv if any(t in g.split("/")[-1] for t in ("alpha","beta"))]
print("\n## 4. alpha/beta 버전으로 저장된 것:", pre if pre else "없음")
P
rm -f "$J"
echo
echo "## 5. 지금 서빙하는 groupVersion (비교용)"
$K api-versions | tr '\n' ' ' | sed 's/^/  /'; echo
