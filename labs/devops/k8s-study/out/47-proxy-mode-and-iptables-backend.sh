#!/usr/bin/env bash
# 실습 저장소의 shared/why/05-kube-proxy-modes/01-proxy-mode-and-iptables-backend.sh 를 옮긴 것. 실습 저장소 루트에서 실행한다.
# kube-proxy 모드는 어디서 정해졌나(ConfigMap·로그·이벤트), 노드의 iptables 는 legacy/nft 중 무엇인가, 규칙은 몇 개인가 (조회만, Mac 에서 실행)
cd "$(dirname "$0")/../../.."   # 실습 저장소 루트 (./lab 이 있는 곳)
K="./lab kubectl"
echo "# 05 kube-proxy 모드와 iptables 백엔드 조회 ($(date '+%F %T %Z'))"

echo; echo "## 1. kube-proxy ConfigMap 의 mode (kubeadm 설정 파일에는 KubeProxyConfiguration 이 없다)"
$K -n kube-system get cm kube-proxy -o jsonpath='{.data.config\.conf}' | grep -nE '^mode:|^  (syncPeriod|minSyncPeriod|masqueradeAll|localhostNodePorts):|^iptables:|^nftables:|^ipvs:'
echo "scripts/master-init.sh 안의 KubeProxyConfiguration 줄 수: $(grep -c KubeProxyConfiguration scripts/master-init.sh)"

echo; echo "## 2. kube-proxy 로그: 시작할 때 고른 Proxier, 모드 기본값 경고(1.37에 추가된 'No kube-proxy mode specified') 유무"
for p in $($K -n kube-system get pod -l k8s-app=kube-proxy -o jsonpath='{range .items[*]}{.metadata.name}:{.spec.nodeName}{"\n"}{end}'); do
  pod=${p%%:*}; node=${p##*:}
  echo "### $node ($pod)"
  $K -n kube-system logs "$pod" 2>/dev/null | grep -E 'Proxier"|No kube-proxy mode specified|route_localnet|iptables-legacy|Detected|backend' | cut -c1-220
done
echo "KubeProxyDefaultMode / IPVSDeprecation 이벤트 수: $($K get events -A --field-selector reason=KubeProxyDefaultMode -o name 2>/dev/null | wc -l | tr -d ' ') / $($K get events -A --field-selector reason=IPVSDeprecation -o name 2>/dev/null | wc -l | tr -d ' ')"
echo "/proxyMode (worker1): $(./lab ssh worker1 -- curl -s 127.0.0.1:10249/proxyMode)"

echo; echo "## 3. kube-proxy 컨테이너 안의 iptables·nft 버전 (이미지에 든 도구)"
KP1=$($K -n kube-system get pod -l k8s-app=kube-proxy --field-selector spec.nodeName=k8s-worker1 -o jsonpath='{.items[0].metadata.name}')
$K -n kube-system exec "$KP1" -- sh -c 'iptables --version; nft --version 2>/dev/null || echo "nft 없음"
for f in /usr/sbin/iptables /usr/sbin/iptables-wrapper /usr/sbin/iptables-legacy /usr/sbin/iptables-nft; do if [ -L $f ]; then echo "$f: symlink"; elif [ -e $f ]; then echo "$f: file"; else echo "$f: 없음"; fi; done
echo "iptables-wrapper 가 백엔드를 고르는 줄(이미지 안 스크립트에서 발췌):"
while IFS= read -r l; do case "$l" in *KUBE-IPTABLES-HINT*|*"mode=nft"*|*"mode=legacy"*) echo "  $l";; esac; done < /usr/sbin/iptables-wrapper' 2>&1 | head -20

echo; echo "## 4. 노드(worker1)의 커널·iptables 백엔드·규칙 수"
./lab ssh worker1 -- sudo bash -s <<'R'
echo "kernel: $(uname -r)"
echo "host iptables: $(iptables --version 2>&1)"
echo "host nft: $(nft --version 2>&1)"
echo "update-alternatives iptables: $(update-alternatives --query iptables 2>/dev/null | awk '/^Value:/{print $2}')"
echo "nft 백엔드 규칙 줄 수(iptables-nft-save): $(iptables-nft-save 2>/dev/null | grep -c '^-A')"
echo "legacy 백엔드 규칙 줄 수(iptables-legacy-save): $(iptables-legacy-save 2>/dev/null | grep -c '^-A')"
echo "legacy 쪽에 있는 표·체인:"; iptables-legacy-save 2>/dev/null | grep -E '^\*|^:' | head -20
echo "KUBE-IPTABLES-HINT(kubelet 이 mangle 표에 만드는 힌트 체인) nft/legacy: $(iptables-nft-save -t mangle 2>/dev/null | grep -c '^:KUBE-IPTABLES-HINT') / $(iptables-legacy-save -t mangle 2>/dev/null | grep -c '^:KUBE-IPTABLES-HINT')"
NAT=$(iptables-save -t nat 2>/dev/null)
echo "nat 표: KUBE-SVC 체인 $(grep -c '^:KUBE-SVC-' <<<"$NAT")개, KUBE-SEP 체인 $(grep -c '^:KUBE-SEP-' <<<"$NAT")개, KUBE-SERVICES 규칙 $(grep -c '^-A KUBE-SERVICES' <<<"$NAT")줄, nat 표 전체 -A $(grep -c '^-A' <<<"$NAT")줄, KUBE 들어간 줄 $(grep -c KUBE <<<"$NAT")줄"
echo "filter 표 KUBE 줄: $(iptables-save -t filter 2>/dev/null | grep -c KUBE)"
echo "iptables-save 전체 바이트: $(iptables-save 2>/dev/null | wc -c)"
echo "nft 테이블 목록:"; nft list tables 2>&1
echo "ip_vs 모듈: $(lsmod | grep -c '^ip_vs')개, kube-ipvs0 장치: $(ip -br link show kube-ipvs0 2>/dev/null | wc -l)개"
echo "sysctl route_localnet(all): $(sysctl -n net.ipv4.conf.all.route_localnet)"
R

echo; echo "## 5. Service 수와 kube-proxy 동기화 메트릭 (worker1)"
echo "Service 수(전체 ns): $($K get svc -A --no-headers | wc -l | tr -d ' '), Service 포트 합: $($K get svc -A -o jsonpath='{range .items[*]}{range .spec.ports[*]}x{"\n"}{end}{end}' | grep -c x)"
./lab ssh worker1 -- curl -s 127.0.0.1:10249/metrics | grep -E '^# HELP kubeproxy_sync_proxy_rules_iptables_(total|last) |^# HELP kubeproxy_sync_(full|partial)_proxy_rules_duration_seconds |^kubeproxy_sync_(full|partial)_proxy_rules_duration_seconds_(sum|count)|^kubeproxy_sync_proxy_rules_duration_seconds_(sum|count)|^kubeproxy_sync_proxy_rules_iptables_(total|last|partial_restore_failures_total)|^kubeproxy_sync_proxy_rules_last_timestamp'
