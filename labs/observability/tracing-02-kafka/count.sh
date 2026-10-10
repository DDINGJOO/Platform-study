#!/bin/sh
# 최근 N초 동안 Tempo 에 쌓인 트레이스를 뿌리 스팬 이름별로 센다. 사용: ./count.sh [초]
S=${1:-120}; NOW=$(date +%s)
curl -s "http://localhost:${TEMPO_PORT:-25001}/api/search?q=%7B%7D&limit=5000&spss=1&start=$((NOW-S))&end=$NOW" |
  python3 -c "import json,sys,collections; c=collections.Counter(f\"{t.get('rootServiceName')} / {t.get('rootTraceName')}\" for t in json.load(sys.stdin)['traces']); [print(f'{v:6d}  {k}') for k,v in c.most_common()]"
