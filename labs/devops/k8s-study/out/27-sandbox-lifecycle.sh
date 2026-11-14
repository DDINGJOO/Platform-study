#!/usr/bin/env bash
# 27편 보강: 27-container-runtime 의 cri-demo 파드(샌드박스 4a7f58…)에 대해 worker1 containerd 로그를 처음부터 끝까지 다시 본다.
# RunPodSandbox 안에서 일어난 CNI ADD, OOM 뒤 같은 샌드박스에서 다시 만든 컨테이너, 삭제 뒤의 RemovePodSandbox 시각.
# Mac 에서 실행(조회만 한다).
cd "${LAB:?실습 저장소(./lab 이 있는 곳) 경로를 LAB 에 넣는다}"
echo "# 27편 보강 cri-demo 샌드박스의 생애 (worker1 containerd 로그, $(date '+%F %T %Z') 에 조회)"
./lab ssh 1 -- sudo bash -s <<'R'
SB=4a7f58eda84c655e70e1a1f0ac927019f74baec7eb3084d5d70480ffb56833f3
journalctl -u containerd --since "2026-11-14 15:53:00" --until "2026-11-14 15:54:00" --no-pager -o cat \
 | grep -E "RunPodSandbox|Calico CNI IPAM assigned|host side interface name|connecting to shim $SB|CreateContainer within sandbox|StartContainer for|StopContainer for|StopPodSandbox for|shim disconnected\" id=$SB|Releasing IP address|TearDown network|RemoveContainer for|RemovePodSandbox" \
 | grep -E "$SB|cri-demo|168f31416bb1|db22cd06d071" \
 | sed -E 's/^time="[0-9-]+T([0-9:.]{12})[0-9]*\+09:00" level=[a-z]+ msg=/\1 /; s/^2026-11-14 ([0-9:.]{12}) \[INFO\]\[[0-9]+\] /\1 [calico] /' \
 | sed -E 's/[0-9a-f]{64}/<&>/g; s/<([0-9a-f]{12})[0-9a-f]{52}>/\1…/g' | cut -c1-150
R
