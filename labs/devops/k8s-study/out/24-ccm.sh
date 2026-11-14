#!/usr/bin/env bash
# kube-controller-manager(KCM) 안에는 어떤 컨트롤러가 있고, cloud-controller-manager(CCM) 가 없으면 무엇이 멈추나 (Mac 에서 실행)
cd "$(dirname "$0")/../.."   # 실습 저장소 루트 (./lab 이 있는 곳)
K="./lab kubectl"; ts(){ date '+%T'; }
KCM=kube-controller-manager-k8s-master
echo "# E7 컨트롤러 매니저와 클라우드 컨트롤러 매니저 ($(date '+%F %T %Z'))"
echo; echo "## 1. kube-controller-manager 실행 플래그 (정적 파드)"
$K -n kube-system get pod $KCM -o jsonpath='{range .spec.containers[0].command[*]}{@}{"\n"}{end}' | grep -E 'controllers|leader-elect|cloud-provider|node-monitor|cluster-cidr|allocate'
echo; echo "## 2. KCM 바이너리 하나에 들어 있는 컨트롤러 (kube-controller-manager --help 의 --controllers 설명)"
$K -n kube-system exec $KCM -- kube-controller-manager --help 2>/dev/null | awk '/--controllers strings/{f=1} f{print} f&&/Disabled-by-default/{exit}' | tr ',' '\n' | sed 's/^ *//' > /tmp/e7-help.txt
grep -oE '(^|[ ,])[a-z][a-z-]*-controller' /tmp/e7-help.txt | tr -d ' ,' | sort -u > /tmp/e7-all.txt
echo "컨트롤러 이름 수: $(wc -l < /tmp/e7-all.txt | tr -d ' ')"; paste -sd' ' /tmp/e7-all.txt | fold -s -w 150
echo "기본 꺼짐:"; grep -A3 'Disabled-by-default' /tmp/e7-help.txt | tr '\n' ' ' | sed 's/.*Disabled-by-default controllers: *//' | cut -c1-200; echo
echo; echo "## 3. 리더 선출: 지금 일하는 KCM / 스케줄러 (Lease)"
$K -n kube-system get lease kube-controller-manager kube-scheduler -o custom-columns='NAME:.metadata.name,HOLDER:.spec.holderIdentity,RENEW:.spec.renewTime'
echo; echo "## 4. CCM 이 있나?"
echo "cloud-controller-manager 파드: $($K get pod -A --no-headers | grep -c cloud-controller)개"
$K get nodes -o custom-columns='NODE:.metadata.name,PROVIDER_ID:.spec.providerID,TAINTS:.spec.taints[*].key'
echo; echo "## 5. CCM 이 없을 때 type: LoadBalancer 서비스"
$K create service loadbalancer ccm-demo --tcp=80:80 >/dev/null; $K set selector svc ccm-demo app=myweb >/dev/null
for i in 1 2 3; do sleep 10; echo "$(ts) $($K get svc ccm-demo --no-headers | awk '{print $1, $2, "EXTERNAL-IP="$4, $5}')"; done
echo "$(ts) 이벤트:"; $K get events --field-selector involvedObject.name=ccm-demo --no-headers 2>/dev/null | head -5
echo "$(ts) NodePort 로는 바로 접속됨:"; NP=$($K get svc ccm-demo -o jsonpath='{.spec.ports[0].nodePort}')
W1=$($K get node k8s-worker1 -o jsonpath='{.status.addresses[?(@.type=="InternalIP")].address}')
./lab ssh master -- curl -s -o /dev/null -w "worker1($W1):$NP → %{http_code}\n" --max-time 3 http://$W1:$NP/
$K delete svc ccm-demo >/dev/null && echo "$(ts) ccm-demo 삭제"
rm -f /tmp/e7-help.txt /tmp/e7-all.txt
