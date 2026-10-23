#!/usr/bin/env python3
"""Real HTTP integration run. Archives previous out/; leaves its own stack up."""
import concurrent.futures
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)
OUT = ROOT / 'out'
if OUT.exists():
    image_dir = ROOT.parents[3] / 'posts/CS/DevOps/deployment-experiments/images/lab-02'
    old_images = list(image_dir.glob('*.png'))
    if old_images:
        (OUT / 'screenshots').mkdir(exist_ok=True)
        for image in old_images:
            shutil.copy2(image, OUT / 'screenshots' / image.name)
    archive = ROOT / 'history' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    archive.parent.mkdir(exist_ok=True)
    shutil.move(str(OUT), archive)
OUT.mkdir()
experiment = 'checkout-copy-v1-' + datetime.now(timezone.utc).strftime('%Y-%m-%d-%H-%M-%S')
env = dict(os.environ, EXPERIMENT_ID=experiment)


def compose(*args):
    return subprocess.run(['docker', 'compose', *args], env=env, check=True, capture_output=True, text=True)


def http(path, body=None, base='http://127.0.0.1:28280', expected=200):
    raw = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(base + path, raw, {'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            status, data = response.status, response.read()
    except urllib.error.HTTPError as err:
        status, data = err.code, err.read()
    assert status == expected, (path, status, data)
    try:
        return json.loads(data)
    except json.JSONDecodeError:
        return data.decode()


def ready(base, path):
    for _ in range(180):
        try:
            return http(path, base=base)
        except Exception:
            time.sleep(1)
    raise AssertionError('not ready: ' + base)


def event(kind, user, request, expected=200):
    return http('/' + kind, {'user_id': user, 'request_id': request}, expected=expected)


def prom(expr):
    return http('/api/v1/query?' + urllib.parse.urlencode({'query': expr}), base='http://127.0.0.1:28290')['data']['result']


compose('up', '-d')
ready('http://127.0.0.1:28280', '/ready')
ready('http://127.0.0.1:28290', '/-/ready')
users = [f'synthetic-user-{i:04d}' for i in range(400)]
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
    assigned = list(pool.map(lambda u: event('entry', u, u + '-entry'), users))
mapping = {r['user_id']: r['variant'] for r in assigned}
# Same request retry, then a new transport request: neither creates another unique user event.
for user in users:
    same = event('entry', user, user + '-entry')
    newer = event('entry', user, user + '-refresh')
    assert same['variant'] == newer['variant'] == mapping[user]
    assert not same['inserted'] and not newer['inserted']
http('/entry', {'request_id': 'missing-user'}, expected=400)
http('/entry', {'user_id': users[0], 'request_id': 'client-variant', 'variant': 'B'}, expected=400)
event('exposure', 'synthetic-user-never-entered', 'no-entry', expected=409)
event('conversion', users[0], 'too-early', expected=409)
exposed = [u for i, u in enumerate(users) if i % 5 != 0]
converters = [u for u in exposed if int(u.rsplit('-', 1)[1]) % (5 if mapping[u] == 'A' else 4) == 1]
for user in exposed:
    assert event('exposure', user, user + '-seen')['inserted']
    assert not event('exposure', user, user + '-seen')['inserted']
for user in converters:
    assert event('conversion', user, user + '-buy')['inserted']
    assert not event('conversion', user, user + '-buy-retry')['inserted']
before = http('/export')
compose('restart', 'app')
ready('http://127.0.0.1:28280', '/ready')
after_restart = http('/export')
assert before == after_restart, 'SQLite-backed assignments/events changed across restart'
for user in users:
    assert event('entry', user, user + '-after-restart')['variant'] == mapping[user]
after = http('/export')
assert before == after, 'post-restart retries changed user-level events'
data = http('/summary')
assert sum(v['assigned_users'] for v in data['variants'].values()) == 400
assert sum(v['entry_users'] for v in data['variants'].values()) == 400
assert sum(v['exposure_users'] for v in data['variants'].values()) == 320
assert sum(v['conversion_users'] for v in data['variants'].values()) == len(converters)
for variant, stats in data['variants'].items():
    expected_exposed = sum(mapping[u] == variant for u in exposed)
    expected_converted = sum(mapping[u] == variant for u in converters)
    assert stats['exposure_users'] == expected_exposed
    assert stats['conversion_users'] == expected_converted
    assert stats['conversion_rate'] == expected_converted / expected_exposed
# Prove changing the salt would remap users if stored assignment/config protection were absent.
import app
changed = sum(('A' if app.bucket(u, salt='changed-lab-salt', experiment=experiment) < 5000 else 'B') != mapping[u] for u in users)
assert 0 < changed < len(users)
# The ACTUAL service startup rejects changing the existing experiment's configuration.
rejected = subprocess.run(['docker', 'compose', 'run', '--rm', '-e', 'ASSIGNMENT_SALT=changed-lab-salt', 'app', 'python', '/app/app.py'], env=env, capture_output=True, text=True)
assert rejected.returncode != 0 and 'Existing experiment configuration changed' in rejected.stderr
for _ in range(30):
    observed = prom('ab_users{stage="exposure"}')
    if {r['metric']['variant']: int(float(r['value'][1])) for r in observed} == {v: d['exposure_users'] for v, d in data['variants'].items()}:
        break
    time.sleep(1)
else:
    raise AssertionError('Prometheus did not scrape expected exposure user counts')
ready('http://127.0.0.1:28200', '/api/health')
checks = {'users_tested': 400, 'assignment_stable_on_refresh_and_restart': True, 'restart_export_identical': True,
          'missing_user_http': 400, 'client_variant_http': 400, 'exposure_without_entry_http': 409,
          'conversion_without_exposure_http': 409, 'changed_salt_would_remap_users': changed,
          'changed_salt_existing_experiment_startup_rejected': True,
          'user_ids_in_metric_labels': False, 'prometheus_exposure_values_verified': True}
assert 'user_id=' not in urllib.request.urlopen('http://127.0.0.1:28280/metrics').read().decode()
report = {'schema_version': 1, 'generated_at': datetime.now(timezone.utc).isoformat(), **data, 'checks': checks,
          'images': {'python': 'python:3.12-slim@sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1', 'prometheus': 'prom/prometheus:v3.15.0', 'grafana': 'grafana/grafana:13.2.3'},
          'prometheus_evidence': observed}
(OUT / 'events.json').write_text(json.dumps(after, ensure_ascii=False, indent=2) + '\n')
(OUT / 'summary.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
(OUT / 'salt-rejection.txt').write_text(rejected.stderr)
(OUT / 'stack-environment.json').write_text(json.dumps({'EXPERIMENT_ID': experiment}, indent=2) + '\n')
lines = ['STICKY A/B — REAL HTTP + SQLITE + PROMETHEUS', 'Synthetic users only; no statistical winner decision.', '', f'Experiment: {experiment}', 'variant  assigned  entry  exposure  conversion  conversion/exposure']
for v, s in data['variants'].items():
    lines.append(f'{v:7}  {s["assigned_users"]:8}  {s["entry_users"]:5}  {s["exposure_users"]:8}  {s["conversion_users"]:10}  {s["conversion_rate"]:.2%}')
lines += ['', f'Accepted entry HTTP requests: {data["accepted_event_attempts"]["entry"]}; unique entry users: 400', f'Accepted exposure requests: {data["accepted_event_attempts"]["exposure"]}; unique exposed users: 320', f'Accepted conversion requests: {data["accepted_event_attempts"]["conversion"]}; unique converted users: {len(converters)}', '400/400 assignments stable after refresh + service restart', 'SQLite export before/after restart and retries: IDENTICAL', 'Missing user/client-supplied variant: HTTP 400', 'Exposure before entry / conversion before exposure: HTTP 409', f'Changed salt would remap {changed}/400 users; same experiment startup: REJECTED', 'Prometheus exposure counts match SQLite: PASS', 'No user_id metric labels: PASS']
(OUT / 'results.txt').write_text('\n'.join(lines) + '\n')
print('\n'.join(lines))
