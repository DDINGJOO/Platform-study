#!/usr/bin/env python3
"""Read-only assertions over real run evidence and live Kayenta report endpoints."""
import datetime,json,math,pathlib,statistics
from urllib.request import urlopen
ROOT=pathlib.Path(__file__).resolve().parent;OUT=ROOT/'out'
summary=json.loads((OUT/'summary.json').read_text())
logs=[json.loads(line) for line in (OUT/'prometheus-queries.jsonl').read_text().splitlines() if line.strip()]
ips=json.loads((OUT/'kayenta-runtime.json').read_text())['container_ips']
def epoch(s):return datetime.datetime.fromisoformat(s.replace('Z','+00:00')).timestamp()
lines=['Actual Kayenta + fresh-baseline comparison','Spinnaker 2026.1.3 | NetflixACAJudge-v1.0','A-prime / B: 0.5 CPU, 96MiB, 4 requests/s each','Warmup 46s | observe 120s | scrape 2s | query step 2s','20% allowed mean latency increase fixed before measurement','scenario        A-prime(ms) B(ms) points/side requests/side score verdict']
assert len(summary['cases'])==2
for row in summary['cases']:
 label=row['scenario'];expected='Pass' if label=='same-version' else 'Fail'
 final=json.loads((OUT/f'{label}-kayenta.json').read_text());judge=final['result']['judgeResult']
 assert final['complete'] and final['status'].lower()=='succeeded'
 assert all(v=='succeeded' for v in final['stageStatus'].values())
 assert judge['judgeName']=='NetflixACAJudge-v1.0'
 assert judge['score']['classification']==expected and judge['score']['score']==(100 if expected=='Pass' else 0)
 assert judge['results'][0]['classification']==('Pass' if expected=='Pass' else 'High')
 series=json.loads((OUT/f'{label}-prometheus-series.json').read_text())
 pairs=json.loads((OUT/f'{label}-kayenta-metric-pairs.json').read_text())
 request=json.loads((OUT/f'{label}-analysis-request.json').read_text())
 cp=request['scopes']['default']['controlScope'];ep=request['scopes']['default']['experimentScope']
 assert (cp['start'],cp['end'],cp['step'])==(ep['start'],ep['end'],ep['step'])
 assert epoch(cp['end'])-epoch(cp['start'])==120 and cp['step']==2
 for role,key in [('baseline','control'),('canary','experiment')]:
  vals=series['warm'][role];actual=pairs[0]['values'][key]
  assert len(vals)==len(actual)==61
  assert all(math.isfinite(float(v[1])) for v in vals)
  assert all(math.isclose(float(a[1]),b,rel_tol=1e-9) for a,b in zip(vals,actual))
  query=f'1000 * sum(rate(orders_duration_seconds_sum{{role="{role}"}}[10s])) / sum(rate(orders_duration_seconds_count{{role="{role}"}}[10s]))'
  found=[r for r in logs if r.get('httpRequest',{}).get('clientIP') in ips and r['params']['query']==query and epoch(r['params']['start'])==epoch(cp['start']) and epoch(r['params']['end'])==epoch(cp['end']) and r['params']['step']==2]
  assert found,(label,role,'missing actual Kayenta Prometheus query')
 meta=json.loads((OUT/f'{label}-start-metadata.json').read_text())
 assert meta['baseline']['version']=='v1' and meta['canary']['version']==('v1' if expected=='Pass' else 'v2')
 assert meta['baseline']['regression_ms']==0 and meta['canary']['regression_ms']==(0 if expected=='Pass' else 40)
 assert abs(meta['baseline']['started_epoch']-meta['canary']['started_epoch'])<3
 assert meta['baseline']['cache_items']==meta['canary']['cache_items']==0
 assert meta['old']['cache_items']==128
 containers=json.loads((OUT/f'{label}-containers.json').read_text())
 chosen=[r for r in containers if any(x in r['name'] for x in ('-baseline-','-canary-'))]
 assert len(chosen)==2 and chosen[0]['image_id']==chosen[1]['image_id']
 assert all(r['memory_bytes']==96*1024*1024 and r['nano_cpus']==500000000 for r in chosen)
 observations=json.loads((OUT/f'{label}-http-observations.json').read_text())
 for role,obs in observations.items():
  warm=[r for r in obs if epoch(cp['start'])<=r['epoch']<=epoch(cp['end'])]
  assert len(warm)==row['request_counts'][role]>=479
  assert all(not r['cache_miss'] for r in warm)
 assert abs(row['request_counts']['baseline']-row['request_counts']['canary'])<=1
 with urlopen(f"http://localhost:28101/v2/canaries/canary/{row['config_id']}/{row['run_id']}?storageAccountName=memory",timeout=20) as response:
  live=json.load(response);assert live['result']['judgeResult']['score']==judge['score']
 a=row['mean_latency_ms']['baseline'];b=row['mean_latency_ms']['canary']
 lines.append(f"{label:15} {a:11.3f} {b:5.3f} {len(pairs[0]['values']['control']):11} {row['request_counts']['baseline']:13} {judge['score']['score']:5.0f} {expected}")
 lines.append(f"  Cold diagnostic only: old A={row['cold_mean_latency_ms']['old']:.3f}ms, fresh A-prime={row['cold_mean_latency_ms']['baseline']:.3f}ms")
lines+=['ASSERTIONS: PASS','All 4 judge input series match real Prometheus values (61 points each).','Actual Kayenta client IP query-log provenance: PASS','Actual Gate report responses: PASS','Rollout owner: Docker Compose script; analysis owner: embedded Orca','Deck http://localhost:28100 | Grafana http://localhost:28105/d/fresh-baseline']
text='\n'.join(lines)+'\n';(OUT/'results.txt').write_text(text);print(text)
