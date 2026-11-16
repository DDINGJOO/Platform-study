#!/usr/bin/env bash
# 관계도의 화살표마다 누가 쓰나: kubectl scale 이 보내는 요청, 객체별 managedFields 작성자, CRD 와 CR 과 그것을 읽는 쪽 (Mac 에서 실행)
# 실습 저장소 루트에서 실행한다. 네임스페이스 blog-58 만 만들고 지운다. 나머지는 조회만 한다.
K="./lab kubectl"; NS=blog-58
echo "# 58 화살표마다 누가 쓰나 ($(date '+%F %T %Z'))"
$K create ns $NS >/dev/null
$K create deploy web -n $NS --image=nginx:1.27-alpine --replicas=1 >/dev/null
$K expose deploy web -n $NS --port=80 >/dev/null
$K rollout status deploy/web -n $NS --timeout=120s >/dev/null

echo; echo "## 1. kubectl scale --replicas=3 이 API 서버에 보내는 요청 (-v=6)"
$K scale deploy web -n $NS --replicas=3 -v=6 2>&1 | grep -oE 'verb="[A-Z]+" url="[^"]+" status="[^"]+"' | sed -E 's#url="https://[^/]+#url="#; s/^/  /'
$K rollout status deploy/web -n $NS --timeout=120s >/dev/null
echo "  Deployment spec.replicas=$($K get deploy web -n $NS -o jsonpath='{.spec.replicas}')  generation=$($K get deploy web -n $NS -o jsonpath='{.metadata.generation}')"
echo "  ReplicaSet spec.replicas=$($K get rs -n $NS -l app=web -o jsonpath='{.items[0].spec.replicas}')  파드 수=$($K get pod -n $NS -l app=web --no-headers | wc -l | tr -d ' ')"

echo; echo "## 2. 객체마다 누가 어느 칸을 썼나 (managedFields: 작성자 / 동작 / 하위 리소스 / 쓴 칸)"
summ() {
python3 -c '
import json,sys
o=json.load(sys.stdin)
for m in o["metadata"].get("managedFields",[]):
    parts=[]
    for k,v in m.get("fieldsV1",{}).items():
        if not k.startswith("f:"): continue
        top=k[2:]
        subs=[s[2:] for s in v if s.startswith("f:")] if isinstance(v,dict) else []
        if top=="status" or not subs: parts.append(top); continue
        if len(subs)>4: subs=subs[:4]+["..."]
        parts.append(top+".{"+",".join(subs)+"}")
    print("    %-24s %-7s %-8s %s" % (m["manager"], m["operation"], m.get("subresource","-"), " ".join(parts)))
'
}
RS=$($K get rs -n $NS -l app=web -o jsonpath='{.items[0].metadata.name}')
POD=$($K get pod -n $NS -l app=web -o jsonpath='{.items[0].metadata.name}')
EPS=$($K get endpointslice -n $NS -l kubernetes.io/service-name=web -o jsonpath='{.items[0].metadata.name}')
echo "  Deployment web"; $K get deploy web -n $NS -o json --show-managed-fields | summ
echo "  ReplicaSet $RS"; $K get rs $RS -n $NS -o json --show-managed-fields | summ
echo "  Pod $POD"; $K get pod $POD -n $NS -o json --show-managed-fields | summ
echo "    (spec.nodeName 을 채운 쪽은 이벤트로: $($K get events -n $NS --field-selector involvedObject.name=$POD,reason=Scheduled -o jsonpath='{.items[0].reportingComponent} {.items[0].reason}'))"
echo "  EndpointSlice $EPS (managed-by=$($K get endpointslice $EPS -n $NS -o jsonpath='{.metadata.labels.endpointslice\.kubernetes\.io/managed-by}'))"; $K get endpointslice $EPS -n $NS -o json --show-managed-fields | summ

echo; echo "## 3. CRD 는 종류를 등록하고 CR 은 그 종류의 객체다 (Calico IPPool)"
$K get crd ippools.crd.projectcalico.org -o jsonpath='  CRD {.metadata.name}: group={.spec.group} kind={.spec.names.kind} scope={.spec.scope} versions={.spec.versions[*].name}{"\n"}'
$K get ippools.crd.projectcalico.org -o custom-columns='  CR:.metadata.name,CIDR:.spec.cidr,IPIP:.spec.ipipMode,BLOCKSIZE:.spec.blockSize'
echo "  ippools 를 list·watch 할 수 있는 ClusterRole 과 그 역할을 받은 ServiceAccount:"
ROLES=$($K get clusterrole -o json | python3 -c '
import json,sys
for r in json.load(sys.stdin)["items"]:
    for rule in r.get("rules") or []:
        res=rule.get("resources",[]); vb=rule.get("verbs",[])
        if ("ippools" in res or "*" in res) and ("watch" in vb or "*" in vb) and "crd.projectcalico.org" in rule.get("apiGroups",[]):
            print(r["metadata"]["name"]); break
')
$K get clusterrolebinding -o json | python3 -c '
import json,sys
roles=set(sys.argv[1].split())
for b in json.load(sys.stdin)["items"]:
    if b["roleRef"]["name"] in roles:
        subs=",".join("%s/%s/%s"%(s["kind"],s.get("namespace","-"),s["name"]) for s in b.get("subjects") or [])
        print("    ClusterRole %-24s <- %s" % (b["roleRef"]["name"], subs))
' "$ROLES"

$K delete ns $NS --wait=false >/dev/null
