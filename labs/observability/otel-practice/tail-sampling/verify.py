#!/usr/bin/env python3
"""Read-only verification of recorded IDs and relationships, optionally requery live Tempo."""
import argparse
import base64
import collections
import concurrent.futures
import datetime as dt
import json
from pathlib import Path

from run import http, spans_from_file

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "out"

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="requery all 182 known IDs from running Tempo")
    args = parser.parse_args()
    rows = json.loads((OUT / "requests.json").read_text())
    summary = json.loads((OUT / "summary.json").read_text())
    assert len(rows) == 182
    assert len({r['trace_id'] for r in rows}) == 182
    for mode in ["head", "tail", "head-tail"]:
        assert collections.Counter(r["lab.kind"] for r in rows if r["lab.mode"] == mode) == {"normal":40,"error":10,"slow":10}
    expected = {r["trace_id"] for r in rows if r["sdk_sampled"] and
                (r["lab.mode"] == "head" or (r["lab.mode"] in ["tail", "head-tail"] and r["lab.kind"] in ["error", "slow"]) or r["lab.mode"] == "late-long")}
    assert set(summary["expected_trace_ids"]) == expected
    output = sum([spans_from_file(n) for n in ["plain.jsonl", "short.jsonl", "long.jsonl"]], [])
    bytrace = collections.defaultdict(list)
    for s in output:
        bytrace[s['traceId']].append(s)
    assert set(bytrace) == expected
    def check_relationship(spans, decode=False):
        assert len(spans) == 2
        root = next(s for s in spans if s['name'] == 'checkout')
        child = next(s for s in spans if s['name'].startswith('inventory.'))
        assert child['parentSpanId'] == root['spanId']
        assert len({s['spanId'] for s in spans}) == 2
    for spans in bytrace.values():
        check_relationship(spans)
    ingress = spans_from_file('ingress.jsonl')
    assert {s['traceId'] for s in ingress} == {r['trace_id'] for r in rows if r['sdk_sampled'] and r['lab.mode'] != 'head'}
    assert len(ingress) == summary['ingress_unique_traces']*2
    saved = json.loads((OUT / "tempo-observed.json").read_text())
    def fetch(r):
        status, body = http('http://127.0.0.1:27201/api/traces/'+r['trace_id'])
        return r['trace_id'], {'status':status, 'trace':json.loads(body) if status==200 else None}
    if args.live:
        with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
            backend = dict(pool.map(fetch, rows))
    else:
        backend = saved
    assert {tid for tid,v in backend.items() if v['status']==200} == expected
    tempo_spans = []
    for tid in expected:
        spans = [s for batch in backend[tid]['trace']['batches'] for scope in batch['scopeSpans'] for s in scope['spans']]
        check_relationship(spans)
        for s in spans:
            assert base64.b64decode(s['traceId']).hex() == tid
        assert {base64.b64decode(s['spanId']).hex() for s in spans} == {s['spanId'] for s in bytrace[tid]}
        tempo_spans.extend(spans)
    for r in rows:
        assert r['http_status'] == (500 if r['lab.kind']=='error' else 200)
        if r['lab.mode']=='late-short':
            assert r['trace_id'] not in expected
        if r['lab.mode']=='late-long':
            assert r['trace_id'] in expected
    assert len(tempo_spans) == len(output) == summary['collector_spans']
    assert len(expected) == summary['collector_unique_traces'] == summary['tempo_unique_traces']
    # Delayed export, rather than span duration, must be what differs in the late case.
    late = next(r for r in rows if r['lab.mode']=='late-long')
    late_spans = bytrace[late['trace_id']]
    duration_ms = (max(int(s['endTimeUnixNano']) for s in late_spans)-min(int(s['startTimeUnixNano']) for s in late_spans))/1e6
    assert duration_ms < 200
    print('Read-only verification: '+('live Tempo + saved Collector output' if args.live else 'saved evidence'))
    print('Checked UTC: '+dt.datetime.now(dt.timezone.utc).isoformat())
    print(f'HTTP requests: {len(rows)}; unique retained traces: {len(expected)}; spans: {len(output)}')
    print('Exact trace IDs, span IDs and parent-child relationships match Collector and Tempo.')
    print(f'Late trace duration: {duration_ms:.2f}ms; export delay: 5s; short=absent, long=present.')
    print('ALL ASSERTIONS PASSED')

if __name__ == '__main__':
    main()
