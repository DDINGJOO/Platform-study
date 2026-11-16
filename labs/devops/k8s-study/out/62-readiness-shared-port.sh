#!/usr/bin/env bash
# 80 포트가 겹치는 Deployment 에서 web2 에 readinessProbe(httpGet 80)를 달면, 네트워크를 같이 쓰는 web1 이 대신 응답해 프로브가 통과하는가 (Mac 에서 실행)
# 실습 저장소 루트에서 실행한다(./lab kubectl). 네임스페이스 blog-62 만 쓰고 지운다. web1 에는 프로브가 없다.
K="./lab kubectl"; NS=blog-62; D=probe-demo
now(){ perl -MTime::HiRes=time -e 'printf "%.1f", time'; }
echo "# 62 겹친 포트와 readinessProbe ($(date '+%F %T %Z'))"
$K create ns $NS >/dev/null
echo; echo "## kubectl apply (minReadySeconds 없음, progressDeadlineSeconds 30, web2 에만 readinessProbe)"
cat <<Y | $K apply -n $NS -f - 2>&1 | sed 's/^/  /'
apiVersion: apps/v1
kind: Deployment
metadata: {name: $D}
spec:
  replicas: 1
  progressDeadlineSeconds: 30
  selector: {matchLabels: {app: $D}}
  template:
    metadata: {labels: {app: $D}}
    spec:
      containers:
      - name: web1
        image: nginx:1.27-alpine
      - name: web2
        image: nginx:1.27-alpine
        readinessProbe:
          httpGet: {path: /, port: 80}
Y
echo "  저장된 web2 프로브: $($K get deploy $D -n $NS -o jsonpath='{.spec.template.spec.containers[1].readinessProbe}')"

echo; echo "## kubectl rollout status"
T0=$(now); out=$($K rollout status deploy/$D -n $NS --timeout=120s 2>&1); rc=$?
echo "  exit=$rc  $(perl -e "printf '%.1f', $(now)-$T0")초  마지막 줄: $(echo "$out" | tail -1)"

echo; echo "## 그 뒤 60초: 바뀔 때만 한 줄 (경과는 rollout status 시작부터)"
echo "  경과 | web2 ready 상태 재시작 | web1 ready | deploy ready/available | Progressing 사유"
last=""; end=$(( $(date +%s) + 60 ))
while [ $(date +%s) -lt $end ]; do
  p=$($K get pod -n $NS -l app=$D -o go-template='{{range .items}}{{range .status.containerStatuses}}{{if eq .name "web2"}}web2 ready={{.ready}} {{range $k,$v := .state}}{{$k}}{{if $v.reason}}({{$v.reason}}){{end}}{{end}} restarts={{.restartCount}}{{end}}{{end}} | {{range .status.containerStatuses}}{{if eq .name "web1"}}web1 ready={{.ready}}{{end}}{{end}}{{end}}' 2>/dev/null)
  d=$($K get deploy $D -n $NS -o jsonpath='ready={.status.readyReplicas} available={.status.availableReplicas} | {.status.conditions[?(@.type=="Progressing")].reason}' 2>/dev/null)
  cur="$p | $d"
  [ "$cur" != "$last" ] && { printf '  +%5.1fs %s\n' $(perl -e "print $(now)-$T0") "$cur"; last=$cur; }
  sleep 0.5
done

POD=$($K get pod -n $NS -l app=$D -o jsonpath='{.items[0].metadata.name}')
echo; echo "## 프로브 요청을 받은 쪽: web1 의 nginx 접근 로그에서 kube-probe 요청 (web1 에는 프로브가 없다)"
$K logs -n $NS $POD -c web1 | grep -c 'kube-probe' | sed 's/^/  kube-probe 줄 수: /'
$K logs -n $NS $POD -c web1 | grep 'kube-probe' | head -2 | sed 's/^/  /'
echo; echo "## web2 의 마지막으로 죽은 실행 로그"
$K logs -n $NS $POD -c web2 --previous 2>&1 | grep -E 'emerg' | head -3 | sed 's/^/  /'
echo; echo "## 파드 이벤트 (사유별 횟수)"
$K get events -n $NS --field-selector involvedObject.name=$POD -o go-template='{{range .items}}{{.reason}} x{{.count}}  {{.message}}{{"\n"}}{{end}}' | sed 's/^/  /'
echo; echo "## Deployment conditions (마지막)"
$K get deploy $D -n $NS -o jsonpath='{range .status.conditions[*]}  {.type}={.status} {.reason}{"\n"}{end}'
$K delete ns $NS --wait=false >/dev/null
echo; echo "  네임스페이스 $NS 삭제 요청"
