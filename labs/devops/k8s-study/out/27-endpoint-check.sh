#!/usr/bin/env bash
# 27편 보강: kubelet 은 /var/run/... 으로, crictl 은 /run/... 으로 적혀 있는데 같은 소켓인가 (조회만, Mac 에서 실행)
cd "${LAB:?실습 저장소(./lab 이 있는 곳) 경로를 LAB 에 넣는다}"
echo "# 27편 보강 CRI 엔드포인트 경로 ($(date '+%F %T %Z'))"
./lab ssh 1 -- sudo bash -s <<'R'
echo "worker1\$ ls -ld /var/run"; ls -ld /var/run
echo "worker1\$ ls -l /run/containerd/containerd.sock"; ls -l /run/containerd/containerd.sock
echo "worker1\$ grep -E 'Endpoint' /var/lib/kubelet/config.yaml"; grep -E 'Endpoint' /var/lib/kubelet/config.yaml
echo "worker1\$ cat /etc/crictl.yaml"; cat /etc/crictl.yaml
R
