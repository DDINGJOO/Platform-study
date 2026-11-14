#!/usr/bin/env bash
# 실습 저장소의 shared/components/03-etcd-btree.sh 를 옮긴 것. 실습 저장소 루트에서 실행한다.
# etcd 의 저장 구조: 디스크의 B+트리(bbolt) 파일, 키마다 여러 리비전(MVCC), compaction, 쓰고 남은 빈 페이지 (Mac 에서 실행)
cd "$(dirname "$0")/../.."   # 실습 저장소 루트 (./lab 이 있는 곳)
K="./lab kubectl"
E=(-n kube-system exec etcd-k8s-master -- etcdctl --endpoints=https://127.0.0.1:2379 --cacert=/etc/kubernetes/pki/etcd/ca.crt --cert=/etc/kubernetes/pki/etcd/server.crt --key=/etc/kubernetes/pki/etcd/server.key)
KEY=/registry/deployments/default/myweb
kv(){ $K "${E[@]}" get $KEY "$@" -w json | python3 -c '
import json,sys,base64
d=json.load(sys.stdin); h=d["header"]
if not d.get("kvs"): print("  (값 없음) header.revision=",h["revision"]); sys.exit()
k=d["kvs"][0]; v=base64.b64decode(k["value"])
import re
m=re.search(rb"\x10(.)",v[v.find(b"spec"):] if b"spec" in v else v)
print("  create_revision=%s mod_revision=%s version=%s | 클러스터 현재 revision=%s" % (k["create_revision"],k["mod_revision"],k["version"],h["revision"]))'; }
echo "# etcd 저장 구조 ($(date '+%F %T %Z'))"
echo; echo "## 1. 디스크의 데이터 파일 (bbolt = B+트리 한 파일) 과 WAL"
./lab ssh master -- sudo sh -c 'ls -la /var/lib/etcd/member/snap/ | grep -E " db$"; ls /var/lib/etcd/member/wal/ | head -3; echo "WAL 파일 수: $(ls /var/lib/etcd/member/wal/*.wal | wc -l)"'
echo; echo "## 2. endpoint status: DB SIZE 와 IN USE"
$K "${E[@]}" endpoint status -w json | python3 -c '
import json,sys
s=json.load(sys.stdin)[0]["Status"]
db=s["dbSize"]; use=s.get("dbSizeInUse",0)
print("  revision=%s raftIndex=%s dbSize=%.1fMB dbSizeInUse=%.1fMB (빈 페이지 %.0f%%)" % (s["header"]["revision"],s["raftIndex"],db/1e6,use/1e6,100*(db-use)/db))'
echo; echo "## 3. 키 하나에 리비전이 여러 개 (MVCC): myweb Deployment"
kv
$K scale deploy myweb --replicas=6 >/dev/null; sleep 2; echo "  \$ kubectl scale deploy myweb --replicas=6"; kv
R6=$($K "${E[@]}" get $KEY -w json | python3 -c 'import json,sys;print(json.load(sys.stdin)["kvs"][0]["mod_revision"])')
$K scale deploy myweb --replicas=5 >/dev/null; sleep 2; echo "  \$ kubectl scale deploy myweb --replicas=5"; kv
echo "  같은 키를 --rev=$R6 (6개로 바꿨던 때) 로 읽기:"
$K "${E[@]}" get $KEY --rev=$R6 -w json | python3 -c '
import json,sys,base64
k=json.load(sys.stdin)["kvs"][0]; v=base64.b64decode(k["value"])
print("   mod_revision=%s version=%s 값 길이 %d바이트" % (k["mod_revision"],k["version"],len(v)))'
echo "  kubectl 로 보면 지금: replicas=$($K get deploy myweb -o jsonpath='{.spec.replicas}'), 그때 값은 etcd 에만 남아 있음"
echo; echo "## 4. 오래된 리비전은 compaction 으로 지워짐 (API 서버 --etcd-compaction-interval 기본 5m)"
echo "  22편 실험 때의 리비전 103241 로 읽기:"; $K "${E[@]}" get $KEY --rev=103241 2>&1 | tail -1 | sed 's/^/   /'
