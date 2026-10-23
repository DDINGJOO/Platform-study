#!/usr/bin/env python3
"""Run fresh server-generated trace IDs against three modes and verify the exported graph, not just counts."""
import argparse
import base64
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import secrets
import subprocess
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'out'
COMPOSE = ['docker', 'compose', '-f', str(ROOT / 'compose.yaml')]
MODES = {'agent': 27381, 'micrometer': 27382, 'both': 27383}
EXPECTED_COUNTS = {'agent': 3, 'micrometer': 4, 'both': 7}

def command(*args):
    return subprocess.check_output(args, text=True, stderr=subprocess.STDOUT)

def get(url, headers=None):
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers or {}), timeout=5) as response:
        return json.load(response)

def poll(fn, message, timeout=90):
    end = time.monotonic() + timeout
    last = None
    while time.monotonic() < end:
        try:
            result = fn()
            if result:
                return result
        except (OSError, ValueError, KeyError) as error:
            last = str(error)
        time.sleep(.4)
    raise AssertionError(f'{message}: timeout; last={last}')

def save(name, data):
    (OUT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')

def attributes(items):
    return {x['key']: next(iter(x['value'].values())) for x in items}

def identifier(value):
    return base64.b64decode(value).hex() if value else ''

def normalize(data):
    spans = {}
    for batch in data.get('batches', data.get('resourceSpans', [])):
        resource = attributes(batch['resource'].get('attributes', []))
        for scoped in batch.get('scopeSpans', []):
            for span in scoped.get('spans', []):
                row = dict(span)
                row.update(traceId=identifier(span['traceId']), spanId=identifier(span['spanId']),
                           parentSpanId=identifier(span.get('parentSpanId', '')),
                           scope=scoped.get('scope', {}), resource=resource,
                           attributes=attributes(span.get('attributes', [])))
                spans[row['spanId']] = row
    return sorted(spans.values(), key=lambda row: int(row['startTimeUnixNano']))

def assert_graph(mode, spans, trace_id, parent_id, response):
    assert len(spans) == EXPECTED_COUNTS[mode], (mode, len(spans))
    assert {s['traceId'] for s in spans} == {trace_id}, (mode, 'trace split')
    ids = {s['spanId'] for s in spans}
    assert len(ids) == len(spans)
    assert {s['resource']['service.name'] for s in spans} == {mode}
    roots = [s for s in spans if s['parentSpanId'] == parent_id]
    assert len(roots) == 1, (mode, 'local root count')
    assert all(s['parentSpanId'] in ids | {parent_id} for s in spans), (mode, 'dangling parents')
    for span in spans:
        seen = {span['spanId']}
        current = span
        while current['parentSpanId'] != parent_id:
            parent = next(s for s in spans if s['spanId'] == current['parentSpanId'])
            assert parent['spanId'] not in seen, 'cycle'
            seen.add(parent['spanId'])
            current = parent
    counts = Counter(s['kind'] for s in spans)
    assert counts == ({'SPAN_KIND_SERVER': 2, 'SPAN_KIND_CLIENT': 1} if mode == 'agent' else
                      {'SPAN_KIND_SERVER': 2, 'SPAN_KIND_CLIENT': 1, 'SPAN_KIND_INTERNAL': 1} if mode == 'micrometer' else
                      {'SPAN_KIND_SERVER': 4, 'SPAN_KIND_CLIENT': 2, 'SPAN_KIND_INTERNAL': 1}), counts
    agent = [s for s in spans if s['scope']['name'].startswith('io.opentelemetry.')]
    boot = [s for s in spans if s['scope']['name'] == 'org.springframework.boot']
    assert len(agent) == (3 if mode != 'micrometer' else 0)
    assert len(boot) == (4 if mode != 'agent' else 0)
    quote = [s for s in spans if s['name'] == 'checkout.quote']
    assert len(quote) == (0 if mode == 'agent' else 1)
    if quote:
        assert quote[0]['attributes']['lab.request'] == response['request']
    sent_parent = response['child']['receivedTraceparent'].split('-')
    assert sent_parent[1] == trace_id
    outgoing = next(s for s in spans if s['spanId'] == sent_parent[2])
    assert outgoing['kind'] == 'SPAN_KIND_CLIENT'
    # On both, prove overlap semantically for each request scope. Counts alone are insufficient.
    if mode == 'both':
        for path in ['/checkout', '/inventory']:
            server_spans = [s for s in spans if s['kind'] == 'SPAN_KIND_SERVER' and
                            (s['attributes'].get('http.route') == path or s['attributes'].get('uri') == path)]
            assert len(server_spans) == 2
            assert len({s['scope']['name'] for s in server_spans}) == 2
            starts = [int(s['startTimeUnixNano']) for s in server_spans]
            ends = [int(s['endTimeUnixNano']) for s in server_spans]
            assert max(starts) < min(ends), 'server intervals must overlap'
        clients = [s for s in spans if s['kind'] == 'SPAN_KIND_CLIENT']
        assert len({s['attributes'].get('url.full', s['attributes'].get('http.url')) for s in clients}) == 1
        assert max(int(s['startTimeUnixNano']) for s in clients) < min(int(s['endTimeUnixNano']) for s in clients)
    sdk_versions = {s['resource']['telemetry.sdk.version'] for s in spans}
    assert sdk_versions == ({'1.66.0'} if mode == 'agent' else {'1.62.0'} if mode == 'micrometer' else {'1.62.0', '1.66.0'})
    if quote:
        assert quote[0]['parentSpanId'] == roots[0]['spanId']
        spring_client = next(s for s in boot if s['kind'] == 'SPAN_KIND_CLIENT')
        assert spring_client['parentSpanId'] == (quote[0]['spanId'] if mode == 'micrometer' else roots[0]['spanId'])
    if mode == 'both':
        assert outgoing['parentSpanId'] == roots[0]['spanId']
        for span in spans:
            if span['kind'] == 'SPAN_KIND_SERVER' and (span['attributes'].get('http.route') == '/inventory' or span['attributes'].get('uri') == '/inventory'):
                assert span['parentSpanId'] == outgoing['spanId']
    if mode == 'micrometer':
        assert response['traceId'] == response['child']['traceId'] == trace_id
        assert response['spanId'] == quote[0]['spanId']
        inventory = next(s for s in spans if s['name'] == 'http get /inventory')
        assert response['child']['spanId'] == inventory['spanId']
    if mode == 'agent':
        assert response['traceId'] == response['child']['traceId'] == 'empty', 'MDC API is not logging-event MDC'
    if mode == 'both':
        assert response['traceId'] == response['child']['traceId'] == trace_id
        assert response['spanId'] == roots[0]['spanId']
        assert response['spanId'] != quote[0]['spanId'], 'both log context is not custom span'
    return counts

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--requests', type=int, default=3)
    ap.add_argument('--no-build', action='store_true')
    args = ap.parse_args()
    assert args.requests > 0
    OUT.mkdir(exist_ok=True)
    # Deliberately replace this lab's evidence; fresh server-generated trace IDs exclude older Tempo data.
    for path in OUT.iterdir():
        if path.is_file():
            path.unlink()
    if not args.no_build:
        command(*COMPOSE, 'build', 'agent')
    command(*COMPOSE, 'up', '-d', '--no-build')
    for mode, port in MODES.items():
        poll(lambda: get(f'http://localhost:{port}/ready')['status'] == 'UP', f'{mode} ready')
    poll(lambda: get('http://localhost:27300/api/health').get('database') == 'ok', 'Grafana ready')
    summary = {'started_at_utc': datetime.now(timezone.utc).isoformat(), 'requests_per_mode': args.requests,
               'versions': {'java': '21', 'spring_boot': '4.1.1', 'micrometer_tracing': '1.7.1',
                            'javaagent': '2.32.0', 'agent_sdk': '1.66.0', 'boot_sdk': '1.62.0',
                            'collector': '0.162.0', 'tempo': '2.10.8', 'grafana': '13.2.3'},
               'modes': {}}
    lines = ['OTel practice 03: Java agent + Micrometer', f'UTC: {summary["started_at_utc"]}',
             'Boot 4.1.1 | Micrometer Tracing 1.7.1 | agent 2.32.0',
             'Trace identity + parent graph + semantic overlap + log correlation', '']
    for mode, port in MODES.items():
        measurements = []
        for index in range(args.requests):
            parent_id = ''
            request_id = f'{mode}-{secrets.token_hex(5)}'
            response = get(f'http://localhost:{port}/checkout?request={request_id}')
            trace_id = response['child']['receivedTraceparent'].split('-')[1]
            assert len(trace_id) == 32 and trace_id != '0' * 32
            def exported():
                data = get(f'http://localhost:27320/api/traces/{trace_id}')
                return data if len(normalize(data)) == EXPECTED_COUNTS[mode] else None
            raw = poll(exported, f'{mode} trace export')
            spans = normalize(raw)
            counts = assert_graph(mode, spans, trace_id, parent_id, response)
            save(f'{mode}-{index + 1}-tempo.json', raw)
            save(f'{mode}-{index + 1}-spans.json', spans)
            measurements.append({'trace_id': trace_id, 'root_parent_id': parent_id,
                                 'request_id': request_id, 'response': response,
                                 'unique_spans': len(spans), 'kinds': dict(counts),
                                 'scope_names': sorted({s['scope']['name'] for s in spans})})
        summary['modes'][mode] = measurements
        lines.append(f'{mode:10} requests={args.requests} spans/request={EXPECTED_COUNTS[mode]} graph=PASS')
    # Logs are actual Docker output, linked to each individual generated request, not fabricated data.
    logs = command(*COMPOSE, 'logs', '--no-color', 'agent', 'micrometer', 'both')
    run_requests = {m['request_id'] for records in summary['modes'].values() for m in records}
    logs = '\n'.join(line for line in logs.splitlines() if any(f'request={r}' in line for r in run_requests)) + '\n'
    (OUT / 'application.log').write_text(logs)
    for mode, measurements in summary['modes'].items():
        for measure in measurements:
            matching = [line for line in logs.splitlines() if f'request={measure["request_id"]}' in line]
            assert len(matching) == 3, (mode, 'three log lines per request', matching)
            for line in matching:
                key = 'traceId' if mode == 'micrometer' else 'trace_id'
                assert f'{key}={measure["trace_id"]}' in line, (mode, 'log trace mismatch')
            span_ids = {s['spanId'] for s in json.loads((OUT / f'{mode}-{measurements.index(measure) + 1}-spans.json').read_text())}
            for line in matching:
                key = 'spanId' if mode == 'micrometer' else 'span_id'
                value = re.search(rf'\b{key}=([a-f0-9]+)\b', line).group(1)
                assert value in span_ids, (mode, 'log span is not exported')
    lines += ['', 'agent: SERVER 2 + CLIENT 1; no checkout.quote span',
              'micrometer: SERVER 2 + CLIENT 1 + INTERNAL 1',
              'both: SERVER 4 + CLIENT 2 + INTERNAL 1',
              'both: /checkout and /inventory overlap across scopes: PASS',
              'both: HTTP CLIENT target + interval overlap: PASS',
              'all: single trace, known parents, log IDs exported: PASS',
              'both: checkout log span differs from checkout.quote: CONFIRMED',
              'Note: synchronous self-call only; no async/JDBC/overhead claim.']
    summary['completed_at_utc'] = datetime.now(timezone.utc).isoformat()
    summary['assertions'] = 'PASS'
    save('summary.json', summary)
    (OUT / 'results.txt').write_text('\n'.join(lines) + '\n')
    (OUT / 'compose-ps.txt').write_text(command(*COMPOSE, 'ps'))
    print('\n'.join(lines))

if __name__ == '__main__':
    main()
