#!/usr/bin/env python3
"""Reset ONLY this compose, run real requests and reconcile SDK/Collector/Tempo IDs."""
import argparse
import concurrent.futures
import datetime as dt
import json
from pathlib import Path
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "out"
COMPOSE = ["docker", "compose", "-f", str(ROOT / "compose.yaml")]

def http(url):
    try:
        with urllib.request.urlopen(url, timeout=20) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()

def wait_ready(url):
    end = time.monotonic()+100
    while time.monotonic() < end:
        try:
            if http(url)[0] == 200:
                return
        except (OSError, TimeoutError):
            pass
        time.sleep(0.3)
    raise RuntimeError("not ready: " + url)

def spans_from_file(name):
    spans = []
    p = OUT / name
    if not p.exists():
        return []
    for line in p.read_text().splitlines():
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue  # A writer may still be flushing its last line.
        for rs in msg.get("resourceSpans", []):
            for ss in rs.get("scopeSpans", []):
                spans.extend(ss.get("spans", []))
    return spans

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default="sampling-seed-a")
    parser.add_argument("--build", action="store_true")
    args = parser.parse_args()
    started = dt.datetime.now(dt.timezone.utc).isoformat()
    # All storage in this project is container-local; recreate it and replace the explicitly named evidence files.
    subprocess.run(COMPOSE+["down", "--remove-orphans"], check=True)
    OUT.mkdir(exist_ok=True)
    for name in ["plain.jsonl", "short.jsonl", "long.jsonl", "ingress.jsonl", "summary.json", "results.txt", "requests.json", "tempo-observed.json", "collector-metrics.txt", "service.log", "collector.log", "images.json", "grafana-visible.txt", "grafana-url.txt", "verification.txt"]:
        (OUT / name).unlink(missing_ok=True)
    subprocess.run(COMPOSE+["up", "-d"]+(["--build"] if args.build else []), check=True)
    for url in ["http://127.0.0.1:27210/health", "http://127.0.0.1:27219/", "http://127.0.0.1:27201/ready", "http://127.0.0.1:27200/api/health"]:
        wait_ready(url)
    requests = []
    def checkout(job):
        mode, kind, case = job
        status, body = http("http://127.0.0.1:27210/checkout?" + urllib.parse.urlencode(dict(mode=mode, kind=kind, case=case, run=args.run_id)))
        record = json.loads(body)
        assert status == (500 if kind == "error" else 200), (status, record)
        return record
    jobs = [(mode, kind, f"{kind}-{i:02d}") for mode in ["head", "tail", "head-tail"]
            for kind, n in [("normal",40), ("error",10), ("slow",10)] for i in range(n)]
    jobs += [(mode, "late", "late-00") for mode in ["late-short", "late-long"]]
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        requests = list(pool.map(checkout, jobs))
    (OUT / "requests.json").write_text(json.dumps(requests, indent=2)+"\n")
    expected = {r["trace_id"] for r in requests if r["sdk_sampled"] and
                (r["lab.mode"] == "head" or (r["lab.mode"] in ["tail", "head-tail"] and r["lab.kind"] in ["error", "slow"]) or r["lab.mode"] == "late-long")}
    end = time.monotonic()+35
    while time.monotonic() < end:
        observed_spans = sum([spans_from_file(n) for n in ["plain.jsonl", "short.jsonl", "long.jsonl"]], [])
        ids = {s["traceId"] for s in observed_spans}
        if ids == expected:
            break
        time.sleep(0.25)
    assert ids == expected, {"missing": sorted(expected-ids), "unexpected": sorted(ids-expected)}
    # Continue observing beyond both decision waits. This tests absence over a stated window, not forever.
    time.sleep(10)
    observed_spans = sum([spans_from_file(n) for n in ["plain.jsonl", "short.jsonl", "long.jsonl"]], [])
    ids = {s["traceId"] for s in observed_spans}
    assert ids == expected
    assert len(observed_spans) == len(expected)*2, (len(observed_spans), len(expected))
    ingress = spans_from_file("ingress.jsonl")
    expected_ingress = {r["trace_id"] for r in requests if r["sdk_sampled"] and r["lab.mode"] != "head"}
    assert {s["traceId"] for s in ingress} == expected_ingress
    assert len(ingress) == 2*len(expected_ingress)
    # Validate backend receipt independently; 404 is expected only for intentionally unsampled known IDs.
    def backend(record):
        tid = record["trace_id"]
        status, body = http("http://127.0.0.1:27201/api/traces/"+tid)
        return tid, {"status": status, "trace": json.loads(body) if status == 200 else None}
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
        tempo = dict(pool.map(backend, requests))
    actual_tempo = {tid for tid,v in tempo.items() if v["status"] == 200}
    assert actual_tempo == expected, {"missing": list(expected-actual_tempo), "extra": list(actual_tempo-expected)}
    tempo_span_count = 0
    for tid in actual_tempo:
        backend_spans = [s for batch in tempo[tid]["trace"]["batches"] for scope in batch["scopeSpans"] for s in scope["spans"]]
        assert len(backend_spans) == 2, (tid, len(backend_spans))
        tempo_span_count += len(backend_spans)
    assert tempo_span_count == len(observed_spans)
    (OUT / "tempo-observed.json").write_text(json.dumps(tempo, indent=2)+"\n")
    stats = {}
    for mode in ["head", "tail", "head-tail", "late-short", "late-long"]:
        stats[mode] = {}
        for kind in (["late"] if mode.startswith("late") else ["normal", "error", "slow"]):
            group = [r for r in requests if r["lab.mode"] == mode and r["lab.kind"] == kind]
            stats[mode][kind] = {"requests": len(group), "sdk_sampled": sum(r["sdk_sampled"] for r in group),
                                 "stored": sum(r["trace_id"] in ids for r in group)}
    metrics = http("http://127.0.0.1:27218/metrics")[1].decode()
    (OUT / "collector-metrics.txt").write_text(metrics)
    for service in ["app", "collector"]:
        log = subprocess.run(COMPOSE+["logs", "--no-color", "--no-log-prefix", service], text=True, capture_output=True, check=True).stdout
        (OUT / ("service.log" if service == "app" else "collector.log")).write_text(log)
    images = json.loads(subprocess.run(COMPOSE+["images", "--format", "json"], text=True, capture_output=True, check=True).stdout)
    (OUT / "images.json").write_text(json.dumps(images, indent=2)+"\n")
    summary = {"started_utc": started, "completed_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "run_id": args.run_id,
               "versions": {"sdk": "1.38.0", "collector": "0.162.0", "tempo": "2.10.8", "grafana": "13.2.3"},
               "population_per_main_mode": {"normal":40, "error":10, "slow":10}, "head_probability": 0.25,
               "tail_latency_threshold_ms":200, "decision_wait_seconds": {"short":2,"long":8}, "late_export_delay_seconds":5,
               "additional_absence_observation_seconds":10, "stats":stats, "expected_trace_ids": sorted(expected),
               "collector_unique_traces":len(ids), "collector_spans":len(observed_spans), "tempo_unique_traces":len(actual_tempo), "tempo_spans":tempo_span_count,
               "ingress_unique_traces":len(expected_ingress), "assertions":"passed"}
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2)+"\n")
    lines = ["OTel sampling lab | executed real HTTP requests", "run: "+args.run_id, "started UTC: "+started,
             "SDK 1.38.0 | Collector 0.162.0 | Tempo 2.10.8 | Grafana 13.2.3", "", "mode         kind      sent   SDK sampled   Tempo stored"]
    for mode, kinds in stats.items():
        for kind,v in kinds.items():
            lines.append(f"{mode:<12} {kind:<8} {v['requests']:>5} {v['sdk_sampled']:>13} {v['stored']:>14}")
    lines += ["", f"Collector output: {len(ids)} unique traces / {len(observed_spans)} spans",f"Tempo confirmed: {len(actual_tempo)} unique traces", "late error: 5s export delay; short wait 2s vs long wait 8s", "Decision caches: sampled=1000, non-sampled=1000", "Absence rechecked for 10s after expected traces arrived", "ALL ASSERTIONS PASSED", "Finite head sample counts need not equal configured 25%."]
    text = "\n".join(lines)+"\n"
    (OUT / "results.txt").write_text(text)
    print(text)
    print("Evidence replaced. Article images are not refreshed: rerun capture.py and term-shot.py after this run.")

if __name__ == "__main__":
    main()
