#!/usr/bin/env bash
# CCM 이 없어도 Calico kube-controllers 의 loadbalancer 컨트롤러가 LoadBalancer IP 를 줄 수 있나 (Mac 에서 실행)
cd "$(dirname "$0")/../.."   # 실습 저장소 루트 (./lab 이 있는 곳)
K="./lab kubectl"; ts(){ date '+%T'; }
echo "# E22 Calico 의 LoadBalancer IP 할당 ($(date '+%F %T %Z'))"
echo "calico-kube-controllers ENABLED_CONTROLLERS=$($K -n kube-system get deploy calico-kube-controllers -o jsonpath='{.spec.template.spec.containers[0].env[?(@.name=="ENABLED_CONTROLLERS")].value}')"
echo "KubeControllersConfiguration loadBalancer: $($K get kubecontrollersconfigurations.crd.projectcalico.org default -o jsonpath='{.spec.controllers.loadBalancer}')"
echo; echo "## 1. LoadBalancer 용 IPPool 이 없을 때"
$K create service loadbalancer lb-demo --tcp=80:80 >/dev/null; $K set selector svc lb-demo app=myweb >/dev/null; sleep 8
echo "$(ts) $($K get svc lb-demo --no-headers | awk '{print $1, $2, "EXTERNAL-IP="$4}')"
echo; echo "## 2. allowedUses: [LoadBalancer] IPPool 을 만들면 (calicoctl, 172.30.0.0/29, blockSize 29)"
./lab ssh master -- bash -s <<'R'
cat <<Y | calicoctl apply -f - 2>&1
apiVersion: projectcalico.org/v3
kind: IPPool
metadata: {name: lb-demo-pool}
spec:
  cidr: 172.30.0.0/29
  blockSize: 29
  allowedUses: [LoadBalancer]
  natOutgoing: false
  disabled: false
Y
calicoctl get ippool -o wide 2>&1
R
for i in 1 2 3 4 5 6; do sleep 3; ip=$($K get svc lb-demo -o jsonpath='{.status.loadBalancer.ingress[0].ip}'); echo "$(ts) EXTERNAL-IP=${ip:-<pending>}"; [ -n "$ip" ] && break; done
echo "서비스 어노테이션/이벤트: $($K get events --field-selector involvedObject.name=lb-demo --no-headers 2>/dev/null | tail -2 | cut -c1-160)"
if [ -n "$ip" ]; then
  echo "마스터 → $ip:80 curl: $(./lab ssh master -- curl -s -o /dev/null -w '%{http_code}' --max-time 3 http://$ip/)"
  echo "worker1 → $ip:80 curl: $(./lab ssh 1 -- curl -s -o /dev/null -w '%{http_code}' --max-time 3 http://$ip/)"
  echo "Mac → $ip:80 curl: $(curl -s -o /dev/null -w '%{http_code}' --max-time 3 http://$ip/)"
  echo "worker1 iptables 에 $ip 규칙: $(./lab ssh 1 -- sudo sh -c "iptables-save -t nat 2>/dev/null | grep -c $ip")줄"
fi
echo; echo "## 3. 정리"
$K delete svc lb-demo >/dev/null; ./lab ssh master -- calicoctl delete ippool lb-demo-pool 2>&1
./lab ssh master -- calicoctl get ippool -o wide 2>&1 | awk '{print $1, $2}'
