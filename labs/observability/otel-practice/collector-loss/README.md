# Collector receipt, queue persistence, and backend commit

Local synthetic checkout workload generator → memory or disk Collector → durable capture gateway → Tempo → Grafana.

## Run

Requirements: Docker Compose v2, Python 3.10+. No host Python packages are needed for the experiment.

```sh
cd labs/observability/otel-practice/collector-loss
python3 run.py
cat out/results.txt
```

`run.py` **resets only this project's containers and volumes** using `docker compose down --volumes`. Existing evidence is moved to `history/<timestamp>/` before a new execution; no previous SQLite/Tempo data is mixed into a new run. Project name: `otel-practice-01`. No global prune or other project mutation.

- Grafana: http://localhost:27120 (local anonymous lab admin)
- Tempo API: http://localhost:27110
- Synthetic checkout HTTP service: http://localhost:27100
- Capture control/records: http://localhost:27180
- Memory/disk Collector OTLP HTTP: 27131 / 27132
- Memory/disk Collector health: 27191 / 27192

```sh
# Recheck the currently running evidence without starting a new experiment:
python3 verify.py
# Only after finishing screenshots / review:
docker compose down
# Remove this lab's data when desired:
docker compose down --volumes
```

## What each measurement means

The service is a small Python HTTP checkout **workload generator**, without OTel SDK or Java agent. It constructs valid OTLP JSON manually and sends one span per OTLP request. The one-millisecond span duration is synthetic and is not measured checkout latency. This deliberately removes SDK queue/batch/retry behavior from a Collector boundary experiment. All generated data is fictitious.

`POST /orders` returns a batch report to the caller. Its HTTP 200 is the workload report response, not a telemetry durability acknowledgement. `collector_accepted` counts the **separate** OTLP HTTP 200 responses with no partial rejection, observed by the generator. No batch processor sits between receiver and exporter. `sending_queue.wait_for_result: false` means queue admission can precede backend completion.

`capture_unique_persisted` counts distinct `(trace ID, span ID)` values in the gateway SQLite database after transaction commit (`journal_mode=WAL`, `synchronous=FULL`). The gateway forwards the same spans to Tempo **after** that commit. These are distinct durability/visibility boundaries: a capture commit does not prove Tempo durable storage. `tempo_unique_spans_queried` separately queries **every persisted unique span** by trace ID from Tempo and verifies the same span ID. It proves query visibility in this running instance, not survival of Tempo/disk failure.

Every received copy gets its own capture row. `duplicate_receipts` is total receipt rows minus unique ID pairs; Tempo may present deduplicated spans, so Grafana alone is not a delivery-count ledger. `accepted_missing` is the accepted ID set minus capture ID set. Exact raw generated IDs, accepted/rejected OTLP responses, capture rows and Tempo-confirmed IDs are saved in `out/`.

## Scenarios and assertions

1. Baseline: 10 generated/accepted/persisted IDs.
2. Backend outage without Collector crash: both queue types accept 20 and recover the exact 20 IDs.
3. Backend outage, then `SIGKILL` on both Collectors: assert capture empty before kill, reuse the disk volume, restart, recover the exact 20 disk IDs. Memory's 20 accepted IDs remain absent. A new memory-pipeline sentinel must arrive to prove the restarted pipeline is working.
4. Disk queue overflow: 140 one-span requests into queue capacity 100 while backend refuses all sends. Assert both accepted and rejected sets nonempty, recover exactly the accepted set, and no rejected IDs enter capture. Exact rejected count is an observation, not a general formula for other batching/consumer configurations.
5. Lost success acknowledgement: the capture gateway commits and Tempo receives a span, then gateway intentionally returns one 503 per unique trace. Collector retries. Three spans yield six receipt rows / three unique IDs. This injects a failed acknowledgement response, rather than literally dropping a network ACK packet.

Backend outage is a deterministic HTTP 503 injection at the gateway receiver; Tempo itself stays online. Collector consumer retries get 503 with no commit during the outage. This isolates the Collector-to-backend boundary and does not test Tempo outage behavior.

Readiness and ID-set polling determine success. Short polling intervals pace retries; fixed sleep is not used as the sole pass criterion. Recovery timing is a single local observation affected by retry backoff and shared Docker resources, not a benchmark.

## Versions and constraints

Collector contrib **0.162.0**, Tempo **2.10.8**, Grafana **13.2.3**, Python image **3.12-slim** (the minor-tag image is not digest pinned). Collector's persistent queue uses a project Docker volume and `file_storage.fsync: true`. The file-storage Collector runs as root solely to make its isolated local Docker volume writable. Production deployment should set volume ownership and a restricted service user.

Not covered: SDK buffers, Collector `batch` processor, host power loss, volume deletion, full disk, filesystem corruption, permanent export errors, multi-Collector routing, Tempo crash/recovery or remote object storage. `max_elapsed_time: 0s` means unlimited retry duration for retryable errors; it cannot rescue a request rejected before queue admission. No exactly-once claim follows from this experiment.

## Files and evidence

`service.py`, `memory.yaml`, `disk.yaml`, `tempo.yaml`, `compose.yaml`, `run.py`, `verify.py`. `out/summary.json` is machine-readable evidence; `out/results.txt` is the capture source; `out/compose.log` contains the retry, restart queue-load and queue-full logs. Raw evidence contains generated synthetic random trace IDs and timestamps, not real user data.

See `references.md` for version-specific official sources. Browser screenshots are in `posts/CS/Observability/otel-practice/images/lab-01/` relative to the repository root. `capture.py` recreates the Grafana screenshot using an existing Playwright/Chrome environment.

```sh
# Recreate only the browser capture, with an existing Playwright/Chrome environment:
python capture.py
# Show capture usage without contacting the stack:
python3 capture.py --help
```

The capture script runs the tracked `.claude/skills/blog-post-pipeline/assets/mask-check.py` before writing the screenshot. Activate your existing Playwright environment before the capture command.
