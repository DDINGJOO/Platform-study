#!/usr/bin/env bash
# 실습 저장소의 shared/components/07-master-workload.sh 를 옮긴 것. 실습 저장소 루트에서 실행한다.
# 마스터에도 일반 파드를 올릴 수 있나: 지금 마스터에 뜬 파드, taint 가 막는 모습, toleration 을 준 파드 (Mac 에서 실행)
cd "$(dirname "$0")/../.."   # 실습 저장소 루트 (./lab 이 있는 곳)
K="./lab kubectl"; ts(){ date '+%T'; }
echo "# 마스터에 일반 파드 올리기 ($(date '+%F %T %Z'))"
echo; echo "## 1. 지금 마스터에 떠 있는 파드와 control-plane taint 를 견디는 toleration"
$K get pod -A -o json --field-selector spec.nodeName=k8s-master | python3 -c '
import json,sys
for p in json.load(sys.stdin)["items"]:
    o=(p["metadata"].get("ownerReferences") or [{}])[0].get("kind","-")
    ts=p["spec"].get("tolerations",[])
    if o=="Node": d="정적 파드: kubelet 이 파일로 띄움, 스케줄러를 거치지 않음"
    elif any(t.get("operator")=="Exists" and not t.get("key") and not t.get("effect") for t in ts): d="toleration: key·effect 없이 operator Exists = 모든 taint 견딤"
    elif any(t.get("operator")=="Exists" and not t.get("key") and t.get("effect")=="NoSchedule" for t in ts): d="toleration: key 없이 NoSchedule 전부 견딤"
    elif any("control-plane" in t.get("key","") for t in ts): d="toleration: node-role.kubernetes.io/control-plane"
    else: d="(control-plane toleration 없음)"
    print("  %-50s owner=%-10s %s" % (p["metadata"]["namespace"]+"/"+p["metadata"]["name"], o, d))'
echo "  마스터 taint: $($K get node k8s-master -o jsonpath='{range .spec.taints[*]}{.key}:{.effect}{end}')"
$K create ns cp-demo >/dev/null
echo; echo "## 2. 마스터를 지정만 한 파드 (toleration 없음)"
cat <<Y | $K -n cp-demo apply -f - >/dev/null
apiVersion: v1
kind: Pod
metadata: {name: on-master-no-tol}
spec:
  nodeSelector: {kubernetes.io/hostname: k8s-master}
  containers: [{name: c, image: registry.k8s.io/pause:3.10.2}]
Y
sleep 5; echo "$(ts) $($K -n cp-demo get pod on-master-no-tol --no-headers -o wide | awk '{print $1, $3, "NODE="$7}')"
$K -n cp-demo get events --field-selector involvedObject.name=on-master-no-tol --no-headers | awk '{$1=""; print "  "$0}' | grep FailedScheduling | cut -c1-200
echo; echo "## 3. 같은 파드에 control-plane taint 를 견디는 toleration 을 더함"
cat <<Y | $K -n cp-demo apply -f - >/dev/null
apiVersion: v1
kind: Pod
metadata: {name: on-master-tol}
spec:
  nodeSelector: {kubernetes.io/hostname: k8s-master}
  tolerations: [{key: node-role.kubernetes.io/control-plane, operator: Exists, effect: NoSchedule}]
  containers: [{name: c, image: registry.k8s.io/pause:3.10.2}]
Y
$K -n cp-demo wait --for=condition=Ready pod/on-master-tol --timeout=60s >/dev/null; echo "$(ts) $($K -n cp-demo get pod on-master-tol --no-headers -o wide | awk '{print $1, $3, "NODE="$7}')"
echo; echo "## 4. toleration 만 주고 노드를 지정하지 않으면? 같은 파드 6개"
cat <<Y | $K -n cp-demo apply -f - >/dev/null
apiVersion: apps/v1
kind: Deployment
metadata: {name: tol-only}
spec:
  replicas: 6
  selector: {matchLabels: {app: tol-only}}
  template:
    metadata: {labels: {app: tol-only}}
    spec:
      tolerations: [{key: node-role.kubernetes.io/control-plane, operator: Exists, effect: NoSchedule}]
      containers: [{name: c, image: registry.k8s.io/pause:3.10.2}]
Y
$K -n cp-demo rollout status deploy/tol-only --timeout=90s >/dev/null; echo "  노드별 개수: $($K -n cp-demo get pod -l app=tol-only -o jsonpath='{range .items[*]}{.spec.nodeName}{"\n"}{end}' | sort | uniq -c | awk '{print $2"="$1}' | paste -sd' ' -)"
echo; echo "## 5. 정리"
$K delete ns cp-demo --wait=true >/dev/null && echo "$(ts) cp-demo 네임스페이스 삭제"
