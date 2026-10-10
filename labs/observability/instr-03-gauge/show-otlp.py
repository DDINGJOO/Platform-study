"""Collector debug 익스포터 로그에서 이름에 주어진 글자가 든 지표의 마지막 모습을 뽑는다.
사용: docker compose logs otel-collector --no-log-prefix | python3 show-otlp.py queue.size"""
import re, sys
keys = sys.argv[1:] or ["orders", "checkout", "order.payload"]
text = sys.stdin.read()
blocks = re.split(r"\nMetric #\d+\n", text)
last = {}
for b in blocks:
    m = re.search(r"-> Name: (\S+)", b)
    if not m or not any(k in m.group(1) for k in keys):
        continue
    keep = []
    for line in b.splitlines():
        line = line.rstrip()
        if re.search(r"-> (Name|Unit|DataType|IsMonotonic|AggregationTemporality):|^Data point attributes|^-> [a-z_.]+: (Str|Int|Bool|Double)\(|^(Value|Count|Sum|Min|Max):|ExplicitBounds|Buckets #", line.strip()):
            keep.append(line)
        if line.startswith("ResourceMetrics") or "\t{" in line:
            break
    last[m.group(1)] = keep
for name in sorted(last):
    print("\n".join(last[name])); print()
