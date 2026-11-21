#!/usr/bin/env bash
# Calico 의 cali 인터페이스 이름은 무엇에서 나오나: 같은 이름으로 다시 만든 파드, 다른 네임스페이스의 같은 이름 파드, 이름이 다른 파드의 cali 이름을 "cali" + SHA-1("네임스페이스.파드")의 앞 11자와 비교 (Mac 에서 실행)
# 실습 저장소 루트에서 실행한다(./lab kubectl). 네임스페이스 blog-79, blog-81 만 쓰고 지운다. 파드는 모두 k8s-worker2 에 고정한다.
K="./lab kubectl"; N=k8s-worker2
S(){ limactl shell $N -- "$@"; }
calc(){ printf 'cali%s' "$(printf '%s.%s' "$1" "$2" | shasum -a 1 | cut -c1-11)"; }
show(){ # 네임스페이스 파드 설명
  $K run $2 -n $1 --image=busybox:1.37 --overrides="{\"spec\":{\"nodeName\":\"$N\"}}" --command -- sleep 3600 >/dev/null
  $K wait pod/$2 -n $1 --for=condition=Ready --timeout=90s >/dev/null
  local ip dev exp idx rx
  ip=$($K get pod $2 -n $1 -o jsonpath='{.status.podIP}')
  dev=$(S ip route get $ip | grep -o 'dev [^ ]*' | cut -d' ' -f2)
  exp=$(calc $1 $2)
  idx=$(S cat /sys/class/net/$dev/ifindex); rx=$(S cat /sys/class/net/$dev/statistics/rx_packets)
  echo "  $3"
  printf '     %-12s IP=%-15s 경로 dev=%-16s 계산값=%-16s 일치=%-3s ifindex=%-3s rx_packets=%s\n' \
    "$1/$2" "$ip" "$dev" "$exp" "$([ "$dev" = "$exp" ] && echo yes || echo no)" "$idx" "$rx"
  LAST_DEV=$dev
}
echo "# 79 cali 이름과 네임스페이스·파드 이름 ($(date '+%F %T %Z')), 노드 $N"
for ns in blog-79 blog-81; do $K create ns $ns >/dev/null; done
echo "  계산 방법: printf '네임스페이스.파드' | shasum -a 1 의 앞 11자 앞에 cali"
echo
show blog-79 web "1) 처음 만든 파드"
D1=$LAST_DEV
$K delete pod web -n blog-79 --grace-period=1 >/dev/null
echo "  파드를 지운 뒤 노드에서 $D1 조회: $(S ip -br link show dev $D1 2>&1 | head -1)"
show blog-79 web "2) 같은 이름으로 다시"
show blog-81 web "3) 다른 네임스페이스"
show blog-79 web2 "4) 다른 파드 이름"
for ns in blog-79 blog-81; do $K delete ns $ns --wait=true >/dev/null; done
echo; echo "  정리: 네임스페이스 blog-79, blog-81 삭제 뒤 조회 결과: $($K get ns blog-79 blog-81 --no-headers 2>&1 | tr '\n' ' ')"
