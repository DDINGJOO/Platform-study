# Official references checked on 2026-10-23

- [Collector exporter helper v0.162.0](https://github.com/open-telemetry/opentelemetry-collector/blob/v0.162.0/exporter/exporterhelper/README.md): queue admission, `wait_for_result`, `sizer`, `queue_size`, `num_consumers`, overflow before retry, persistent queue replay and retry duration. Primary basis for experiment settings.
- [OTLP HTTP exporter v0.162.0](https://github.com/open-telemetry/opentelemetry-collector/blob/v0.162.0/exporter/otlphttpexporter/README.md): canonical component name `otlp_http`, JSON encoding, compression disabled. The older `otlphttp` alias is deprecated in this version.
- [File storage extension v0.162.0](https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/v0.162.0/extension/storage/filestorage/README.md): writable directory, `create_directory`, `fsync` and storage constraints. This lab explicitly uses `fsync: true`.
- [Collector resiliency documentation](https://opentelemetry.io/docs/collector/resiliency/): general failure categories, persistent queue, retries, queue overflow and disk failure. This page is rolling documentation; pinned settings above are the version authority.
- [OTLP specification](https://opentelemetry.io/docs/specs/otlp/): JSON/HTTP trace export. The app uses valid OTLP JSON directly, with one span per request.
- [Tempo v2.10.8 release](https://github.com/grafana/tempo/releases/tag/v2.10.8) and [Tempo trace query API](https://grafana.com/docs/tempo/latest/api_docs/#query): query by trace ID; the actual API schema was checked against this running Tempo version.

No third-party tutorial, company repository, real telemetry, or external write is used.
