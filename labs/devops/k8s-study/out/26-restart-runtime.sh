#!/usr/bin/env bash
# shim 의 부모가 systemd 라서: containerd·kubelet 을 재시작해도 컨테이너 프로세스는 그대로인가 (워커1 VM 안에서 sudo 로 실행)
P=$(pgrep -o -f 'nginx: master' ); IP=$(crictl pods --name myweb -q | head -1 | xargs -r crictl inspectp | grep -m1 '"ip"' | awk -F'"' '{print $4}')
t(){ date '+%T'; }
st(){ echo "$(t) nginx master pid 들: $(pgrep -f 'nginx: master' | paste -sd' ' -) | shim 수 $(pgrep -c -f containerd-shim-runc-v2) | containerd pid $(pgrep -xo containerd) | kubelet pid $(pgrep -xo kubelet) | curl $IP → $(curl -s -o /dev/null -w '%{http_code}' --max-time 2 http://$IP/)"; }
echo "# E12b 워커1에서 containerd·kubelet 재시작 ($(date '+%F %T %Z'))"
echo "shim 의 부모: $(ps -o ppid= -p $(pgrep -o -f containerd-shim-runc-v2) | tr -d ' ') ($(ps -o comm= -p $(ps -o ppid= -p $(pgrep -o -f containerd-shim-runc-v2))))"
st
echo "$(t) worker1# systemctl restart containerd"; systemctl restart containerd
for i in 1 2 3; do sleep 2; st; done
echo "$(t) worker1# systemctl restart kubelet"; systemctl restart kubelet
for i in 1 2 3; do sleep 2; st; done
