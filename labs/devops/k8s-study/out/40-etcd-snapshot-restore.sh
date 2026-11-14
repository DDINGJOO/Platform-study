#!/usr/bin/env bash
# 실습 저장소의 shared/components/17-etcd-snapshot-restore.sh 를 옮긴 것. 실습 저장소 루트에서 실행한다.
# etcd 백업·복원: 예전 버전(etcd 3.5)식 명령을 우리 etcd 3.7.0 에 그대로 쳐 보고, 되는 방법으로 백업 → 상태 확인 → 임시 폴더에 복원 (Mac 에서 실행, 운영 데이터는 건드리지 않음)
cd "$(dirname "$0")/../.."   # 실습 저장소 루트 (./lab 이 있는 곳)
K="./lab kubectl"
P=(-n kube-system exec etcd-k8s-master --)
C=(--endpoints=127.0.0.1:2379 --cacert=/etc/kubernetes/pki/etcd/ca.crt --cert=/etc/kubernetes/pki/etcd/server.crt --key=/etc/kubernetes/pki/etcd/server.key)
echo "# etcd snapshot save & restore ($(date '+%F %T %Z'))"
echo; echo "## 1. 예전 버전(etcd 3.5)식 명령 그대로 (sh -c \"ETCDCTL_API=3 etcdctl …\")"
$K "${P[@]}" sh -c "ETCDCTL_API=3 etcdctl ${C[*]} snapshot save /var/lib/etcd/snapshot.db" 2>&1 | tail -2 | sed 's/^/  /'
echo "  etcd 이미지 버전: $($K -n kube-system get pod etcd-k8s-master -o jsonpath='{.spec.containers[0].image}')"
echo; echo "## 2. 셸 없이 etcdctl 을 바로 실행 (v3 API 는 3.4 부터 기본이라 ETCDCTL_API=3 도 필요 없음)"
$K "${P[@]}" etcdctl "${C[@]}" snapshot save /var/lib/etcd/snapshot.db 2>&1 | grep -vE '^\{' | sed 's/^/  /'
echo; echo "## 3. 스냅숏 확인 (etcdutl)"
$K "${P[@]}" etcdutl snapshot status /var/lib/etcd/snapshot.db -w table 2>&1 | sed 's/^/  /'
echo; echo "## 4. 복원은 etcdutl 로 (etcdctl 쪽 restore 는 있나?)"
echo "  etcdctl snapshot 하위 명령: $($K "${P[@]}" etcdctl snapshot --help 2>&1 | awk '/Available Commands|COMMANDS/{f=1;next} f&&NF{print $1}' | head -4 | paste -sd' ' -)"
echo "  \$ etcdutl snapshot restore /var/lib/etcd/snapshot.db --data-dir /var/lib/etcd/restore-test   (운영 데이터와 다른 임시 폴더)"
$K "${P[@]}" etcdutl snapshot restore /var/lib/etcd/snapshot.db --data-dir /var/lib/etcd/restore-test 2>&1 | grep -oE '"msg":"[^"]+"' | sort -u | head -6 | sed 's/^/    /'
echo "  복원된 폴더: $(./lab ssh master -- sudo sh -c 'find /var/lib/etcd/restore-test -maxdepth 3 | sed s#/var/lib/etcd/## | paste -sd" " -')"
echo; echo "## 5. 실제 복원이라면 (실행하지 않음): API 서버·etcd 정적 파드 매니페스트를 잠시 빼고 → etcd.yaml 의 hostPath 를 restore 폴더로 바꾸거나 /var/lib/etcd 를 교체 → 매니페스트를 되돌림"
echo; echo "## 6. 정리: 스냅숏과 임시 복원 폴더 삭제"
./lab ssh master -- sudo rm -rf /var/lib/etcd/snapshot.db /var/lib/etcd/restore-test && echo "  삭제 완료: $(./lab ssh master -- sudo ls /var/lib/etcd)"
