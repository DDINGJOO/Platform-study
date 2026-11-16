#!/usr/bin/env bash
# 같은 포트(80)를 쓰는 컨테이너 둘을 한 파드에 넣으면 (Mac 에서 실행)
cd "$(dirname "$0")/../.."
K="./lab kubectl"; NS=ch05
echo "# 13 한 파드에 80 포트 컨테이너 둘 ($(date '+%F %T %Z'))"
echo; echo "## apply (API 서버가 막는지, 경고만 하는지)"
cat <<'Y' | $K apply -n $NS -f - 2>&1 | sed 's/^/  /'
apiVersion: v1
kind: Pod
metadata: {name: same-port}
spec:
  containers:
  - {name: web1, image: nginx:1.27-alpine, ports: [{containerPort: 80}]}
  - {name: web2, image: nginx:1.27-alpine, ports: [{containerPort: 80}]}
Y
sleep 40
echo; echo "## 40초 뒤"
$K get pod same-port -n $NS --no-headers | sed 's/^/  /'
$K get pod same-port -n $NS -o go-template='{{range .status.containerStatuses}}  {{.name}}: ready={{.ready}} restarts={{.restartCount}} {{range $k,$v := .state}}{{$k}}{{if $v.reason}}({{$v.reason}}){{end}}{{end}}{{"\n"}}{{end}}'
echo; echo "## 실패한 쪽 로그"
for c in web1 web2; do r=$($K get pod same-port -n $NS -o jsonpath="{.status.containerStatuses[?(@.name==\"$c\")].restartCount}"); [ "$r" -gt 0 ] && { echo "  [$c] 마지막으로 죽은 실행의 로그"; { $K logs same-port -c $c -n $NS 2>/dev/null || $K logs same-port -c $c -n $NS --previous 2>&1; } | tail -4 | sed 's/^/    /'; }; done
$K delete pod same-port -n $NS --wait=false >/dev/null
