#!/usr/bin/env bash
# calico-kube-controllers 의 IPAM 정리 기록: 점검 주기, ipam-fill(31-ipam-blocks) 을 지울 때의 누수 후보, 빈 블록 반납 (조회만 한다)
# 실습 저장소 루트(./lab 이 있는 곳)에서 bash <이 파일> 로 실행 (Mac). 로그 시각은 UTC (KST = UTC+9)
K="./lab kubectl"
KC=$($K -n kube-system get pod -l k8s-app=calico-kube-controllers -o jsonpath='{.items[0].metadata.name}')
L=$($K -n kube-system logs $KC 2>&1)
short(){ sed -E 's/handle="k8s-pod-network\.([0-9a-f]{12})[0-9a-f]*"/handle="k8s-pod-network.\1…"/' | cut -c1-210; }
echo "# 31편 보강: calico-kube-controllers IPAM 로그 ($(date '+%F %T %Z')), Mac 에서 ./lab 으로 조회, 파드 $KC"
echo; echo "## 1. KubeControllersConfiguration default 의 node 컨트롤러 설정"
$K get kubecontrollersconfigurations.crd.projectcalico.org default -o jsonpath='leakGracePeriod={.spec.controllers.node.leakGracePeriod}{"\n"}'
echo; echo "## 2. 시작할 때 정한 IPAM 점검 주기와 전체 점검 시각"
echo "$L" | grep -E 'ipam.go [0-9]+: Will run periodic IPAM sync every'
echo "$L" | grep -E 'Performing a full scan of IPAM allocations' | awk '$2>="06:20" && $2<="06:50"' | cut -c1-140
echo; echo "## 3. ipam-fill(파드 62개) 을 지운 직후(06:29:49 UTC = 15:29:49 KST): 누수 후보(Candidate IP leak)"
C=$(echo "$L" | grep 'Candidate IP leak' | awk '$2>="06:29:00" && $2<="06:31:00"')
echo "06:29~06:31 UTC 의 Candidate IP leak 줄 수: $(echo "$C" | grep -c .)  (첫 줄 $(echo "$C" | head -1 | awk '{print $2}'), 끝 줄 $(echo "$C" | tail -1 | awk '{print $2}'))"
echo "그중 pod=\"default/ipam-fill-…\" 인 줄 수: $(echo "$C" | grep -c 'pod="default/ipam-fill-')"
echo "$C" | head -3 | short
echo "로그 전체의 Confirmed IP leak 줄 수: $(echo "$L" | grep -c 'Confirmed IP leak')"
echo; echo "## 4. 빈 블록 반납"
echo "$L" | grep -E 'Releasing affinity for empty block|Received block delete' | cut -c1-200
