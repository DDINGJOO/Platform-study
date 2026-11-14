#!/usr/bin/env bash
# 31-ip-lifecycle 의 ipam-demo 파드(worker1, 15:26:36~15:27:30 KST)를 containerd 로그와 Calico CNI 로그로 한 줄에 놓는다 (조회만 한다)
# 실습 저장소 루트(./lab 이 있는 곳)에서 bash <이 파일> 로 실행 (Mac)
SB=347b3b3ed2f4   # ipam-demo 의 sandbox id 앞 12자 (31-ip-lifecycle.txt 의 containerID 와 같다)
echo "# 31편 보강: ipam-demo 파드의 CRI 호출과 CNI ADD·DEL 순서 ($(date '+%F %T %Z')), Mac 에서 ./lab ssh 1 로 worker1 조회"
echo "# 긴 ID 는 앞 12자만 남겼다. [containerd] = journalctl -u containerd, [calico-cni] = /var/log/calico/cni/cni.log"
./lab ssh 1 -- sudo SB=$SB bash -s <<'R'
{
journalctl -u containerd --since "2026-11-14 15:26:36" --until "2026-11-14 15:27:30" --no-pager -o cat \
  | grep -E 'RunPodSandbox|StopPodSandbox|RemovePodSandbox|TearDown|CreateContainer|StartContainer|StopContainer|RemoveContainer' \
  | grep -E "ipam-demo|$SB|6200a7ce1f" \
  | sed -E 's/^time="[0-9-]+T([0-9:.]{12})[0-9]*\+09:00" level=info msg=/\1 [containerd] /'
grep "$SB" /var/log/calico/cni/cni.log \
  | grep -E 'Calico CNI IPAM request|Looking up existing affinities|Attempting to assign|Creating new handle|Writing block in order|Successfully claimed|Auto-assigned|Populated endpoint|Setting the host side interface name|Adding IPv4 route|Wrote updated endpoint|Releasing IP address|Released address using handleID|Asked to release address' \
  | sed -E 's/^2026-11-14 ([0-9:.]{12}) \[(INFO|WARNING)\]\[[0-9]+\] /\1 [calico-cni] /'
} | sort | sed -E 's/([0-9a-f]{12})[0-9a-f]{52}/\1…/g; s/\\"/"/g' | python3 -c 'import sys; [print(l.rstrip("\n")[:150]) for l in sys.stdin]'
R
