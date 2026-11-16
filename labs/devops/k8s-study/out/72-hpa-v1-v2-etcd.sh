#!/usr/bin/env bash
# 확인: HPA 하나를 autoscaling/v1로 만들고 v1·v2로 읽은 뒤 etcd에 실제로 어떤 apiVersion으로 저장됐는지 본다. v1에 없는 v2 필드가 어떻게 왕복되는지도 (Mac 에서 실행)
# 실행: bash shared/why/08-api-versions-deprecation/02-hpa-v1-v2-etcd.sh | tee shared/why/08-api-versions-deprecation/02-hpa-v1-v2-etcd.txt
# 네임스페이스 why-api만 쓴다. etcd는 읽기만 한다. 마지막에 HPA를 지운다(네임스페이스는 마지막 실험이 지운다).
set -u
cd /Users/dding/orca/workspaces/k8s/tang
K="./lab kubectl"; NS=why-api
E=(-n kube-system exec etcd-k8s-master -- etcdctl --endpoints=https://127.0.0.1:2379
   --cacert=/etc/kubernetes/pki/etcd/ca.crt --cert=/etc/kubernetes/pki/etcd/server.crt --key=/etc/kubernetes/pki/etcd/server.key)
# etcd 값의 앞부분을 풀어 저장된 apiVersion/kind를 보여 준다. 내장 리소스는 protobuf("k8s\0" + runtime.Unknown{TypeMeta, raw}), CRD는 JSON.
DECODE='
import json,sys,base64
def varint(b,i):
    r=s=0
    while True:
        c=b[i]; i+=1; r|=(c&0x7f)<<s; s+=7
        if c<0x80: return r,i
def fields(b):
    i=0; out={}
    while i<len(b):
        k,i=varint(b,i); f,t=k>>3,k&7
        if t==2:
            l,i=varint(b,i); out.setdefault(f,[]).append(b[i:i+l]); i+=l
        elif t==0:
            v,i=varint(b,i); out.setdefault(f,[]).append(v)
        else: break
    return out
kv=json.load(sys.stdin)["kvs"][0]; v=base64.b64decode(kv["value"])
if v.startswith(b"k8s\x00"):
    tm=fields(fields(v[4:])[1][0]); print("  형식 protobuf | apiVersion=%s kind=%s | mod_revision=%s | %d바이트" % (tm[1][0].decode(), tm[2][0].decode(), kv["mod_revision"], len(v)))
else:
    o=json.loads(v); print("  형식 JSON | apiVersion=%s kind=%s | mod_revision=%s" % (o["apiVersion"], o["kind"], kv["mod_revision"]))
for w in sys.argv[1:]:
    print("    값 안에 %-45s %s" % (repr(w), "있음" if w.encode() in v else "없음"))
'
etcd_show(){ $K "${E[@]}" get "$1" -w json | python3 -c "$DECODE" "${@:2}"; }
ts(){ date '+%T'; }

echo "# 02 HPA를 v1으로 만들고 v1·v2로 읽고 etcd를 본다 ($(date '+%F %T %Z'))"
$K create namespace $NS --dry-run=client -o yaml | $K apply -f - >/dev/null
$K -n $NS delete hpa web --ignore-not-found >/dev/null

echo; echo "## 1. $(ts) autoscaling/v1으로 생성 (targetCPUUtilizationPercentage: 50, 대상 Deployment는 일부러 없음)"
M1='apiVersion: autoscaling/v1
kind: HorizontalPodAutoscaler
metadata: {name: web, namespace: why-api}
spec:
  scaleTargetRef: {apiVersion: apps/v1, kind: Deployment, name: web}
  minReplicas: 1
  maxReplicas: 3
  targetCPUUtilizationPercentage: 50'
echo "$M1" | sed 's/^/    /'
echo "$M1" | $K create -f - | sed 's/^/  → /'

echo; echo "## 2. 같은 객체를 두 버전 경로로 GET"
for v in v1 v2; do
  echo "  GET /apis/autoscaling/$v/namespaces/$NS/horizontalpodautoscalers/web"
  $K get --raw /apis/autoscaling/$v/namespaces/$NS/horizontalpodautoscalers/web | python3 -c 'import json,sys; o=json.load(sys.stdin); s=o["spec"]; s.pop("scaleTargetRef",None); print("    apiVersion:", o["apiVersion"], "| uid:", o["metadata"]["uid"], "| resourceVersion:", o["metadata"]["resourceVersion"]); print("    spec:", json.dumps(s, ensure_ascii=False))'
done

echo; echo "## 3. etcd에 저장된 것 (/registry/horizontalpodautoscalers/$NS/web)"
etcd_show /registry/horizontalpodautoscalers/$NS/web autoscaling.alpha.kubernetes.io averageUtilization targetCPUUtilizationPercentage
echo "  protobuf 본문에는 필드 이름이 없고 번호만 있다(averageUtilization 없음). 그런데도 targetCPUUtilizationPercentage가 보이는 건"
echo "  managedFields(fieldsV1은 JSON) 때문이다. 관리자마다 자기가 쓴 apiVersion으로 필드 목록을 남긴다:"
$K get --raw /apis/autoscaling/v2/namespaces/$NS/horizontalpodautoscalers/web | python3 -c 'import json,sys; o=json.load(sys.stdin); [print("    manager=%s operation=%s apiVersion=%s fields=%s" % (m["manager"], m["operation"], m["apiVersion"], list(m["fieldsV1"].get("f:spec",{}).keys()))) for m in o["metadata"]["managedFields"]]'

echo; echo "## 4. $(ts) v2로만 표현되는 것 추가: memory 지표 + behavior (horizontalpodautoscalers.v2.autoscaling에 merge patch)"
$K -n $NS patch horizontalpodautoscalers.v2.autoscaling web --type=merge -p '{"spec":{"metrics":[
 {"type":"Resource","resource":{"name":"cpu","target":{"type":"Utilization","averageUtilization":50}}},
 {"type":"Resource","resource":{"name":"memory","target":{"type":"Utilization","averageUtilization":70}}}],
 "behavior":{"scaleDown":{"stabilizationWindowSeconds":60}}}}' | sed 's/^/  → /'
sleep 3

echo; echo "## 5. v1으로 읽으면: v1에 자리가 없는 정보가 annotation으로 나온다"
$K -n $NS get horizontalpodautoscalers.v1.autoscaling web -o json | python3 -c '
import json,sys; o=json.load(sys.stdin)
print("  apiVersion:", o["apiVersion"], "| targetCPUUtilizationPercentage:", o["spec"].get("targetCPUUtilizationPercentage"))
for k,v in sorted(o["metadata"].get("annotations",{}).items()):
    print("  annotation %s = %s" % (k, (v[:150]+"...") if len(v)>150 else v))'
echo "  v2로 읽으면:"
$K -n $NS get horizontalpodautoscalers.v2.autoscaling web -o json | python3 -c '
import json,sys; o=json.load(sys.stdin)
print("  apiVersion:", o["apiVersion"], "| annotation 수:", len(o["metadata"].get("annotations",{})))
print("  spec.metrics:", [(m["resource"]["name"], m["resource"]["target"]["averageUtilization"]) for m in o["spec"]["metrics"]])
print("  spec.behavior.scaleDown.stabilizationWindowSeconds:", o["spec"]["behavior"]["scaleDown"]["stabilizationWindowSeconds"])
print("  status.conditions:", [(c["type"], c["status"], c["reason"]) for c in o["status"].get("conditions",[])])'

echo; echo "## 6. etcd는 여전히 v2 한 벌 (annotation은 저장되지 않고 v1으로 변환할 때 만들어진다)"
etcd_show /registry/horizontalpodautoscalers/$NS/web memory autoscaling.alpha.kubernetes.io

echo; echo "## 7. $(ts) v1 클라이언트의 왕복: v1으로 GET 한 것을 그대로 PUT (kubectl replace)"
$K -n $NS get horizontalpodautoscalers.v1.autoscaling web -o json | $K replace -f - | sed 's/^/  → /'
echo "  (PUT 전 v2 순서는 cpu, memory였다)"
$K -n $NS get horizontalpodautoscalers.v2.autoscaling web -o jsonpath='  v2로 다시 읽은 metrics: {range .spec.metrics[*]}{.resource.name}={.resource.target.averageUtilization} {end}| behavior.scaleDown.stabilizationWindowSeconds={.spec.behavior.scaleDown.stabilizationWindowSeconds}{"\n"}'

echo; echo "## 8. $(ts) annotation을 모르는 v1 클라이언트가 자기 매니페스트로 덮어쓰면 (kubectl replace, annotation 없음)"
RV=$($K -n $NS get horizontalpodautoscalers.v1.autoscaling web -o jsonpath='{.metadata.resourceVersion}')
cat <<Y | $K replace -f - | sed 's/^/  → /'
apiVersion: autoscaling/v1
kind: HorizontalPodAutoscaler
metadata: {name: web, namespace: why-api, resourceVersion: "$RV"}
spec:
  scaleTargetRef: {apiVersion: apps/v1, kind: Deployment, name: web}
  minReplicas: 1
  maxReplicas: 3
  targetCPUUtilizationPercentage: 50
Y
$K -n $NS get horizontalpodautoscalers.v2.autoscaling web -o jsonpath='  v2로 다시 읽은 metrics: {range .spec.metrics[*]}{.resource.name}={.resource.target.averageUtilization} {end}| behavior: {.spec.behavior}{"\n"}'
echo "  (memory 지표와 behavior가 사라졌는지 위 줄로 판단)"

echo; echo "## 9. kubectl 함정: 짧은 이름에 버전을 붙이면(hpa.v1.autoscaling) 버전이 무시되고 preferredVersion으로 간다"
for r in hpa.v1.autoscaling horizontalpodautoscalers.v1.autoscaling; do
  printf '  kubectl get %-40s → %s\n' "$r" "$($K -n $NS get $r -v=6 2>&1 | grep -oE 'url="[^"]+"' | head -1)"
done

echo; echo "## 10. 정리"
$K -n $NS delete hpa web | sed 's/^/  /'
