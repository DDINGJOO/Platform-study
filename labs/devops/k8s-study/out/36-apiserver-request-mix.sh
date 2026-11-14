#!/usr/bin/env bash
# 36편: API 서버가 가장 많이 받는 요청은 무엇인가. /metrics 의 apiserver_request_total 을 verb·리소스별로 묶고
# 매니페스트의 프로브 주기, Lease, Prometheus 수집 설정, APF FlowSchema 와 맞춰 본다. 조회만 한다.
# 실습 저장소 루트(./lab 이 있는 곳)에서 bash <이 스크립트> [저장해 둔 /metrics 파일] 로 실행
# 인자를 주면 그 파일을 집계하고(예: 36-apiserver-metrics-snapshot.txt) 주지 않으면 지금 /metrics 를 받는다.
set -u
K="./lab kubectl"
M=$(mktemp); trap 'rm -f "$M"' EXIT
echo "# API 서버가 받은 요청 구성 ($(date '+%F %T %Z'))"
if [ $# -ge 1 ]; then
  echo "  입력: 저장해 둔 /metrics 파일 $(basename "$1") (첫 줄에 받은 시각이 있다)"
  cp "$1" "$M"; NOW=$(sed -n '1s/^# 36편: \([0-9-]* [0-9:]*\) KST.*/\1/p' "$1")
else
  $K get --raw /metrics > "$M"; NOW=$(date '+%F %T')
fi
echo; echo "## 1. verb 와 대상별 누적 요청 수 (GET·PUT·CONNECT, 많은 순 3개)"
python3 - "$M" "$NOW" <<'PY'
import re,sys,collections,datetime
path,now=sys.argv[1],sys.argv[2]
start=None; c=collections.Counter(); by=collections.defaultdict(collections.Counter)
for l in open(path):
    if l.startswith("process_start_time_seconds"): start=float(l.split()[1])
    if not l.startswith("apiserver_request_total{"): continue
    lab=dict(re.findall(r'(\w+)="([^"]*)"', l.split("}")[0])); v=float(l.rsplit(" ",1)[1])
    if lab["verb"] not in ("GET","PUT","CONNECT"): continue
    t=lab["resource"] or "(경로)"
    if lab["subresource"]: t+=" "+lab["subresource"]
    if lab["group"]: t=lab["group"]+"/"+t
    c[lab["verb"]]+=v; by[lab["verb"]][t]+=v
s=datetime.datetime.fromtimestamp(start); n=datetime.datetime.strptime(now,"%Y-%m-%d %H:%M:%S")
el=(n-s).total_seconds()
print("  API 서버 프로세스 시작 %s, 집계 시각 %s, 경과 %d초" % (s.strftime("%F %T"), n.strftime("%F %T"), el))
for verb in ("GET","PUT","CONNECT"):
    print("  %-8s 합계 %6d (초당 %.2f)" % (verb, c[verb], c[verb]/el))
    for t,v in by[verb].most_common(3):
        print("      %-40s %6d (초당 %.2f, %s 의 %d%%)" % (t, v, v/el, verb, round(100*v/c[verb])))
PY
echo; echo "## 2. 매니페스트의 프로브 주기 (kube-apiserver 정적 파드)"
$K -n kube-system get pod kube-apiserver-k8s-master -o jsonpath='{range .spec.containers[0]}  readinessProbe {.readinessProbe.httpGet.path} {.readinessProbe.periodSeconds}초 | livenessProbe {.livenessProbe.httpGet.path} {.livenessProbe.periodSeconds}초 | startupProbe {.startupProbe.httpGet.path} {.startupProbe.periodSeconds}초{"\n"}{end}'
echo; echo "## 3. Lease (PUT 의 대상)"
$K get lease -A
echo; echo "## 4. Prometheus 수집 설정 가운데 API 서버 프록시를 거치는 job (CONNECT nodes/proxy 의 출처)"
$K -n monitoring get cm prometheus-server-conf -o jsonpath='{.data.prometheus\.yml}' | grep -n 'scrape_interval\|job_name\|proxy/metrics\|kubernetes.default.svc' | sed 's/^/  /'
echo; echo "## 5. 상태 확인·리더 선출·kubelet 요청을 받는 FlowSchema"
$K get flowschema probes system-leader-election system-node-high system-nodes -o json | python3 -c '
import json,sys
for f in json.load(sys.stdin)["items"]:
    s=f["spec"]; print("  %s -> %s (precedence %d)" % (f["metadata"]["name"], s["priorityLevelConfiguration"]["name"], s["matchingPrecedence"]))
    for r in s.get("rules",[]):
        subj=[x.get("user",x.get("group",x.get("serviceAccount",{}))).get("name") for x in r["subjects"]]
        print("      누가:", ", ".join(map(str,subj)))
        for nr in r.get("nonResourceRules",[]): print("      경로:", nr["nonResourceURLs"], nr["verbs"])
        for rr in r.get("resourceRules",[]): print("      리소스:", rr["resources"], rr["verbs"])'
$K get prioritylevelconfigurations exempt leader-election system node-high workload-high workload-low global-default
