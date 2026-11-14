#!/usr/bin/env bash
# 48편: 멤버가 하나뿐인 etcd 에서도 Raft 가 도는지 조회만으로 확인한다 (클러스터를 바꾸지 않음, Mac 에서 실행)
# 실습 저장소 루트(./lab 이 있는 곳)에서 실행한다.
K="./lab kubectl"
E=(-n kube-system exec etcd-k8s-master -- etcdctl --endpoints=https://127.0.0.1:2379 --cacert=/etc/kubernetes/pki/etcd/ca.crt --cert=/etc/kubernetes/pki/etcd/server.crt --key=/etc/kubernetes/pki/etcd/server.key)
status(){ $K "${E[@]}" endpoint status -w json | python3 -c '
import json,sys
s=json.load(sys.stdin)[0]["Status"]; h=s["header"]
print("  member_id=%x leader=%x raftTerm=%s raftIndex=%s raftAppliedIndex=%s isLearner=%s" % (h["member_id"],s["leader"],s["raftTerm"],s["raftIndex"],s.get("raftAppliedIndex"),s.get("isLearner",False)))'; }
rev(){ $K "${E[@]}" endpoint status -w json | python3 -c 'import json,sys;print(json.load(sys.stdin)[0]["Status"]["header"]["revision"])'; }
METRICS='^(etcd_server_(has_leader|is_leader|leader_changes_seen_total|proposals_committed_total|proposals_applied_total|proposals_pending|proposals_failed_total|heartbeat_send_failures_total)|etcd_disk_wal_fsync_duration_seconds_count|etcd_disk_backend_commit_duration_seconds_count|etcd_network_peer_sent_bytes_total|etcd_network_peer_received_bytes_total|etcd_mvcc_put_total|etcd_mvcc_txn_total|etcd_mvcc_delete_total) '
metrics(){ ./lab ssh master -- curl -s http://127.0.0.1:2381/metrics | grep -E "$METRICS"; }

echo "# 48 멤버 하나짜리 etcd 의 Raft 상태 조회 ($(date '+%F %T %Z'))"

echo; echo "## 1. 멤버 목록"
$K "${E[@]}" member list -w table

echo; echo "## 2. endpoint status: 자기 자신이 리더인가, term 과 index"
status

echo; echo "## 3. Raft 타이머와 스냅숏 주기: 매니페스트에 적힌 값과 etcd 기본값"
echo "  etcd.yaml 에서 heartbeat-interval / election-timeout 을 적은 줄 수: $(./lab ssh master -- sudo grep -c -E 'heartbeat-interval|election-timeout' /etc/kubernetes/manifests/etcd.yaml)"
echo "  etcd.yaml 의 snapshot-count / initial-cluster / listen-peer-urls:"
./lab ssh master -- sudo grep -E 'snapshot-count|initial-cluster=|listen-peer-urls' /etc/kubernetes/manifests/etcd.yaml | sed 's/^ */    /'
echo "  etcd --help (기본값):"
$K -n kube-system exec etcd-k8s-master -- etcd --help 2>&1 | grep -A1 -E -- '^ *--(heartbeat-interval|election-timeout) ' | sed 's/^ */    /'

echo; echo "## 4. 이번 기동에서 선거를 치른 기록 (etcd 로그에서 raft 상태 전환 줄만)"
$K -n kube-system logs etcd-k8s-master 2>&1 | grep -E 'became (pre-candidate|candidate|leader)|elected leader|starting a new election' | python3 -c '
import json,sys
for line in sys.stdin:
    try: d=json.loads(line)
    except Exception: continue
    print("  %s %s" % (d.get("ts","")[:23], d.get("msg","")))'

echo; echo "## 5. 30초 동안 Raft 와 디스크가 처리한 양 (metrics 127.0.0.1:2381)"
status | sed 's/^  /  [시작] /'; r0=$(rev)
T=$(mktemp -d)
metrics > "$T/a.txt"; t0=$(date +%s)
sleep 30
metrics > "$T/b.txt"; t1=$(date +%s)
status | sed 's/^  /  [끝]   /'; r1=$(rev)
echo "  같은 동안 etcd revision(키·값 변경 번호) 증가: $((r1-r0))"
echo "  경과 $((t1-t0))초. 지표별 시작값 → 끝값 (차이):"
python3 - "$T/a.txt" "$T/b.txt" <<'PY'
import sys
def load(p):
    d={}
    for l in open(p):
        k,v=l.rsplit(" ",1); d[k]=float(v)
    return d
a,b=load(sys.argv[1]),load(sys.argv[2])
for k in sorted(set(a)|set(b)):
    x,y=a.get(k),b.get(k)
    if x is None or y is None: print("    %-60s %s → %s" % (k,x,y)); continue
    print("    %-60s %.0f → %.0f (%+.0f)" % (k,x,y,y-x))
PY
echo "  peer 로 주고받은 바이트 지표 줄 수(피어가 없으면 0): $(grep -c '^etcd_network_peer' "$T/b.txt")"
rm -rf "$T"

echo; echo "## 6. 2380(멤버끼리, Raft) 과 2379(클라이언트) 의 연결"
./lab ssh master -- sudo ss -Htln 'sport = :2380' | awk '{print "  LISTEN " $4}'
echo "  2380 에 맺어진 연결 수: $(./lab ssh master -- sudo ss -Htn state established 'sport = :2380' | wc -l | tr -d ' ')"
echo "  2379 에 맺어진 연결 수: $(./lab ssh master -- sudo ss -Htn state established 'sport = :2379' | wc -l | tr -d ' ')"

echo; echo "## 7. API 서버가 고를 수 있는 저장소 (kube-apiserver --help)"
$K -n kube-system exec kube-apiserver-k8s-master -- kube-apiserver --help 2>&1 | grep -A1 -E -- '--storage-backend ' | sed 's/^ */  /'
