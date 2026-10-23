#!/usr/bin/env python3
"""Read actual sticky-ab exports without rewriting their plan or claiming an effect."""
import argparse,gzip,hashlib,json,pathlib
from analysis import instant,srm
from report import render
ROOT=pathlib.Path(__file__).resolve().parent

def describe(payload):
    events={}
    for event in payload['events']:
        if event['event_id'] in events and events[event['event_id']]!=event:
            raise ValueError('conflicting event_id')
        events[event['event_id']]=event
    assignments={row['user_id']:row['variant'] for row in payload['assignments']}
    exposures={}
    for e in sorted(events.values(),key=lambda e:instant(e['occurred_at'])):
        if e['experiment_id']!=payload['experiment_id']:raise ValueError('foreign experiment event')
        if assignments.get(e['user_id'])!=e['variant']:raise ValueError('assignment mismatch')
        if e['event_type']=='exposure':exposures.setdefault(e['user_id'],e)
    converted=set()
    for e in events.values():
        if e['event_type']=='conversion':
            first=exposures.get(e['user_id'])
            if first is None or instant(e['occurred_at'])<instant(first['occurred_at']):
                raise ValueError('conversion without prior exposure')
            converted.add(e['user_id'])
    groups={}
    for v in ['A','B']:
        users={u for u,e in exposures.items() if e['variant']==v}
        groups[v]={'assigned_users':sum(x==v for x in assignments.values()),'exposed_users':len(users),'converted_users':len(users&converted),
            'conversion_rate_display':f'{len(users&converted)/len(users)*100:.3f}%' if users else 'n/a'}
    return {'allocation_srm_diagnostic':srm(groups['A']['assigned_users'],groups['B']['assigned_users']), 'exposure_srm_diagnostic':srm(groups['A']['exposed_users'],groups['B']['exposed_users']), 'groups':groups,'decision':'DESCRIPTIVE_ONLY','reason':'No predeclared mature outcome window/guardrails for this source in decision/plan.json; do not infer product lift.','unique_events':len(events),'source_experiment_id':payload['experiment_id']}
def main():
    ap=argparse.ArgumentParser();ap.add_argument('source');a=ap.parse_args()
    raw=pathlib.Path(a.source).read_bytes();payload=json.loads(raw)
    result=describe(payload);result['source_sha256']=hashlib.sha256(raw).hexdigest()
    (ROOT/'out/source-events.json.gz').write_bytes(gzip.compress(raw,mtime=0))
    (ROOT/'out/source-integration.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    summary=json.loads((ROOT/'out/summary.json').read_text());render(summary,ROOT/'out/index.html')
    print('Actual HTTP-event integration: DESCRIPTIVE_ONLY')
    print(json.dumps(result['groups'],indent=2))
if __name__=='__main__':main()
