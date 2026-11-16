#!/usr/bin/env bash
# SIGTERM 에 반응하지 않는 PID 1(sleep infinity) 파드를 지우면 STATUS 열·phase·deletionTimestamp·종료 코드가 어떤 순서로 바뀌나, restartPolicy Never vs Always (Mac 에서 실행)
# 실습 저장소 루트에서 실행한다(./lab kubectl). 네임스페이스 blog-63 만 쓰고 지운다.
K="./lab kubectl"; NS=blog-63
now(){ perl -MTime::HiRes=time -e 'printf "%.1f", time'; }
GT='{{.status.phase}} | del={{.metadata.deletionTimestamp}} grace={{.metadata.deletionGracePeriodSeconds}} | {{range .status.conditions}}{{if eq .type "PodReadyToStartContainers" "Ready"}}{{.type}}={{.status}} {{end}}{{end}}| {{range .status.containerStatuses}}{{range $k,$v := .state}}{{$k}}{{if $v.reason}}({{$v.reason}}){{end}}{{if $v.exitCode}} exit={{$v.exitCode}}{{end}}{{end}}{{end}}'
echo "# 63 지우는 중인 파드의 상태 변화 ($(date '+%F %T %Z'))"
$K create ns $NS >/dev/null
for rp in Never Always; do
  P=sleep-$(echo $rp | tr A-Z a-z)
  $K run $P -n $NS --image=busybox:1.37 --restart=$rp --command -- sleep infinity >/dev/null
  $K wait -n $NS pod/$P --for=condition=Ready --timeout=90s >/dev/null
  echo; echo "## restartPolicy: $rp (파드 $P, 노드 $($K get pod -n $NS $P -o jsonpath='{.spec.nodeName}'))"
  echo "  표기: 경과 STATUS열 | phase | deletionTimestamp deletionGracePeriodSeconds | 조건 | 컨테이너 상태"
  echo "  delete 요청 시각(Mac 시계, UTC): $(date -u '+%H:%M:%S')"
  T0=$(now); $K delete pod -n $NS $P --wait=false >/dev/null
  last=""
  while :; do
    st=$($K get pod -n $NS $P --no-headers 2>/dev/null | awk '{print $3}')
    cur=$($K get pod -n $NS $P -o go-template="$GT" 2>/dev/null) || { printf '  +%5.1fs (객체 없음)\n' $(perl -e "print $(now)-$T0"); break; }
    line="$st | $cur"
    [ "$line" != "$last" ] && { printf '  +%5.1fs %s\n' $(perl -e "print $(now)-$T0") "$line"; last=$line; }
    sleep 0.3
  done
done
$K delete ns $NS --wait=false >/dev/null
echo; echo "  네임스페이스 $NS 삭제 요청"
