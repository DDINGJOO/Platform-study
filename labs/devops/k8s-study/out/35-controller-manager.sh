#!/usr/bin/env bash
# 실습 저장소의 shared/components/20-controller-manager.sh 를 옮긴 것. 실습 저장소 루트에서 실행한다.
# kube-controller-manager: 안에 든 컨트롤러 목록, 컨트롤러별 신원, 원하는 상태로 되돌리는 루프, 밖에 있는 컨트롤러 (Mac 에서 실행)
# 실험 전용 네임스페이스 cm-demo 에서만 만들고 지운다.
cd "$(dirname "$0")/../.."   # 실습 저장소 루트 (./lab 이 있는 곳)
K="./lab kubectl"; ts(){ date '+%T'; }
NS=cm-demo; IMG=registry.k8s.io/pause:3.10.2
now(){ python3 -c 'import time;print("%.1f"%time.time())'; }
echo "# kube-controller-manager 가 하는 일 ($(date '+%F %T %Z'))"

echo; echo "## 0. 어디서 어떤 설정으로 도나"
$K -n kube-system get pod -l component=kube-controller-manager -o wide
echo "$(ts) master\$ grep -- '- --' /etc/kubernetes/manifests/kube-controller-manager.yaml"
./lab ssh master -- sudo grep -E '^\s+- --' /etc/kubernetes/manifests/kube-controller-manager.yaml
echo "$(ts) 리더 선출 Lease: $($K -n kube-system get lease kube-controller-manager -o jsonpath='holder={.spec.holderIdentity} leaseDurationSeconds={.spec.leaseDurationSeconds}')"
echo "$(ts) master\$ ss -tnp 로 kube-controller-manager 프로세스의 TCP 연결 (상대 주소:포트별 개수)"
./lab ssh master -- sudo bash -s <<'R'
ss -tnp | grep '"kube-controller' | awk '{print $5}' | sort | uniq -c | sed 's/^/  /'
echo "  LISTEN: $(ss -tlnp | grep '"kube-controller' | awk '{print $4}' | tr '\n' ' ')"
R

echo; echo "## 1. 바이너리 안에 든 컨트롤러 (kube-controller-manager --help 의 --controllers 설명)"
$K -n kube-system exec kube-controller-manager-k8s-master -- kube-controller-manager --help 2>/dev/null > /tmp/kcm-help.$$ || true
python3 - /tmp/kcm-help.$$ <<'P'
import re,sys
t=open(sys.argv[1]).read()
m=re.search(r'--controllers strings(.*?)\n\s*--', t, re.S)
s=" ".join(m.group(1).split())
allc=re.search(r'All controllers: (.*?)\s*Disabled-by-default controllers: (.*?)\s*\(default', s)
a=[x.strip() for x in allc.group(1).split(',')]; d=[x.strip() for x in allc.group(2).split(',')]
print("  전체 %d개 (그중 기본으로 꺼진 것 %d개: %s)" % (len(a), len(d), ", ".join(d)))
for i in range(0,len(a),4): print("   ", "  ".join("%-38s" % x for x in a[i:i+4]))
P
rm -f /tmp/kcm-help.$$
echo "$(ts) 시작 로그에서 건너뛴 컨트롤러 (kubectl logs kube-controller-manager-k8s-master | grep -i skip)"
$K -n kube-system logs kube-controller-manager-k8s-master 2>/dev/null | grep -i -E 'skipping|Warning: controller|disabled' | sed -E 's/^.{0,0}/  /' | cut -c1-220 | head -12

echo; echo "## 2. 컨트롤러마다 따로 쓰는 신원 (--use-service-account-credentials=true)"
echo "  kube-system 의 *-controller ServiceAccount: $($K -n kube-system get sa -o name | grep -c -- '-controller$')개"
$K -n kube-system get sa -o name | grep -- '-controller$' | sed 's#serviceaccount/##' | paste -sd' ' - | fold -w 150 -s | sed 's/^/    /'

$K create ns $NS >/dev/null
echo; echo "## 3. 원하는 상태로 되돌리는 루프: Deployment → ReplicaSet → Pod"
$K -n $NS create deployment web --image=$IMG --replicas=3 >/dev/null
$K -n $NS rollout status deploy/web --timeout=60s >/dev/null
RS=$($K -n $NS get rs -l app=web -o jsonpath='{.items[0].metadata.name}')
P1=$($K -n $NS get pod -l app=web -o jsonpath='{.items[0].metadata.name}')
echo "$(ts) 주인 사슬(ownerReferences):"
echo "    pod/$P1 → $($K -n $NS get pod $P1 -o jsonpath='{.metadata.ownerReferences[0].kind}/{.metadata.ownerReferences[0].name} (controller={.metadata.ownerReferences[0].controller})')"
echo "    replicaset/$RS → $($K -n $NS get rs $RS -o jsonpath='{.metadata.ownerReferences[0].kind}/{.metadata.ownerReferences[0].name} (controller={.metadata.ownerReferences[0].controller})')"
echo "    pod 를 쓴 주체들(managedFields: manager / operation / subresource):"
$K -n $NS get pod $P1 --show-managed-fields -o json | python3 -c '
import json,sys
for m in json.load(sys.stdin)["metadata"]["managedFields"]: print("      %-24s %-7s %s" % (m["manager"], m["operation"], m.get("subresource","-")))'


echo; echo "### 3-a. 파드 하나를 지우면 (ReplicaSet 컨트롤러)"
T0=$(now); $K -n $NS delete pod $P1 --wait=false >/dev/null
echo "$(ts) kubectl delete pod $P1"
while [ "$($K -n $NS get pod -l app=web --no-headers 2>/dev/null | grep -v Terminating | grep -c Running)" != 3 ]; do sleep 0.3; done
echo "$(ts) Running 3개로 돌아옴: $(python3 -c "print('%.1f' % ($(now)-$T0))")초 (조회 간격 0.3초 포함)"
$K -n $NS get events --field-selector involvedObject.kind=ReplicaSet -o json | python3 -c '
import json,sys
for e in json.load(sys.stdin)["items"]:
    print("    %-22s %-16s %s" % (e.get("reportingComponent") or e["source"].get("component",""), e["reason"], e["message"]))' | tail -1

echo; echo "### 3-b. ReplicaSet 을 직접 5개로 바꾸면 (위층 Deployment 컨트롤러가 되돌리나)"
T0=$(now); $K -n $NS scale rs $RS --replicas=5 >/dev/null
echo "$(ts) kubectl scale rs $RS --replicas=5"
for i in 1 2 3 4 5 6 7 8 9 10; do
  echo "    +$(python3 -c "print('%.1f' % ($(now)-$T0))")s  rs.spec.replicas=$($K -n $NS get rs $RS -o jsonpath='{.spec.replicas}')  파드 $($K -n $NS get pod -l app=web --no-headers | awk '{print $3}' | sort | uniq -c | tr -s ' ' | tr '\n' ' ')"
  sleep 0.5
done
echo "$(ts) 이벤트(누가 무엇을):"
$K -n $NS get events -o json | python3 -c '
import json,sys
it=json.load(sys.stdin)["items"]
it=[e for e in it if e["involvedObject"]["kind"] in ("Deployment","ReplicaSet")]
for e in sorted(it,key=lambda e:e.get("lastTimestamp") or e.get("eventTime") or "")[-6:]:
    print("    %-22s %-10s %-18s %s" % (e.get("reportingComponent") or e["source"].get("component",""), e["involvedObject"]["kind"], e["reason"], e["message"]))'

echo; echo "## 4. KCM 밖에서 도는 컨트롤러 예: calico-kube-controllers"
$K -n kube-system get deploy calico-kube-controllers -o jsonpath='  {.metadata.name}: replicas={.spec.replicas} image={.spec.template.spec.containers[0].image} ENABLED_CONTROLLERS={.spec.template.spec.containers[0].env[?(@.name=="ENABLED_CONTROLLERS")].value}{"\n"}'
echo "  type=LoadBalancer Service 를 맡을 cloud-controller-manager: $($K get pod -A --no-headers 2>/dev/null | grep -c cloud-controller)개 (24편)"

echo; echo "## 5. kubectl apply 는 create/update 를 어떻게 고르나 (-v=6, ConfigMap)"
printf 'apiVersion: v1\nkind: ConfigMap\nmetadata: {name: ap-demo, namespace: %s}\ndata: {k: v1}\n' $NS > /tmp/ap.$$.yaml
echo "$(ts) 처음 apply:"; $K apply -f /tmp/ap.$$.yaml -v=6 2>&1 | python3 -c '
import re,sys
for l in sys.stdin:
    m=re.search(r"verb=\"(\w+)\" url=\"https?://[^/]+([^\"?]*)[^\"]*\" status=\"([^\"]*)\"",l)
    if m and not m.group(2).startswith("/openapi"): print("    %-6s %-48s %s" % m.groups())
    elif l.startswith("configmap/"): print("    → "+l.strip())' 
sed -i '' 's/k: v1/k: v2/' /tmp/ap.$$.yaml
echo "$(ts) 값을 바꿔 다시 apply:"; $K apply -f /tmp/ap.$$.yaml -v=6 2>&1 | python3 -c '
import re,sys
for l in sys.stdin:
    m=re.search(r"verb=\"(\w+)\" url=\"https?://[^/]+([^\"?]*)[^\"]*\" status=\"([^\"]*)\"",l)
    if m and not m.group(2).startswith("/openapi"): print("    %-6s %-48s %s" % m.groups())
    elif l.startswith("configmap/"): print("    → "+l.strip())' 
rm -f /tmp/ap.$$.yaml

echo; echo "## 6. 정리"
$K delete ns $NS --wait=true >/dev/null; echo "$(ts) 네임스페이스 $NS 삭제"
