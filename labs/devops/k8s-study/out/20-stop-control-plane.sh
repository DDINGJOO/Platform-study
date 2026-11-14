#!/usr/bin/env bash
# 컨트롤 플레인 구성 요소를 하나씩 멈춰 보는 실험 (마스터에서 실행). 정적 파드 매니페스트를 잠깐 옮겼다가 되돌린다.
set -u
M=/etc/kubernetes/manifests; B=/root/arch-exp-backup; O=/lab/arch-exp
ts(){ date '+%T'; }
sudo mkdir -p $B
restore_all(){ for f in kube-apiserver kube-scheduler kube-controller-manager; do [ -f $B/$f.yaml ] && sudo mv $B/$f.yaml $M/ && echo "$(ts) (안전장치) $f.yaml 되돌림"; done; }
trap restore_all EXIT
gone(){ for i in $(seq 1 45); do [ -z "$(sudo crictl ps --name "$1" -q)" ] && return 0; sleep 2; done; return 1; }
api_ready(){ for i in $(seq 1 90); do kubectl get --raw /readyz >/dev/null 2>&1 && return 0; sleep 2; done; return 1; }

{
echo "# E1 API 서버를 멈추면: kubectl 은? 돌던 파드는? ($(date '+%F %T %Z'))"
P=$(kubectl get pod -l app=myweb -o jsonpath='{.items[0].status.podIP}'); N=$(kubectl get pod -l app=myweb -o jsonpath='{.items[0].spec.nodeName}')
echo "$(ts) 대상 파드 IP $P ($N)"
curl -s -o /dev/null -w "$(ts) 멈추기 전: curl http://$P/ → %{http_code}\n" --max-time 3 http://$P/
echo "$(ts) master\$ sudo mv $M/kube-apiserver.yaml $B/"; sudo mv $M/kube-apiserver.yaml $B/
gone kube-apiserver; echo "$(ts) master\$ sudo crictl ps --name kube-apiserver → $(sudo crictl ps --name kube-apiserver -q | wc -l)개"
echo "$(ts) master\$ kubectl get nodes"; kubectl get nodes 2>&1 | tail -1
curl -s -o /dev/null -w "$(ts) API 서버 없이: curl http://$P/ → %{http_code}\n" --max-time 3 http://$P/
echo "$(ts) master\$ sudo crictl ps --name 'etcd|kube-scheduler|kube-controller' 로 남은 컨테이너"; sudo crictl ps -o json | python3 -c 'import json,sys;[print("   ",c["metadata"]["name"],c["state"]) for c in json.load(sys.stdin)["containers"] if c["metadata"]["name"] in ("etcd","kube-scheduler","kube-controller-manager")]'
echo "$(ts) 되돌리기: sudo mv $B/kube-apiserver.yaml $M/"; sudo mv $B/kube-apiserver.yaml $M/
api_ready; echo "$(ts) kubectl get --raw /readyz → $(kubectl get --raw /readyz 2>&1)"
kubectl get nodes 2>&1
} > $O/e1-apiserver.txt 2>&1
sleep 10

{
echo "# E2 스케줄러를 멈추면: 새 파드는? ($(date '+%F %T %Z'))"
echo "$(ts) master\$ sudo mv $M/kube-scheduler.yaml $B/"; sudo mv $M/kube-scheduler.yaml $B/
gone kube-scheduler; echo "$(ts) kube-scheduler 컨테이너 $(sudo crictl ps --name kube-scheduler -q | wc -l)개"
echo "$(ts) master\$ kubectl create deployment sched-test --image=nginx:1.25.1-alpine"; kubectl create deployment sched-test --image=nginx:1.25.1-alpine
sleep 20
echo "$(ts) master\$ kubectl get pods -l app=sched-test -o wide"; kubectl get pods -l app=sched-test -o wide
echo "$(ts) master\$ kubectl get events --field-selector involvedObject.kind=Pod | grep sched-test"; kubectl get events --field-selector involvedObject.kind=Pod 2>/dev/null | grep sched-test || echo "   (파드 이벤트 없음)"
echo "$(ts) 되돌리기: sudo mv $B/kube-scheduler.yaml $M/"; sudo mv $B/kube-scheduler.yaml $M/
kubectl wait --for=condition=Ready pod -l app=sched-test --timeout=120s >/dev/null 2>&1
echo "$(ts) master\$ kubectl get pods -l app=sched-test -o wide"; kubectl get pods -l app=sched-test -o wide
echo "$(ts) master\$ kubectl get events --field-selector involvedObject.kind=Pod --sort-by=.lastTimestamp | grep sched-test"; kubectl get events --field-selector involvedObject.kind=Pod --sort-by=.lastTimestamp | grep sched-test | head -5
kubectl delete deployment sched-test >/dev/null && echo "$(ts) sched-test 삭제"
} > $O/e2-scheduler.txt 2>&1
sleep 10

{
echo "# E3 컨트롤러 매니저를 멈추면: replicas 를 늘리거나 파드를 지우면? ($(date '+%F %T %Z'))"
echo "$(ts) master\$ kubectl get deploy,rs -l app=myweb"; kubectl get deploy myweb; kubectl get rs -l app=myweb
echo "$(ts) master\$ sudo mv $M/kube-controller-manager.yaml $B/"; sudo mv $M/kube-controller-manager.yaml $B/
gone kube-controller-manager; echo "$(ts) kube-controller-manager 컨테이너 $(sudo crictl ps --name kube-controller-manager -q | wc -l)개"
echo "$(ts) master\$ kubectl scale deploy myweb --replicas=7"; kubectl scale deploy myweb --replicas=7
D=$(kubectl get pod -l app=myweb -o jsonpath='{.items[0].metadata.name}')
echo "$(ts) master\$ kubectl delete pod $D"; kubectl delete pod $D --wait=true
sleep 20
echo "$(ts) master\$ kubectl get deploy myweb; kubectl get rs -l app=myweb; kubectl get pods -l app=myweb --no-headers | wc -l"; kubectl get deploy myweb; kubectl get rs -l app=myweb; echo "   myweb 파드 $(kubectl get pods -l app=myweb --no-headers | wc -l)개"
echo "$(ts) 되돌리기: sudo mv $B/kube-controller-manager.yaml $M/"; sudo mv $B/kube-controller-manager.yaml $M/
for i in $(seq 1 60); do [ "$(kubectl get deploy myweb -o jsonpath='{.status.readyReplicas}')" = 7 ] && break; sleep 2; done
echo "$(ts) master\$ kubectl get deploy myweb; kubectl get rs -l app=myweb"; kubectl get deploy myweb; kubectl get rs -l app=myweb
kubectl scale deploy myweb --replicas=5 >/dev/null; kubectl rollout status deploy/myweb --timeout=60s >/dev/null; echo "$(ts) myweb 을 5개로 되돌림: $(kubectl get deploy myweb --no-headers | awk '{print $2}')"
} > $O/e3-controller-manager.txt 2>&1
trap - EXIT
echo done
