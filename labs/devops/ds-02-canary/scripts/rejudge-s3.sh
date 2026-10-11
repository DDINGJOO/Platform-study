#!/usr/bin/env bash
# 시나리오 3 의 세 구간을 같은 끝 시각(end)으로 다시 판정한다.
# 처음 돌릴 때 판정 서버가 step 과 무관하게 10초 rate 창을 써서, step 30/60 판정이 점 사이 요청을 버렸다.
# judge.py 를 고친 뒤 이미지를 다시 넣고 이 스크립트로 같은 구간을 다시 판정했다.
set -euo pipefail
cd "$(dirname "$0")/.."
IN=results/raw/s3-lowtraffic.jsonl
OUT=results/raw/s3-lowtraffic-rejudged.jsonl
: > $OUT
python3 -c "
import json
seen=set()
for l in open('$IN'):
    d=json.loads(l)
    if 'metrics' not in d or d['rate'] in seen: continue
    seen.add(d['rate']); print(d['rate'], d['control'], d['experiment'], d['end'])
" | while read RATE B C END; do
  for step in 10 30 60; do
    curl -s "http://localhost:25080/judge?control=$B&experiment=$C&window=600&step=$step&end=$END&label=rate$RATE-step$step" \
      | python3 -c "import sys,json;d=json.load(sys.stdin);d['rate']='$RATE';print(json.dumps(d))" >> $OUT
  done
done
wc -l $OUT
