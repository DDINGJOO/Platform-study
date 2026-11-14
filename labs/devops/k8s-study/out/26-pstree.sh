#!/usr/bin/env bash
# 마스터의 프로세스 트리: 누가 누구의 부모인가 (마스터 VM 안에서 실행: ./lab ssh master -- sudo bash -s < 이 파일)
echo "# E12 마스터 pstree ($(date '+%F %T %Z'))"
echo; echo "## 1. 전체 (스레드 숨김, -T)"
echo "master# pstree -T"; pstree -T
echo; echo "## 2. 쿠버네티스 관련 가지만, PID 와 인자 (pstree -T -p -a, 줄임)"
for p in $(pgrep -x kubelet) $(pgrep -x containerd); do pstree -T -p -a $p | cut -c1-140; done
echo; echo "## 3. shim 하나당 파드 하나: shim 의 자식 = pause + 컨테이너 프로세스"
for s in $(pgrep -f containerd-shim-runc-v2); do
  id=$(tr '\0' ' ' < /proc/$s/cmdline | grep -oE '\-id [0-9a-f]+' | awk '{print $2}')
  pod=$(crictl inspectp $id 2>/dev/null | grep -m1 '"name"' | awk -F'"' '{print $4}')
  kids=$(ps --ppid $s -o pid=,comm= | awk '{printf "%s(%s) ", $2, $1}')
  printf 'shim(%s) %-36s 자식: %s\n' "$s" "${pod:-?}" "$kids"
done
echo; echo "## 4. 부모 관계 요약 (PPID)"
for n in containerd kubelet kube-apiserver etcd kube-scheduler kube-controller-manager kube-proxy; do
  p=$(pgrep -o -f "^(/usr/local/bin/|/usr/bin/)?$n( |$)"); pp=$(ps -o ppid= -p $p | tr -d ' ')
  printf '%-24s pid=%-6s 부모 pid=%-6s (%s)\n' "$n" "$p" "$pp" "$(ps -o comm= -p $pp)"
done
echo; echo "## 5. systemd 서비스로 뜨는 것 (kubelet, containerd)"
systemctl is-active kubelet containerd | paste -sd' ' -
systemctl show -p MainPID -p ExecStart kubelet | cut -c1-160
