# 02. Tail sampling does not guarantee every failure trace

A real stdlib HTTP checkout service uses OpenTelemetry Python SDK spans, sends OTLP/HTTP to a Collector, and queries stored traces from Tempo. Grafana Explore shows the actual trace. Everything is fictional local data. No company repositories or identities are used.

## Versions and local URLs

- Python `3.12-slim`; OTel SDK/exporter `1.38.0`.
- Collector contrib `0.162.0`; Tempo `2.10.8`; Grafana `13.2.3`.
- Project name: `otel-practice-02` only. Published ports bind to loopback.
- Service: http://127.0.0.1:27210/health
- Grafana: http://127.0.0.1:27200 (anonymous local Admin, no external exposure).
- Tempo: http://127.0.0.1:27201/ready
- Collector health: http://127.0.0.1:27219/
- Collector metrics: http://127.0.0.1:27218/metrics
- Exact Grafana Explore link is recorded in `out/grafana-url.txt` after capture.

## Reproduce

From this directory:

```sh
python3 run.py --build
cat out/results.txt
```

`run.py` stops/recreates **only this compose project**, replaces the named generated evidence files, and starts an empty container-local Tempo. It never runs global prune or touches other projects. It polls readiness, makes 182 actual HTTP requests with eight threads, checks each HTTP status (the ten synthetic errors per main mode really return HTTP 500), and asserts the exact unique ID and span sets. A final extra ten-second window checks for unexpected arrivals. It leaves its stack running for manual inspection. If the stack is no longer needed:

```sh
docker compose down
```

`--run-id sampling-seed-a` is the default. SHA-256 of run/mode/case creates repeatable trace IDs; span IDs remain random. Each of head/tail/head-tail uses different trace IDs so Tempo cannot accidentally merge modes. Thus their head sample counts cannot be compared as paired requests, and no exact 25% finite population is promised. Modes `head` and `head-tail` both use SDK `ParentBased(TraceIdRatioBased(0.25))`; `tail`, `late-short`, and `late-long` use `ALWAYS_ON`.

## Experiment and assertions

Each main mode receives 40 normal + 10 error + 10 slow requests. Each request has a `checkout` server span and an `inventory.lookup` child. Slow requests actually sleep 320 ms. Error requests explicitly set OTel ERROR status; a plain HTTP status alone is not what the Collector's `status_code` policy tests.

| Mode | SDK sampler | Collector path |
| --- | --- | --- |
| head | probability 0.25, parent based | straight to Tempo |
| tail | always on | tail ERROR OR duration > 200ms (integer milliseconds), wait 2s |
| head-tail | probability 0.25, parent based | same 2s tail policy |
| late-short | always on | same 2s tail policy |
| late-long | always on | same policy, wait 8s |

The Collector latency policy checks the earliest span start through the latest end in its accumulated trace. It is not the sum of span durations. In each late case the root and error child execute for approximately 15ms, and the child end timestamp is captured before its export is delayed by five seconds. Therefore the long-wait result is caused by the error policy, not a five-second trace duration. Root arrives early; error child arrives after the 2s decision. Both decision caches are explicitly 1000 entries. The HTTP handler itself waits for the delayed export and returns after about five seconds; its root span is deliberately ended early to control the recorded trace duration. This is a deliberately constructed delayed-export case, not a faithful automatic server-span implementation or evidence about every async framework.

For the committed local snapshot `sampling-seed-a`:

| Mode | Normal stored/sent | Error stored/sent | Slow stored/sent |
| --- | --- | --- | --- |
| head | 10/40 | 3/10 | 1/10 |
| tail | 0/40 | 10/10 | 10/10 |
| head-tail | 0/40 | 5/10 | 1/10 |

Late error: short wait **0/1**, long wait **1/1**. Collector final output and Tempo each have **41 unique traces / 82 spans**. Tail ingress contains 81 unique traces / 162 spans. The tail non-sampled decision cache counter has one hit, and the early-capacity-drop counter is zero. The exact run timestamp is in `out/summary.json`. These counts describe this run and configuration, not universal retention or memory/performance guarantees.

Assertions reconcile:

1. Driver response populations and SDK sampling flags.
2. Pre-tail file exporter ingress against all sampled requests in tail paths.
3. Post-policy file exporters against the expected IDs; exactly two spans per retained request.
4. Backend `/api/traces/{trace_id}` 200/404 statuses for every known request; exact match to expected IDs.
5. Late-short absent and late-long present after the additional observation window.

Evidence: `out/requests.json`, `ingress.jsonl`, `plain.jsonl`, `short.jsonl`, `long.jsonl`, `tempo-observed.json`, `collector-metrics.txt`, `service.log`, `collector.log`, `images.json`, `summary.json`, `results.txt`. The pre-tail exporter is a local audit device and does not mean production should store unfiltered data before sampling.

## Read-only recheck without replacing evidence

```sh
python3 verify.py         # reconcile saved evidence only
python3 verify.py --live  # also requery every known trace ID from the running Tempo
```

The verifier checks exact trace IDs, span IDs, parent-child relationships, and that the late trace itself lasted under 200ms. It does not restart services or change evidence. The measured late-long trace is 15.96ms in this snapshot.

## Real screenshot

The existing uploader environment has Playwright and Chrome. From the repository root:

```sh
/Users/dding/.local/share/tistory-uploader/venv/bin/python labs/observability/otel-practice/tail-sampling/capture.py
/Users/dding/.local/share/tistory-uploader/venv/bin/python .claude/skills/blog-post-pipeline/assets/term-shot.py \
  --from labs/observability/otel-practice/tail-sampling/out/results.txt \
  --cmd 'python3 run.py --build' \
  --source labs/observability/otel-practice/tail-sampling/out/results.txt \
  --title 'OTel sampling: head vs tail' \
  -o posts/CS/Observability/otel-practice/images/lab-02/results.png
```

`capture.py` waits for the real `inventory.lookup` span, verifies the expected service and absence of no-data errors, saves visible DOM text, masks-checks it, then captures Grafana. It reads stored evidence and does not generate more service traffic. Capture again after a new run so screenshots and evidence stay aligned.

Screenshots live in `posts/CS/Observability/otel-practice/images/lab-02/`. They are actual Grafana/output captures, not generated charts. `out/grafana-visible.txt` and `out/results.txt` passed the text masking checker before the final captures.

## Resource note

Grafana initially exceeded a 256MiB cgroup limit during background plugin installation after the first capture. Its limit was raised to 384MiB and only Grafana was recreated; Tempo, Collector and request evidence were preserved. The final capture is from the recreated healthy Grafana. This is an environment limit encountered during the lab, not a benchmark.

## Limits

This is one Collector and one service with manual SDK instrumentation. It does not measure a production distributed application's service-boundary routing, load, memory, disk, transport reliability, restart behavior, or statistical sampling accuracy. No tail overflow is intentionally tested. Multiple Collector replicas would require routing all spans of a trace to the same sampler instance; that deployment was not executed here. Increasing wait may help a delayed-export case, but is not a blanket guarantee and raises the duration for which pending traces remain buffered. Keep unsampled request/error/latency metrics separately; this lab keeps complete HTTP response records and stdout logs but does not add a metrics backend.

## Official references checked

- [Collector contrib v0.162.0 tail sampler](https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/v0.162.0/processor/tailsamplingprocessor/README.md): policy combination, wait, late spans, decision caches, routing constraint; configuration used by the pinned image.
- [Collector contrib v0.162.0 policy code](https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/v0.162.0/processor/tailsamplingprocessor/internal/sampling/latency.go): earliest start/latest end latency calculation.
- [Collector contrib v0.162.0 internal telemetry](https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/v0.162.0/processor/tailsamplingprocessor/documentation.md): non-sampled decision cache hits and early-drop counters.
- [OTel Python v1.38.0 sampling implementation](https://github.com/open-telemetry/opentelemetry-python/blob/v1.38.0/opentelemetry-sdk/src/opentelemetry/sdk/trace/sampling.py): TraceIdRatioBased makes a creation-time decision from trace ID; ParentBased respects the parent.
- [OTel Python v1.38.0 exporter](https://github.com/open-telemetry/opentelemetry-python/blob/v1.38.0/exporter/opentelemetry-exporter-otlp-proto-http/src/opentelemetry/exporter/otlp/proto/http/trace_exporter/__init__.py): the chosen OTLP/HTTP transport.
- [Official sampling concepts](https://opentelemetry.io/docs/concepts/sampling/): head information loss before a downstream tail sampler. This is a living conceptual page; implementation-specific claims use the pinned sources above.
