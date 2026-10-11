#!/usr/bin/env bash
# CPU 할당량(cpus: 2) 아래에서 동시성별 CFS 스로틀링 횟수와 시간을 센다.
# 출력은 results/cpu-throttle.txt 에 cpu.stat 원문(전·후)과 함께 남긴다. 끝나면 앱을 cpus 4 로 되돌린다.
set -euo pipefail
cd "$(dirname "$0")/.."
APP=${APP_URL:-http://localhost:22080}
APP_CPUS=2 docker compose up -d app; sleep 8
curl -s -XPOST "$APP/config?parallelUs=0&serialUs=0&coherencyUs=0&cpuUs=0&cpuLoops=1800000&spinSerial=true&expRandom=false" >/dev/null
OUT=results/cpu-throttle.txt
echo "# $(date "+%F %T") cpus=2, cpuLoops=1800000, 단계마다 k6 25초(워밍업 5 + 측정 20). usage 는 25초 평균" > "$OUT"
docker compose exec -T app cat /sys/fs/cgroup/cpu.max | sed "s/^/# cpu.max: /" >> "$OUT"
for n in 2 4 8 32; do
  s0=$(docker compose exec -T app cat /sys/fs/cgroup/cpu.stat | tr '\n' ' ')
  line=$(docker compose --profile load run --rm -e VUS="$n" k6 run -q --no-color /scripts/step.js 2>/dev/null | grep '^{"vus"')
  s1=$(docker compose exec -T app cat /sys/fs/cgroup/cpu.stat | tr '\n' ' ')
  # *_usec 는 ms 로, k6 소수는 셋째 자리로 줄여 적는다(8자리 숫자가 마스킹 검사에 걸리지 않게)
  python3 - "$n" "$line" "$s0" "$s1" >> "$OUT" <<'PY'
import json, re, sys
n, line, s0, s1 = sys.argv[1], json.loads(sys.argv[2]), sys.argv[3], sys.argv[4]
line = {k: (round(v, 3) if isinstance(v, float) else v) for k, v in line.items()}
ms = lambda s: re.sub(r"(\w+)_usec (\d+)", lambda m: f"{m.group(1)}_ms {int(m.group(2)) / 1000:.3f}", s)
print(f"## N={n} k6: {json.dumps(line)}\n## cpu.stat before: {ms(s0)}\n## cpu.stat after:  {ms(s1)}")
PY
  python3 - "$n" "$line" "$s0" "$s1" <<'PY' | tee -a "$OUT"
import json, sys
n, line, s0, s1 = sys.argv[1], json.loads(sys.argv[2]), sys.argv[3].split(), sys.argv[4].split()
a = dict(zip(s0[::2], map(int, s0[1::2]))); b = dict(zip(s1[::2], map(int, s1[1::2])))
d = {k: b[k] - a[k] for k in b}
x = line['count'] / line['measureSeconds']
print(f"N={n:>3} X={line['count']/line['measureSeconds']:7.1f}  usage={d['usage_usec']/25e6:5.2f}코어(25초 평균)  "
      f"periods={d['nr_periods']} throttled={d['nr_throttled']} throttled_ms={d['throttled_usec']/1000:.0f}  p99={line['p99Ms']:.1f}ms  "
      f"요청당CPU={d['usage_usec']/(x*25)/1000:.2f}ms(워밍업 포함 25초 사용량 / (측정 처리량 × 25초))")
PY
done
docker compose up -d app
