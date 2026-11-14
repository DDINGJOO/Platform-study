#!/usr/bin/env bash
# 실습 저장소의 shared/components/04-apiserver-requests.sh 를 옮긴 것. 실습 저장소 루트에서 실행한다.
# kube-apiserver 가 "API 요청을 관리"한다는 것: kubectl 명령이 실제로 보내는 HTTP 요청, watch, 요청 공정 분배(APF) (Mac 에서 실행)
cd "$(dirname "$0")/../.."   # 실습 저장소 루트 (./lab 이 있는 곳)
K="./lab kubectl"
echo "# kube-apiserver 가 받는 요청 ($(date '+%F %T %Z'))"
echo; echo "## 1. kubectl get pod 한 번이 보내는 HTTP 요청 (-v=6)"
$K get pod -l app=myweb -v=6 2>&1 | grep -E 'GET|POST|PUT|PATCH|DELETE' | sed -E 's/^.*\] //' | sed -E 's#https://[0-9.]+:6443#https://<API서버>:6443#' | cut -c1-150
echo; echo "## 2. kubectl scale 은 PATCH 한 번 (-v=6)"
$K scale deploy myweb --replicas=5 -v=6 2>&1 | grep -E 'GET|PATCH|PUT' | sed -E 's/^.*\] //' | sed -E 's#https://[0-9.]+:6443#https://<API서버>:6443#' | cut -c1-150
echo; echo "## 3. watch: 컨트롤러·kubelet 이 쓰는 방식. 파드를 하나 만들고 지우는 동안 이벤트가 흘러옴"
( timeout 12 $K get --raw '/api/v1/namespaces/default/pods?watch=true&labelSelector=run%3Dwatch-demo' 2>/dev/null | python3 -c '
import sys,json
for line in sys.stdin:
    try: e=json.loads(line)
    except: continue
    o=e["object"]; st=o.get("status",{})
    print("   watch 이벤트:", e["type"], o["metadata"]["name"], "phase="+str(st.get("phase")), "node="+str(o["spec"].get("nodeName")), "rv="+o["metadata"]["resourceVersion"])' ) &
sleep 2; $K run watch-demo --image=registry.k8s.io/pause:3.10.2 --restart=Never >/dev/null; sleep 5; $K delete pod watch-demo --now >/dev/null; wait
echo; echo "## 4. 요청 공정 분배 (API Priority and Fairness): 누가 어떤 줄에 서나"
$K get flowschemas -o custom-columns='NAME:.metadata.name,PRIORITYLEVEL:.spec.priorityLevelConfiguration.name,PRECEDENCE:.spec.matchingPrecedence' | head -14
echo; echo "## 5. 지금까지 API 서버가 받은 요청 수 (verb 별, /metrics 의 apiserver_request_total 합)"
$K get --raw /metrics | python3 -c '
import sys,re,collections
c=collections.Counter()
for l in sys.stdin:
    if l.startswith("apiserver_request_total{"):
        v=re.search(r"verb=\"([A-Z]+)\"",l).group(1); c[v]+=float(l.rsplit(" ",1)[1])
for k,v in c.most_common(): print("   %-8s %d" % (k,v))'
