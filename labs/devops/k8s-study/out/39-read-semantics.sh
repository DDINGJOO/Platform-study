#!/usr/bin/env bash
# 39편을 쓰며 새로 만든 조회 전용 스크립트. 실습 저장소 루트(./lab 이 있는 곳)에서 실행한다 (Mac). 클러스터에 아무것도 쓰지 않는다.
# 같은 순간에 etcd 리비전, API 서버 watch 캐시의 위치, LIST 두 방식(resourceVersion=0 / 비움)이 돌려준 resourceVersion 을 나란히 보고
# 컨트롤러 매니저·스케줄러가 재시작 뒤 캐시 동기화를 기다린 로그와 API 서버 /readyz 의 관련 항목을 본다.
K="./lab kubectl"
E=(-n kube-system exec etcd-k8s-master -- etcdctl --endpoints=https://127.0.0.1:2379 --cacert=/etc/kubernetes/pki/etcd/ca.crt --cert=/etc/kubernetes/pki/etcd/server.crt --key=/etc/kubernetes/pki/etcd/server.key)
now(){ python3 -c 'import datetime;print(datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3])'; }
lrv(){ $K get --raw "/api/v1/pods$1" | python3 -c 'import json,sys;d=json.load(sys.stdin);print(d["metadata"]["resourceVersion"], "파드", len(d["items"]))'; }
erev(){ $K "${E[@]}" endpoint status -w json | python3 -c 'import json,sys;print(json.load(sys.stdin)[0]["Status"]["header"]["revision"])'; }
crv(){ $K get --raw /metrics | python3 -c '
import sys
for l in sys.stdin:
    if l.startswith("apiserver_watch_cache_resource_version{") and "resource=\"pods\"" in l and "group=\"\"" in l:
        print(int(float(l.split()[-1])))'; }
echo "# 읽기 방식에 따라 달라지는 resourceVersion, 캐시 동기화 대기 ($(date '+%F %T %Z'))"
echo "  (etcd 는 21:57 복원 리허설에서 리비전을 10억 올린 상태: shared/components/21-etcd-restore-rehearsal.txt)"
echo
echo "## 1. 차례로 읽기: ① LIST ?resourceVersion=0 (Any)  ② etcd 리비전  ③ LIST (resourceVersion 비움, Most recent)  ④ ① 다시  ⑤ watch 캐시 위치(pods 메트릭)"
for i in 1 2 3 4 5; do
  a=$(lrv '?resourceVersion=0'); ta=$(now)
  e=$(erev); te=$(now)
  c=$(lrv ''); tc=$(now)
  b=$(lrv '?resourceVersion=0'); tb=$(now)
  m=$(crv)
  echo "  [$i] ① $a ($ta) | ② etcd $e ($te) | ③ $c ($tc) | ④ $b ($tb) | ⑤ $m"
  sleep 3
done
echo
echo "## 2. 컨트롤러 매니저: 재시작 뒤 리더가 되고 캐시를 다 채운 다음에 컨트롤러를 돌린다 (로그 시각은 UTC)"
$K -n kube-system logs kube-controller-manager-k8s-master 2>&1 > /tmp/kcm.log
grep -m1 '"Starting" version' /tmp/kcm.log | cut -c1-120
grep -m1 'Successfully acquired lease' /tmp/kcm.log | cut -c1-120
grep -m1 'Waiting for caches to sync' /tmp/kcm.log | cut -c1-120
grep 'Caches are synced' /tmp/kcm.log | tail -1 | cut -c1-120
echo "  \"Waiting for caches to sync\" 줄 수: $(grep -c 'Waiting for caches to sync' /tmp/kcm.log), \"Caches are synced\" 줄 수: $(grep -c 'Caches are synced' /tmp/kcm.log)"
rm -f /tmp/kcm.log
echo
echo "## 3. 스케줄러도 같은 기록"
$K -n kube-system logs kube-scheduler-k8s-master 2>&1 > /tmp/ks.log
grep -m1 'Waiting for caches to sync' /tmp/ks.log | cut -c1-120
grep 'Caches are synced' /tmp/ks.log | tail -1 | cut -c1-120
grep -m1 'Successfully acquired lease' /tmp/ks.log | cut -c1-120
echo "  \"Waiting for caches to sync\" 줄 수: $(grep -c 'Waiting for caches to sync' /tmp/ks.log), \"Caches are synced\" 줄 수: $(grep -c 'Caches are synced' /tmp/ks.log)"
rm -f /tmp/ks.log
echo
echo "## 4. API 서버 /readyz?verbose 에서 캐시·informer 관련 항목"
$K get --raw '/readyz?verbose' | grep -i -E 'cache|informer|storage' | sed 's/^/  /'
