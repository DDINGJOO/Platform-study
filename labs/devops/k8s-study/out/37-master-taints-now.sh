#!/usr/bin/env bash
# 37편: 지금 노드에 붙은 taint 와 역할 라벨, 마스터에 떠 있는 파드가 어떤 toleration 으로 그 taint 를 견디는지,
# 마스터의 requests 가 얼마나 차 있는지 본다. 조회만 한다.
# 실습 저장소 루트(./lab 이 있는 곳)에서 bash <이 스크립트> 로 실행
set -u
K="./lab kubectl"
echo "# 마스터의 taint 와 마스터에 있는 파드 ($(date '+%F %T %Z'))"
echo; echo "## 1. 노드별 역할 라벨과 taint"
$K get nodes -o json | python3 -c '
import json,sys
for n in json.load(sys.stdin)["items"]:
    roles=[k.split("/",1)[1] for k in n["metadata"]["labels"] if k.startswith("node-role.kubernetes.io/")]
    t=["%s:%s" % (x["key"],x["effect"]) for x in n["spec"].get("taints",[])] or ["없음"]
    print("  %-12s role 라벨=%-14s taints=%s" % (n["metadata"]["name"], ",".join(roles) or "-", " ".join(t)))'
echo; echo "## 2. 마스터에 떠 있는 파드: 소유자, 만든 시각, CPU·메모리 requests, toleration"
$K get pod -A -o json --field-selector spec.nodeName=k8s-master | python3 -c '
import json,sys
def tol(t):
    k=t.get("key","(key 없음)"); op=t.get("operator","Equal"); e=t.get("effect","(effect 없음)")
    s="%s %s %s" % (k,op,e)
    if "tolerationSeconds" in t: s+=" %ss" % t["tolerationSeconds"]
    return s
for p in json.load(sys.stdin)["items"]:
    m=p["metadata"]; o=(m.get("ownerReferences") or [{}])[0].get("kind","-")
    rq=[c.get("resources",{}).get("requests",{}) for c in p["spec"]["containers"]]
    cpu=",".join(r.get("cpu","-") for r in rq); mem=",".join(r.get("memory","-") for r in rq)
    print("  %s/%s  owner=%s  created=%s  cpu=%s mem=%s" % (m["namespace"], m["name"], o, m["creationTimestamp"], cpu, mem))
    for t in p["spec"].get("tolerations",[]): print("        toleration:", tol(t))'
echo; echo "## 3. 마스터의 Allocatable 과 Allocated resources (kubectl describe node)"
$K describe node k8s-master | sed -n '/^Allocatable:/,/^System Info:/p' | grep -E '^Allocatable|^  (cpu|memory|pods):'
$K describe node k8s-master | sed -n '/^Allocated resources:/,/^Events:/p' | grep -E 'Resource|cpu|memory'
echo; echo "## 4. 노드별 CPU requests 합 (지금 떠 있는 파드 기준)"
$K get pod -A -o json --field-selector status.phase=Running | python3 -c '
import json,sys,collections
def m(v):
    return int(float(v[:-1])) if v.endswith("m") else int(float(v)*1000)
s=collections.Counter(); n=collections.Counter()
for p in json.load(sys.stdin)["items"]:
    node=p["spec"].get("nodeName"); n[node]+=1
    for c in p["spec"]["containers"]:
        r=c.get("resources",{}).get("requests",{}).get("cpu")
        if r: s[node]+=m(r)
for node in sorted(n): print("  %-12s Running 파드 %2d개, CPU requests 합 %dm" % (node, n[node], s[node]))'
