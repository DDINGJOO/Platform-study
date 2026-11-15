#!/usr/bin/env python3
"""Validate published claims against saved evidence, then validate the HTML assets."""
import collections
import hashlib
import importlib.util
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
EV = HERE / 'evidence'


def read(name):
    return json.loads((EV / (name + '.json')).read_text())


def kind(state, name):
    return [o for o in state['items'] if o['kind'] == name]


summary = read('summary')
for phase in ['rollout', 'replacement']:
    rows = read(phase + '-requests')
    successful = [r for r in rows if r['returncode'] == 0 and r['http'] == '200']
    assert len(rows) == summary[phase]['samples']
    assert len(successful) == summary[phase]['http200']
    assert [r for r in rows if r not in successful] == summary[phase]['errors']
    assert all(r['body']['request_id'] == r['id'] for r in successful)
assert collections.Counter(r['body']['version'] for r in read('rollout-requests')) == {'v1': 42, 'v2': 87}
assert collections.Counter(r['returncode'] for r in read('replacement-requests')) == {0: 108, 7: 8, 28: 3, 56: 1}

initial, unready, rolled, replaced = [read(n) for n in
    ['06-initial-state', '13-unready-state', '23-after-rollout', '25-after-replacement']]
services = [kind(s, 'Service')[0] for s in [initial, unready, rolled, replaced]]
assert len({s['metadata']['uid'] for s in services}) == 1
assert len({s['spec']['clusterIP'] for s in services}) == 1
assert services[0]['spec']['clusterIP'] == '10.98.233.106'
ep = kind(unready, 'EndpointSlice')[0]['endpoints'][0]
assert ep['addresses'] == ['10.244.194.93']
assert ep['conditions'] == {'ready': False, 'serving': False, 'terminating': False}
assert 'HTTP 503' in read('03-early-direct-readyz')['stdout']
assert 'HTTP 200' in read('03-early-direct-api-info')['stdout']
assert read('04-early-nodeport')['returncode'] == 7
assert read('15-unready-nodeport')['returncode'] == 7
assert 'HTTP 200' in read('14-unready-direct')['stdout']
app = next(o for o in kind(unready, 'Pod') if o['metadata']['name'].startswith('deploy-board'))
assert app['status']['phase'] == 'Running'
assert app['status']['containerStatuses'][0]['restartCount'] == 0
assert summary['before_delete']['uid'] != summary['after_delete']['uid']

# UID links prove ownership rather than relying on similar generated names.
pod = next(o for o in kind(initial, 'Pod') if o['metadata']['name'].startswith('deploy-board'))
rs = next(o for o in kind(initial, 'ReplicaSet') if o['metadata']['uid'] == pod['metadata']['ownerReferences'][0]['uid'])
deployment = kind(initial, 'Deployment')[0]
assert rs['metadata']['ownerReferences'][0]['uid'] == deployment['metadata']['uid']
assert 'internal-first-57' in read('11-app-logs')['stdout']
assert 'internal-first-57' in read('10-internal-http')['stdout']
assert '10.98.233.106' in read('09-dns')['stdout']
assert read('28-client-cleanup')['returncode'] == 0
assert json.loads(read('30-final-external-http')['stdout'])['version'] == 'v2'

runtime = read('final-runtime')
spaces = runtime['commands'][0]['stdout'].splitlines()
assert spaces[0] == spaces[1] and spaces[0] != spaces[2]
assert runtime['pod']['uid'] == summary['after_delete']['uid']
assert runtime['sandbox']['network']['ip'] == summary['after_delete']['ip']
route = json.loads(runtime['commands'][-1]['stdout'])[0]
assert route['dev'] == 'cali01a59808126'
spec = json.loads((HERE / 'application-v1.json').read_text())
cm = next(x for x in spec['items'] if x['kind'] == 'ConfigMap')
assert cm['data']['app.py'] == (HERE / 'app.py').read_text()
assert cm['immutable'] is True

timeline = [json.loads(s) for s in (EV / 'timeline.jsonl').read_text().splitlines()]
assert all('error' not in row for row in timeline)
assert any(row['phase'] == 'rollout' and any(
    o['kind'] == 'EndpointSlice' and any(
        ep['conditions'].get('terminating') and ep['conditions'].get('serving')
        for ep in o.get('endpoints', [])) for o in row['objects']) for row in timeline)
assert any(row['phase'] == 'replacement' and not any(
    o['kind'] == 'EndpointSlice' and any(ep['conditions'].get('ready') for ep in o.get('endpoints', []))
    for o in row['objects']) for row in timeline)

module_spec = importlib.util.spec_from_file_location('post_validation', HERE.parent / 'calico-51-56/validate.py')
module = importlib.util.module_from_spec(module_spec)
module_spec.loader.exec_module(module)
style = re.search(r'<style>.*?</style>', (ROOT / '.claude/skills/tistory-sketch-post/assets/template.html').read_text(), re.S).group()
entry = json.loads((HERE / 'manifest.json').read_text())[0]
result = module.validate(entry, style)
assert not result['errors'], result
result['evidence'] = {'timeline_snapshots': len(timeline), 'rollout_http200': 129,
                      'replacement_http200': 108, 'replacement_failures': 12,
                      'ownership_uid_links': 'verified', 'service_identity_preserved': True,
                      'configmap_matches_source': True}
(HERE / 'validation.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(result, ensure_ascii=False, indent=2))
