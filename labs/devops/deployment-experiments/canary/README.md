# Fresh baseline A′ vs equally fresh canary B

Actual HTTP service replicas → actual Prometheus range queries → official Netflix Kayenta judge → official Spinnaker Deck report. Grafana shows measured release age, cache population, request rate and latency. All data is synthetic/local; no company services are involved.

## Reproduce

Requirements: Docker Compose v2, Python 3.9+, internet for the first official image pull, and sufficient Docker memory. This subset was designed for a shared 8GB Docker VM; it does **not** run the whole Spinnaker installation.

```sh
cd labs/devops/deployment-experiments/canary
python3 run.py
python3 verify.py
cat out/results.txt
```

`run.py` intentionally resets **only** Compose project `deployment-experiments-01`, including its Redis/Prometheus volumes. Existing output is moved to `history/<timestamp>/` before a new execution. Other labs and the existing kind cluster are not touched. A complete run includes two >2-minute observation windows and takes several minutes. `verify.py` is a read-only recheck and does not restart or reset the experiment.

Endpoints:

- Deck: http://localhost:28100
- Gate: http://localhost:28101
- Kayenta: http://localhost:28102
- Front50: http://localhost:28103
- Prometheus: http://localhost:28104
- Grafana: http://localhost:28105/d/fresh-baseline
- A / A′ / B local service: 28110 / 28111 / 28112

These unauthenticated demo endpoints bind loopback only. No public exposure or production installation is intended.

## What actually runs

Spinnaker **2026.1.3** official multiarch image digests are pinned in `compose.yaml`: Deck, Gate, Kayenta, Front50. Kayenta includes its own embedded Orca, which executes real fetch/judge analysis stages backed by Redis. Front50 stores actual application metadata in Redis. The official Kayenta memory account holds configs and analysis objects; this is the upstream implementation, but **Kayenta restart loses those config/results**. Raw results are saved to host `out/` so the evidence survives that restart, though the report UI requires live in-memory objects.

The outer rollout coordinator is **this lab's `run.py` calling Docker Compose**. It really recreates both baseline and canary containers. External Spinnaker Orca/Clouddriver deploy stages, cloud provisioning, traffic promotion, and automated production rollback are not implemented. Deck shows the actual Kayenta report, not a fabricated deployment pipeline graph. Grafana's rollout chart is actual Prometheus data from those real process restarts.

Prometheus **v3.15.0**, Grafana **13.2.3**, Redis **7.4**, Python base **3.12-slim**. Spinnaker component images are digest-pinned; the other version tags are not digest-pinned.

## Experimental controls fixed before measurement

- **A**: earlier-started v1 local replica. Load it until all 128 real in-memory cache entries exist. It is not long-lived production; exact process ages are recorded.
- **A′**: newly recreated v1 replica with empty cache.
- **B**: newly recreated replica, either same v1/no additional delay or v2 configuration with **40ms explicit injected delay**. Both scenarios use the same service image/code; the candidate version label and `REGRESSION_MS` environment variable are the controlled configuration changes. This is a synthetic configuration regression, not evidence of a real product release bug.
- A′/B: same local image ID, **0.5 CPU and 96MiB** limit, one process each. Container created/start timestamps and limits are recorded. Assert application process start delta <3 seconds.
- Each replica receives the identical cyclic key sequence (128 keys), open-loop **4 requests/second** from separate threads with a barrier. Response time does not decide the next request schedule. In this small experiment each request finishes before the next scheduled request; under overload this loader would lag, so actual achieved counts and rates must be checked.
- Cache misses add a deliberate **65ms synthetic I/O delay**; cache hits have **10–14ms** requested delay. A real in-process cache decides hit/miss; the delay models I/O rather than contacting an actual datastore. Measured duration includes actual elapsed time around that code, not a metric invented from the configured delay.
- Identical **46-second warmup** fills all 128 keys, plus enough time to exclude cold requests from the 10-second `rate` lookback. Primary observation is the same absolute **120-second** interval for A′ and B.
- Prometheus **2s scrape/2s query step** yields **61 points** per series (inclusive endpoints), exceeding the official ≥50-point laboratory recommendation. Consecutive rolling-rate points are correlated, not independent customer samples.
- Prespecified actual Kayenta `NetflixACAJudge-v1.0`, direction `increase`, critical latency metric, `effectSize.measure=meanRatio`, `allowedIncrease=criticalIncrease=1.20`. This **20% budget is chosen before measurement**; thresholds are not fitted to a desired outcome. One group/one metric weighted100; passing score95, marginal75. A score100 is a weighted classification score, not 100% confidence or a complete release-quality guarantee.

A vs A′ early-cold data is diagnostic only (shorter window, no release verdict). It demonstrates that comparing a warm old replica to a cold same-code replica confounds process/cache state with a release change. Primary release judgments compare **fresh A′ against equally fresh B after equal warmup**.

## Recorded run

| Case | A′ mean (ms) | B mean (ms) | Points/side | Requests/side | Actual judge |
|---|---:|---:|---:|---:|---|
| same-version | 13.001 | 13.005 | 61 | 480 | Pass (100) |
| regression | 13.484 | 53.807 | 61 | 480 | Fail (0) |

These values belong to the saved `out/summary.json`, not a claimed deterministic timing result. A rerun will produce new timing values and run IDs. The same-version early-cold diagnostic was old A=13.183ms versus fresh A′=78.448ms; that shorter window was **not** sent to the release judge.

## Provenance and assertions

`out/*-http-observations.json` saves actual HTTP responses with measured durations. `out/*-start-metadata.json` records app states/ages; `*-containers.json` records actual image IDs, creation/start time and Docker limits. `*-prometheus-series.json` contains exact range-query timepoints. `*-analysis-request.json` is the actual Kayenta request with identical baseline/canary timestamps and step. `*-kayenta.json` is the real completed judge response; stage context contains fetched metric-set IDs and queries. `prometheus-queries.jsonl` is the actual Prometheus query log; it independently shows matching Kayenta range queries.

`summary.json` contains measured numbers, run IDs and live Deck deep links. `results.txt` is a human-readable capture source. Verification asserts version/config boundaries, same resources/image, balanced actual request counts, ≥50 points, exactly matched Prometheus windows/query scopes, completed actual Kayenta execution, and expected pass/fail of the two cases.

## Capture / stop

Use an **existing** environment with Playwright and local Chrome; no package installation is performed:

```sh
CAPTURE_PYTHON="$HOME/.local/share/tistory-uploader/venv/bin/python"
"$CAPTURE_PYTHON" capture.py --help
"$CAPTURE_PYTHON" capture.py
# After reviewing live UI:
docker compose down
```

The script reads completed run IDs, opens the real Deck report/Grafana dashboard, waits for report data and runs the tracked repository `.claude/skills/blog-post-pipeline/assets/mask-check.py` before screenshots. Deck displays a 2-second step as `0.03333333333333333 mins`; that exact recurring decimal is explicitly allowed for capture after DOM/source review. Images live in `posts/CS/DevOps/deployment-experiments/images/lab-01/` at repository root.

## Troubleshooting and limits

- `python3 run.py` resets data: use `verify.py` to retain the same run.
- Initial downloads include several large official Java images; no emulation is required on arm64.
- Gate still requires a Clouddriver client bean even without using cloud resource pages. `services.clouddriver.enabled: false` prevents boot; this lab leaves the bean enabled against an unused loopback endpoint. No Clouddriver responses are stubbed.
- Gate/Front50 require a syntactically valid Fiat URL even with authentication disabled. The config supplies an unused loopback URL, while Fiat use is disabled.
- Some unused Deck global/resource requests return500 because Echo, external Orca and Clouddriver are absent. They are not mocked. Actual canary report/config requests must succeed; screenshots focus on the working report route. `/canary` alone is an abstract route; use `/canary/report` or the saved full run deep link.
- Config/report missing after Kayenta restart: the memory account is intentionally ephemeral. Rerun to rebuild a new actual report; do not paste saved fixtures into the UI.
- Short synthetic traffic, one latency metric, one instance per role, and 120s windows do not establish production safety, seasonality coverage, statistical power for product conversion, or rollback readiness. The experiment verifies integration and comparison discipline.

See `references.md` for official version-specific source links.
