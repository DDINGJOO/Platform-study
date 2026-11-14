#!/usr/bin/env bash
# 43-pause-vs-app-kill 의 sb-demo 파드(worker1, 2026-11-14 21:40:16~21:40:31 KST)를 containerd·Calico CNI·kubelet 로그로 한 줄에 놓는다 (조회만 한다)
# 실습 저장소 루트(./lab 이 있는 곳)에서 bash <이 파일> 로 실행 (Mac). 파드와 네임스페이스는 이미 지워졌고 노드 로그만 읽는다.
# 샌드박스 ID 6e1464df433e(attempt 0), 6c69b5d1cf56(attempt 1), web 컨테이너 ID bf3cec712f08(0)·93ee38c5f48c(1)·a7d46be8b6b1(2)
echo "# 43편 보강: sb-demo 파드에서 앱 kill 과 pause kill 때 오간 호출 ($(date '+%F %T %Z')), Mac 에서 ./lab ssh worker1 로 조회"
echo "# 긴 ID 는 앞 12자만 남기고 RunPodSandbox 줄의 uid·namespace 는 뺐다. [containerd] = journalctl -u containerd, [calico-cni] = /var/log/calico/cni/cni.log, [kubelet] = journalctl -u kubelet"
./lab ssh worker1 -- sudo bash -s <<'R'
IDS='6e1464df433e|6c69b5d1cf56|bf3cec712f08|93ee38c5f48c|a7d46be8b6b1'
{
journalctl -u containerd --since "2026-11-14 21:40:16" --until "2026-11-14 21:40:31" --no-pager -o cat \
  | grep -E 'RunPodSandbox|StopPodSandbox|TearDown|CreateContainer|StartContainer|StopContainer|received (sandbox |container )?exit event' \
  | grep -E "sb-demo|$IDS" | grep -v 'received sandbox container exit event' \
  | sed -E 's/^time="[0-9-]+T([0-9:.]{12})[0-9]*\+09:00" level=info msg=/\1 [containerd] /; s/ (exited_at|monitor_name|pid)[:=].*$//'
grep -E "$IDS" /var/log/calico/cni/cni.log | awk '$2>="21:40:16" && $2<"21:40:31"' \
  | grep -E 'Releasing IP address\(es\)|Released address using handleID|Reassigning existing IP|Calico CNI IPAM request|Auto assigning IP|Calico CNI using IPs' \
  | sed -E 's/^2026-11-14 ([0-9:.]{12}) \[(INFO|WARNING)\]\[[0-9]+\] /\1 [calico-cni] /; s/ (Namespace|WorkloadEndpoint|HandleID|Workload|ips|assignArgs)=.*$//'
journalctl -u kubelet --since "2026-11-14 21:40:16" --until "2026-11-14 21:40:31" --no-pager -o cat \
  | grep 'sb-demo' | grep -E 'CrashLoopBackOff' | head -1 \
  | sed -E 's/^E1114 ([0-9:.]{12})[0-9]* +[0-9]+ /\1 [kubelet] /; s/(container=web).*$/\1/'
} | sort | sed -E 's/([0-9a-f]{12})[0-9a-f]{52}/\1…/g; s/\\"/"/g; s/  uid:"[^"]*"  namespace:"w1-pause"//' | python3 -c 'import sys; [print(l.rstrip("\n")[:185]) for l in sys.stdin]'
R
