#!/usr/bin/env bash
# 40편: etcd 복원 리허설(실습 저장소 shared/components/21-etcd-restore-rehearsal.sh, 2026-11-14 21:57~21:59 KST) 뒤에 남은 흔적을 조회만 해서 모은다.
# 실습 저장소 루트(./lab 이 있는 곳)에서 실행한다. 클러스터를 바꾸지 않는다(get, logs, journalctl, crictl inspecti, grep 만).
[ -x ./lab ] || { echo "실습 저장소 루트에서 실행한다"; exit 1; }
K="./lab kubectl"
E="--endpoints=127.0.0.1:2379 --cacert=/etc/kubernetes/pki/etcd/ca.crt --cert=/etc/kubernetes/pki/etcd/server.crt --key=/etc/kubernetes/pki/etcd/server.key"
echo "# etcd 복원 리허설 뒤의 흔적 ($(date '+%F %T %Z'), 조회만)"

echo; echo "## 1. etcd 이미지(registry.k8s.io/etcd:3.7.0-0)의 층 (마스터 crictl inspecti 의 history)"
./lab ssh master -- sudo bash -s <<'R'
crictl inspecti registry.k8s.io/etcd:3.7.0-0 | python3 -c '
import json,sys
c=json.load(sys.stdin)["info"]["imageSpec"]
for h in c.get("history",[]): print("  "+h.get("created_by","")[:100])
print("  Cmd="+str(c["config"].get("Cmd"))+" WorkingDir="+str(c["config"].get("WorkingDir")))'
R

echo; echo "## 2. etcd.yaml 에서 복원 명령에 옮겨 쓴 값 (마스터, 지금 파일은 리허설 전 원본과 같다)"
./lab ssh master -- sudo bash -s <<'R'
grep -n -E -- '--name=|--data-dir=|--initial-cluster=|--initial-advertise-peer-urls=|--initial-cluster-token|path: /var/lib/etcd' /etc/kubernetes/manifests/etcd.yaml | sed 's/^/  /'
grep -c -- '--initial-cluster-token' /etc/kubernetes/manifests/etcd.yaml | sed 's/^/  --initial-cluster-token 줄 수: /'
diff -q /root/restore-rehearsal/etcd.yaml.orig /etc/kubernetes/manifests/etcd.yaml >/dev/null && echo "  (diff) 리허설 전 원본 etcd.yaml.orig 와 같음"
R

echo; echo "## 3. 멤버 ID: 복원 전 기록 / 지금 / peer URL 과 토큰으로 계산한 값"
awk -F'│' '/127.0.0.1:2379/ {gsub(/ /,""); print "  복원 전 (shared/arch-exp/e6-etcd-ssot.txt, 15:17): ID="$3" RAFT_TERM="$12" RAFT_INDEX="$13}' shared/arch-exp/e6-etcd-ssot.txt
$K -n kube-system exec etcd-k8s-master -- etcdctl $E endpoint status -w json 2>/dev/null | python3 -c '
import json,sys
s=json.load(sys.stdin)[0]["Status"]; h=s["header"]
print("  지금: member_id=%x cluster_id=%x raftTerm=%d raftIndex=%d revision=%d" % (h["member_id"], h["cluster_id"], s["raftTerm"], s["raftIndex"], h["revision"]))'
python3 - <<'P'
import hashlib
m = hashlib.sha1(b"https://192.168.104.1:2380" + b"etcd-cluster").digest()[:8]
c = hashlib.sha1(m).digest()[:8]
print("  계산: sha1(peer URL + 토큰 etcd-cluster) 앞 8바이트 = %s, sha1(멤버 ID) 앞 8바이트 = %s" % (m.hex(), c.hex()))
P

echo; echo "## 4. etcd 로그: 복원본 data-dir 로 마지막에 다시 뜬 때 (지금 etcd 컨테이너, 시각은 UTC)"
$K -n kube-system logs etcd-k8s-master 2>/dev/null | grep -E '"restarting local member"|"restored last compact revision"|"kvstore restored"|became leader at term' | head -4 \
  | python3 -c '
import json,sys
for l in sys.stdin:
    d=json.loads(l); t=d.get("ts","")[11:23]
    rest={k:v for k,v in d.items() if k in ("cluster-id","local-member-id","restored-compact-revision","current-rev")}
    print("  "+t+" "+d.get("msg","")+" "+json.dumps(rest,ensure_ascii=False))'

echo; echo "## 5. containerd 기록: etcd.yaml 의 hostPath 를 바꾸고 kubelet 을 재시작한 21:57:35~21:57:48 (마스터, KST, ID 는 앞 12자)"
./lab ssh master -- sudo bash -s <<'R'
journalctl -u containerd --since "2026-11-14 21:57:35" --until "2026-11-14 21:57:48" --no-pager -o cat \
 | grep -E 'ee65cf7ef789|689de7d0ca40|06f24a742b52|e30eb998fc86|a5c090702bdc' \
 | grep -E 'received container exit|StopContainer for .* (with timeout|failed)|RunPodSandbox for name|attempt|StartContainer for .* returns|CreateContainer within sandbox .* for container name' \
 | sed -E 's/^time="2026-11-14T([0-9:.]{12})[0-9]*\+09:00" level=[a-z]+ msg="/\1 /; s/\\"//g; s/([0-9a-f]{12})[0-9a-f]{52}/\1/g; s/  id:[0-9a-f]+//; s/exited_at:\{[^}]*\}//; s/"$//' | cut -c1-150 | sed 's/^/  /'
R
echo "  (ee65cf7ef789 = 리허설 전부터 돌던 etcd 컨테이너, 06f24a742b52·e30eb998fc86·a5c090702bdc = 새 hostPath 의 etcd 컨테이너 attempt 0·1·2)"

echo; echo "## 6. 스케줄러·컨트롤러 매니저: API 서버가 멈춘 동안 리더 Lease 를 갱신하지 못하고 재시작 (마스터 /var/log/pods, 시각은 KST)"
./lab ssh master -- sudo bash -s <<'R'
S=$(ls -d /var/log/pods/kube-system_kube-scheduler-k8s-master_*/kube-scheduler)
C=$(ls -d /var/log/pods/kube-system_kube-controller-manager-k8s-master_*/kube-controller-manager)
echo "  [kube-scheduler 1.log 끝]"
grep -h -E 'Failed to renew lease|Leaderelection lost' $S/1.log | sed -E 's/^2026-11-14T([0-9:.]{12})[0-9]*\+09:00 stderr F [IEW][0-9]{4} [0-9:.]+ +[0-9]+ /\1 /' | cut -c1-130 | sed 's/^/    /'
echo "  [kube-scheduler 2.log 처음]"; head -1 $S/2.log | sed -E 's/^2026-11-14T([0-9:.]{12})[0-9]*\+09:00 stderr F [IEW][0-9]{4} [0-9:.]+ +[0-9]+ /\1 /' | cut -c1-130 | sed 's/^/    /'
echo "  [kube-controller-manager 2.log: 21:57:17 에 새로 시작한 컨테이너]"
grep -h -E '"Starting" version|Attempting to acquire|Successfully acquired lease' $C/2.log | sed -E 's/^2026-11-14T([0-9:.]{12})[0-9]*\+09:00 stderr F [IEW][0-9]{4} [0-9:.]+ +[0-9]+ /\1 /' | cut -c1-130 | sed 's/^/    /'
R

echo; echo "## 7. calico-kube-controllers: 복원 전 리비전으로 watch 를 이으려다 \"too old resource version\" (시각은 UTC, 각 줄 앞의 \"Watch has expired, triggering full resync.\" 는 줄임)"
P=$($K -n kube-system get pod -l k8s-app=calico-kube-controllers -o name)
echo "  $P 시작 $($K -n kube-system get $P -o jsonpath='{.status.startTime} {.spec.nodeName} 재시작 {.status.containerStatuses[0].restartCount}')"
$K -n kube-system logs $P --since-time=2026-11-14T12:57:45Z 2>/dev/null | grep 'too old resource version' \
 | sed -E 's/^2026-11-14 ([0-9:.]+) \[INFO\]\[[0-9]+\] kube-controllers\/watchercache.go [0-9]+: /\1 /; s/ cacheID=[0-9]+//; s/Watch has expired, triggering full resync. //' | sed 's/^/  /'
echo "  Full resync is required 줄 수: $($K -n kube-system logs $P --since-time=2026-11-14T12:57:45Z 2>/dev/null | grep -c 'Full resync is required')"
