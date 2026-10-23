# Sticky A/B: assignment, exposure, user-level denominators

Synthetic-only Python standard-library HTTP service, SQLite volume, Prometheus 3.15.0, Grafana 13.2.3. This implements a small local experiment; it does not deploy Unleash or Netflix's internal experimentation platform. The app runs Python3.12.15 from `python:3.12-slim`, pinned in Compose to the resolved SHA-256 manifest digest used in this run (the app has no third-party Python dependencies).

```bash
cd labs/devops/deployment-experiments/sticky-ab
python3 run.py
/Users/dding/.local/share/tistory-uploader/venv/bin/python capture.py
```

Docker Compose v2 and Python 3.9+ are required for the runner. Capture additionally uses the existing Playwright installation and system Chrome; no install is performed. `run.py` starts only project `deployment-experiments-02`, creates a new experiment ID per run, sends actual HTTP requests, restarts the application, asserts invariants and Prometheus values, and writes `out/summary.json`, `out/results.txt`, `out/events.json`. Before a rerun, existing article screenshots are copied into the previous `out/screenshots/`, then that entire `out/` moves to ignored `history/<UTC>/`. Before replacing screenshots, `capture.py` copies existing PNGs and the active summary to ignored `history/captures/<UTC>/`. The copied summary identifies the active experiment, not necessarily the older image if evidence was rerun before capture. Do not mix an old screenshot with a new summary. The named SQLite volume retains previous experiments; the HTTP API/export/metrics exposes the current experiment only.

- App: http://127.0.0.1:28280/summary
- Export: http://127.0.0.1:28280/export
- Prometheus: http://127.0.0.1:28290
- Actual Grafana dashboard: http://127.0.0.1:28200/d/sticky-ab/sticky-ab?orgId=1
- Limits: Python128MiB, Prometheus256MiB, Grafana1GiB, CPUs0.5/0.5/1. Grafana limit accommodates startup memory. All host ports bind loopback.

`run.py` leaves the stack up for inspection. Shut down only this project, retaining the database volume:

```bash
docker compose down
```

To reopen the recorded experiment rather than the Compose default, use the saved environment:

```bash
EXPERIMENT_ID=$(python3 -c 'import json; print(json.load(open("out/stack-environment.json"))["EXPERIMENT_ID"])') docker compose up -d
```

## Allocation contract

Input is JSON `[experiment_id, salt, user_id]` serialized UTF-8 with `ensure_ascii=False,separators=(',',':')`. Compute SHA-256, take its first8bytes as unsigned big-endian integer, then modulo10000. Buckets0–4999 map to A,5000–9999 to B. SHA-256 modulo mapping has negligible modulo bias in this teaching example; it does not guarantee exactly equal sample counts. Stored assignment is primary key `(experiment_id,user_id)`. Missing ID is HTTP400 instead of random assignment. The service accepts only IDs beginning `synthetic-user-`; use no real people or accounts.

Salt is a public experimental configuration value, not a secret and not anonymization. Changing experiment ID/salt changes the mapping. Startup rejects a changed salt/config under an existing experiment ID; use a new experiment ID for a new allocation. The integration run also computes how many of its400 assignments would change with a different salt, then actually starts the service with that salt and asserts the startup error.

SQLite transactions (`BEGIN IMMEDIATE`,15s busy timeout) serialize assignment/event updates; unique keys protect concurrent retries. Assignment and successful event write commit together. This is a single-node lab, not a horizontally scaled production event store.

## HTTP and event interface (shared with decision lab)

```bash
curl -s http://127.0.0.1:28280/entry -H 'Content-Type: application/json' -d '{"user_id":"synthetic-user-demo","request_id":"demo-entry"}'
curl -s http://127.0.0.1:28280/exposure -H 'Content-Type: application/json' -d '{"user_id":"synthetic-user-demo","request_id":"demo-seen"}'
curl -s http://127.0.0.1:28280/conversion -H 'Content-Type: application/json' -d '{"user_id":"synthetic-user-demo","request_id":"demo-buy"}'
```

These example mutations add a user to a live dashboard; recapture only after rerunning the isolated evidence experiment. No auth is provided; loopback and synthetic data only. `/entry` assigns and records entry. `/exposure` requires prior entry and is an explicit acknowledgement sent by this test client; it does not verify an actual browser painted the feature. `/conversion` requires exposure. Client-supplied `variant` is HTTP400. Invalid ordering is409. Repeated event returns200 with `inserted:false`. `request_id` is diagnostic metadata; dedup is **per user + event type + experiment**, including new IDs on retry. It is not a global idempotency key, payment deduplication, or purchase counter. Multiple purchases by one user intentionally count as one converted user. First-event timestamps are retained.

`GET /export` / `out/events.json`:

```json
{
  "schema_version": 1,
  "experiment_id": "checkout-copy-v1",
  "assignments": [{"experiment_id":"checkout-copy-v1","user_id":"synthetic-user-demo","variant":"A","bucket":100}],
  "events": [{"event_id":1,"experiment_id":"checkout-copy-v1","user_id":"synthetic-user-demo","variant":"A","event_type":"entry","request_id":"demo-entry","occurred_at":"2026-10-23T00:00:00.000001+00:00"}]
}
```

Example fields show shape, not measured assignment. `event_id` is a monotonically increasing SQLite integer; gaps are possible because duplicate inserts are ignored. `event_type` is `entry|exposure|conversion`; UTC timestamp string. Events have unique `(experiment_id,user_id,event_type)`. Array sorted by `event_id`. `assignments` sorted by user ID. Third article reads this format independently and may add `request` fixture events for error/latency guardrails, not emitted by this service.

## Evidence and interpretation

The runner uses400 synthetic users, four entry submissions per user (initial, same-ID retry, refresh, after restart), two exposure submissions per exposed user, and two conversion submissions per converted user. Users with index divisible by5 never send exposure. Synthetic conversions are intentionally generated by user-index rules conditional on assignment; they provide no product-effect evidence.

The saved run has A202/B198 assignments,160/160 exposed users,46/37 converted users. Thus A46/160=28.75%, B37/160=23.125% (Grafana rounds to23.13%; Python text output uses23.12%).1600 entry requests represent400 users;640 exposure requests represent320 users;166 conversion requests represent83 users. Both groups' exposed-user denominators happen to be160 in this run; equality is not enforced. All400 assignments survive repeats/restart. Full export before/after restart and after retries is identical. Changed salt would remap182/400 users; actual startup rejects changed configuration.

`ab_users{experiment_id,variant,stage}` is a SQLite-derived gauge, including assigned/entry/exposure/conversion snapshots. `ab_event_attempts_total{experiment_id,event_type}` counts **accepted** submissions, including duplicates, and persists in the same SQLite database. HTTP400/409 rejections do not count. Neither metric includes `user_id`/requestID. Raw user-level event records stay in SQLite/export, not metric labels. Prometheus checks compare exposure series to database summaries; Grafana uses these actual series. Statistical sample planning, SRM, intervals, and winner decisions belong to article3.

## Sources

- [Unleash stickiness](https://docs.getunleash.io/concepts/stickiness): stable context/group ID and reshuffle implications; Unleash itself uses MurmurHash, unlike this lab's SHA-256.
- [Unleash A/B testing](https://docs.getunleash.io/guides/a-b-testing): stable variants and measuring outcomes.
- [Netflix engineering: experimentation platform](https://medium.com/netflix-techblog/its-all-a-bout-testing-the-netflix-experimentation-platform-4e1ca458c15): allocation does not imply exposure to the relevant experience.
- [Prometheus instrumentation](https://prometheus.io/docs/practices/instrumentation/) and [metric naming](https://prometheus.io/docs/practices/naming/): avoid unbounded user ID labels.
- [Python hashlib](https://docs.python.org/3.12/library/hashlib.html), [sqlite3 transactions](https://docs.python.org/3.12/library/sqlite3.html#transaction-control), [SQLite UNIQUE](https://www.sqlite.org/lang_createtable.html#unique_constraints).
