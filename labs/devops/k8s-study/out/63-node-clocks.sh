#!/usr/bin/env bash
# 노드마다 시계가 얼마나 다른가 (Mac 에서 실행). 같은 순간에 각 노드의 시각을 찍어 Mac 시각과 비교
cd "$(dirname "$0")/../.."
echo "# 03 노드 시계 차이 ($(date '+%F %T %Z'))"
for i in 0 1 2 3; do
  if [ $i = 0 ]; then n=k8s-master; else n=k8s-worker$i; fi
  mac=$(perl -MTime::HiRes=time -e 'printf "%.3f", time')
  vm=$(limactl shell $n -- date +%s.%N | cut -c1-14)
  mac2=$(perl -MTime::HiRes=time -e 'printf "%.3f", time')
  perl -e "printf \"  %-12s VM - Mac = %+7.3fs  (왕복 %.2fs)\n\", '$n', $vm - ($mac+$mac2)/2, $mac2-$mac"
  limactl shell $n -- timedatectl show -p NTPSynchronized -p NTP --value 2>/dev/null | paste -sd' ' - | sed 's/^/                NTP 켜짐·동기화: /'
done
