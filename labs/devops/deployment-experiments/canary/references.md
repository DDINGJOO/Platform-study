# Official sources checked on 2026-10-23

Spinnaker release2026.1.3 source SHA: `a59b1887bb66ae3e5d92b98782abbde7e2eef70e`. All implementation source links below pin that SHA.

- [Release](https://github.com/spinnaker/spinnaker/releases/tag/spinnaker-release-2026.1.3), [BOM](https://storage.googleapis.com/halconfig/bom/2026.1.3.yml): component versions and official registry.
- [Netflix's original Kayenta explanation](https://netflixtechblog.com/automated-canary-analysis-at-netflix-with-kayenta-3260bc7acc69): old production, fresh baseline and fresh canary comparison rationale. This historical source explains methodology, not current image configuration.
- [Spinnaker canary best practices](https://spinnaker.io/docs/guides/user/canary/best-practices/): comparable baseline/canary and ≥50 time-series points. This lab does not reproduce recommended long production windows.
- [Judge semantics](https://spinnaker.io/docs/guides/user/canary/judge/): metric classification and weighted scoring.
- [Standalone Kayenta](https://github.com/spinnaker/spinnaker/blob/a59b1887bb66ae3e5d92b98782abbde7e2eef70e/kayenta/docs/kayenta-standalone.md): embedded Orca, Redis and analysis endpoints.
- [Actual CanaryController](https://github.com/spinnaker/spinnaker/blob/a59b1887bb66ae3e5d92b98782abbde7e2eef70e/kayenta/kayenta-web/src/main/java/com/netflix/kayenta/controllers/CanaryController.java): saved config execution and result retrieval.
- [PrometheusMetricsService](https://github.com/spinnaker/spinnaker/blob/a59b1887bb66ae3e5d92b98782abbde7e2eef70e/kayenta/kayenta-prometheus/src/main/java/com/netflix/kayenta/prometheus/metrics/PrometheusMetricsService.java): `customInlineTemplate`, `PromQL:` complete expressions, `${scope}` expansion and actual range-query calls.
- [NetflixACAJudge](https://github.com/spinnaker/spinnaker/blob/a59b1887bb66ae3e5d92b98782abbde7e2eef70e/kayenta/kayenta-judge/src/main/scala/com/netflix/kayenta/judge/NetflixACAJudge.scala): `analysisConfigurations.canary.effectSize` with `meanRatio`, `allowedIncrease`, `criticalIncrease`; judge uses Mann-Whitney classification and configured effect limits.
- [Memory storage configuration](https://github.com/spinnaker/spinnaker/blob/a59b1887bb66ae3e5d92b98782abbde7e2eef70e/kayenta/kayenta-objectstore-memory/src/main/java/com/netflix/kayenta/memory/config/MemoryConfiguration.java): actual in-memory configuration/object store account.
- [Deck canary report route](https://github.com/spinnaker/spinnaker/blob/a59b1887bb66ae3e5d92b98782abbde7e2eef70e/deck-kayenta/src/kayenta/navigation/canary.states.ts), [actual report service](https://github.com/spinnaker/spinnaker/blob/a59b1887bb66ae3e5d92b98782abbde7e2eef70e/deck-kayenta/src/kayenta/service/canaryRun.service.ts): real UI and Gate API used in browser captures.
- [Front50 application creation](https://github.com/spinnaker/spinnaker/blob/a59b1887bb66ae3e5d92b98782abbde7e2eef70e/front50/front50-web/src/main/java/com/netflix/spinnaker/front50/controllers/v2/ApplicationsController.java): metadata registration; no fake app API.
- [Prometheus query log](https://prometheus.io/docs/guides/query-log/), [Prometheus v3.15.0 config source](https://github.com/prometheus/prometheus/blob/v3.15.0/config/config.go): `global.query_log_file` captures actual queries, start/end/step.

Researcher source subset and registry manifest checks were supplied in `/tmp/deployment-docs.md`; the tracked links above are the reproducible references and do not require that workstation scratch file.
