#!/usr/bin/env bash
# 실습 저장소의 shared/components/12-etcd-compaction-defrag.sh 를 옮긴 것. 실습 저장소 루트에서 실행한다.
# compaction 은 옛 리비전을 지울 뿐 파일을 줄이지 않는다, defrag 를 해야 줄어든다. 그리고 etcd 자체는 저장 데이터를 암호화하지 않는다 (Mac 에서 실행)
cd "$(dirname "$0")/../.."   # 실습 저장소 루트 (./lab 이 있는 곳)
K="./lab kubectl"; ts(){ date '+%T'; }
E=(-n kube-system exec etcd-k8s-master -- etcdctl --endpoints=https://127.0.0.1:2379 --cacert=/etc/kubernetes/pki/etcd/ca.crt --cert=/etc/kubernetes/pki/etcd/server.crt --key=/etc/kubernetes/pki/etcd/server.key)
st(){ $K "${E[@]}" endpoint status -w json | python3 -c '
import json,sys
s=json.load(sys.stdin)[0]["Status"]; db=s["dbSize"]; u=s.get("dbSizeInUse",0)
print("revision=%s dbSize=%.1fMB inUse=%.1fMB 빈 페이지=%.0f%%" % (s["header"]["revision"],db/1e6,u/1e6,100*(db-u)/db))'; }
fs(){ ./lab ssh master -- sudo stat -c '%s' /var/lib/etcd/member/snap/db | awk '{printf "%.1fMB", $1/1e6}'; }
echo "# etcd compaction 과 defrag ($(date '+%F %T %Z'))"
echo; echo "## 1. API 서버가 하는 자동 compaction 설정"
echo "  kube-apiserver --etcd-compaction-interval: 매니페스트에 $( ./lab ssh master -- sudo grep -c etcd-compaction-interval /etc/kubernetes/manifests/kube-apiserver.yaml)개(= 기본값 5m0s, 22편에서 --help 로 확인)"
echo; echo "## 2. defrag 전"
echo "$(ts) $(st) | 파일 크기 $(fs)"
echo; echo "## 3. defrag (단일 멤버라 잠깐 읽기·쓰기가 멈춤)"
T0=$(date +%s.%N); $K "${E[@]}" defrag 2>&1 | tail -1; echo "  걸린 시간 약 $(python3 -c "import time;print(round(time.time()-$T0,1))")초 (kubectl exec 왕복 포함)"
echo; echo "## 4. defrag 뒤"
echo "$(ts) $(st) | 파일 크기 $(fs)"
echo "  API 서버 /readyz: $($K get --raw /readyz)"
echo; echo "## 5. etcd 자체는 저장 데이터를 암호화하지 않음: 파일 안에서 평범한 객체 이름이 그대로 보임"
./lab ssh master -- sudo sh -c 'printf "  db 파일 안의 \"myweb\" 문자열 수: "; grep -a -c myweb /var/lib/etcd/member/snap/db'
echo "  etcd 플래그 중 저장 암호화 관련: $(./lab ssh master -- sudo grep -ciE 'encrypt' /etc/kubernetes/manifests/etcd.yaml)개 (TLS 관련은 --cert-file·--client-cert-auth 등 전송 구간 설정)"
