# OTel 5편: Metrics 소스 확인 기록

블로그 원고의 공개 원자료와 확인 범위를 기록한다. 이 디렉터리는 실행 실험이나 성능 측정 결과를 담지 않는다. 시리즈의 Context/Trace runtime probe를 Metrics 검증 근거로 사용하지 않았다.

- 원고: `posts/CS/Observability/otel/05_5편 - 메트릭은 어디서 집계되고 누가 가져갈까.html`
- 저장소: `open-telemetry/opentelemetry-java`
- 태그: `v1.67.0`
- 커밋: `b4b3a1b354425c3f1411173c0e48cb24a1cba224`
- 문서 확인일: 2026-10-21. Micrometer 웹 문서는 1.17.1 표시 기준. OTel 웹 사양과 Java 릴리스 번호를 동일시하지 않는다.
- 소스 라이선스: Apache-2.0. 공개 원본은 읽기 전용으로 취급했다.

## 캡처 명세

[source-manifest.json](source-manifest.json)의 SHA-256은 raw URL에서 받은 **전체 파일 바이트**의 해시다. 발췌문 해시나 Git blob 식별자가 아니다. 두 파일을 다시 내려받아 Python `hashlib.sha256` 결과와 대조했다.

| 출력 basename | 원본과 범위 | 전체 파일 SHA-256 |
| --- | --- | --- |
| metric-reader.png | [MetricReader.java 24~42행](https://github.com/open-telemetry/opentelemetry-java/blob/b4b3a1b354425c3f1411173c0e48cb24a1cba224/sdk/metrics/src/main/java/io/opentelemetry/sdk/metrics/export/MetricReader.java#L24-L42) | `4dc9fc384ad642c74c486fef82f5fd36d6be6e9531cbdedbfdc3d731039f9c0d` |
| periodic-reader.png | [PeriodicMetricReader.java 86~94행](https://github.com/open-telemetry/opentelemetry-java/blob/b4b3a1b354425c3f1411173c0e48cb24a1cba224/sdk/metrics/src/main/java/io/opentelemetry/sdk/metrics/export/PeriodicMetricReader.java#L86-L94) | `47197ab58920a1293a605d0e7d72b8b9d2b577fb69ce0cd751ff5e7fa5c0d237` |

첫 캡처는 temporality/default-aggregation selector와 collection 등록, 두 번째 캡처는 exporter 정책 위임만 보여 준다. 상태 독립성, 전송 중복 제어, 누적 저장소 등은 이미지 밖의 별도 원문으로 확인했다. 원고에 캡션과 고정 permalink, alt, 텍스트 분석을 함께 둔다. PNG는 원문을 변경하지 않은 로컬 코드 뷰어 렌더링이며 GitHub UI의 화면 캡처가 아니다. 생성은 통합 담당자의 공통 도구가 `posts/CS/Observability/otel/images/05` 출력 디렉터리로 수행한다.

## 호출 경로와 본문 근거

아래 링크는 모두 위 고정 커밋이다.

| 원본 | 확인한 내용과 해석 경계 |
| --- | --- |
| [SdkLongCounter.java 42~74행](https://github.com/open-telemetry/opentelemetry-java/blob/b4b3a1b354425c3f1411173c0e48cb24a1cba224/sdk/metrics/src/main/java/io/opentelemetry/sdk/metrics/SdkLongCounter.java#L42-L74) | add에서 음수 검사 후 storage.recordLong 호출. 음수이면 경고 후 기록하지 않는다. 이 메서드가 exporter에 네트워크 요청을 하지는 않는다. |
| [InstrumentBuilder.java 67~71행](https://github.com/open-telemetry/opentelemetry-java/blob/b4b3a1b354425c3f1411173c0e48cb24a1cba224/sdk/metrics/src/main/java/io/opentelemetry/sdk/metrics/InstrumentBuilder.java#L67-L71) | descriptor 생성 → 저장소 등록 → 저장소를 가진 동기 instrument 생성. |
| [SdkMeter.java 281~312행](https://github.com/open-telemetry/opentelemetry-java/blob/b4b3a1b354425c3f1411173c0e48cb24a1cba224/sdk/metrics/src/main/java/io/opentelemetry/sdk/metrics/SdkMeter.java#L281-L312) | Reader별 View 선택과 storage 생성. Drop view 제외, 저장소 하나면 직접 반환하고 아니면 MultiWritableMetricStorage. |
| [SdkMeter.java 367~385행](https://github.com/open-telemetry/opentelemetry-java/blob/b4b3a1b354425c3f1411173c0e48cb24a1cba224/sdk/metrics/src/main/java/io/opentelemetry/sdk/metrics/SdkMeter.java#L367-L385) | 다수 저장소에 recordLong/recordDouble 반복 전달. Reader를 늘리면 기록 경로와 상태가 늘 수 있다는 해석의 근거. 정확한 성능 배수는 주장하지 않는다. |
| [LongSumAggregator.java 102~135행](https://github.com/open-telemetry/opentelemetry-java/blob/b4b3a1b354425c3f1411173c0e48cb24a1cba224/sdk/metrics/src/main/java/io/opentelemetry/sdk/metrics/internal/aggregator/LongSumAggregator.java#L102-L135) | LongAdder에 더하고 aggregate 시 sum 또는 sumThenReset. 개별 발생 순서·시각 목록이 아니라 합계를 유지한다. 모든 metric kind가 같은 집계라는 의미는 아니다. |
| [CumulativeSynchronousMetricStorage.java 96~149행](https://github.com/open-telemetry/opentelemetry-java/blob/b4b3a1b354425c3f1411173c0e48cb24a1cba224/sdk/metrics/src/main/java/io/opentelemetry/sdk/metrics/internal/state/CumulativeSynchronousMetricStorage.java#L96-L149) | attributes filter 적용 후 handle 조회, 최초 시계열 측정에 관계된 handle 생성 시각을 start로 사용하며 reset=false로 집계. Cardinality 초과는 overflow 조합으로 전환하므로 단순 전부 drop이라고 쓰지 않는다. |
| [CumulativeSynchronousMetricStorage.java 61~65행](https://github.com/open-telemetry/opentelemetry-java/blob/b4b3a1b354425c3f1411173c0e48cb24a1cba224/sdk/metrics/src/main/java/io/opentelemetry/sdk/metrics/internal/state/CumulativeSynchronousMetricStorage.java#L61-L65) | cumulative handles/map 수명에 대한 주석. 해당 구현에 한정하며 다른 언어·저장소 전체로 일반화하지 않는다. |
| [DeltaSynchronousMetricStorage.java 216~280행](https://github.com/open-telemetry/opentelemetry-java/blob/b4b3a1b354425c3f1411173c0e48cb24a1cba224/sdk/metrics/src/main/java/io/opentelemetry/sdk/metrics/internal/state/DeltaSynchronousMetricStorage.java#L216-L280) | collect 시 holder 전환, bound handle 유지와 memory mode별 map 재사용. 논리적 구간 reset이 모든 메모리 객체의 해제를 의미하지 않는다. 동시성 알고리즘 전체를 검증한 것으로 표현하지 않는다. |
| [DefaultSynchronousMetricStorage.java 65~85행](https://github.com/open-telemetry/opentelemetry-java/blob/b4b3a1b354425c3f1411173c0e48cb24a1cba224/sdk/metrics/src/main/java/io/opentelemetry/sdk/metrics/internal/state/DefaultSynchronousMetricStorage.java#L65-L85) | Reader의 instrument-kind별 temporality에 따라 cumulative/delta 저장소 선택. |
| [SdkMeterProviderBuilder.java 119~149행](https://github.com/open-telemetry/opentelemetry-java/blob/b4b3a1b354425c3f1411173c0e48cb24a1cba224/sdk/metrics/src/main/java/io/opentelemetry/sdk/metrics/SdkMeterProviderBuilder.java#L119-L149) | View의 filter/cardinality 설정 저장과 Reader 별도 등록. |
| [SdkMeterProvider.java 67~104행](https://github.com/open-telemetry/opentelemetry-java/blob/b4b3a1b354425c3f1411173c0e48cb24a1cba224/sdk/metrics/src/main/java/io/opentelemetry/sdk/metrics/SdkMeterProvider.java#L67-L104) | RegisteredReader/ViewRegistry 구성, Reader별 producer 연결 후 register. |
| [SdkMeterProvider.java 120~129행](https://github.com/open-telemetry/opentelemetry-java/blob/b4b3a1b354425c3f1411173c0e48cb24a1cba224/sdk/metrics/src/main/java/io/opentelemetry/sdk/metrics/SdkMeterProvider.java#L120-L129) | Reader가 없으면 no-op meter builder. SDK 객체를 만들면 무조건 recording을 유지한다는 주장을 피한다. |
| [PeriodicMetricReader.java 161~197행](https://github.com/open-telemetry/opentelemetry-java/blob/b4b3a1b354425c3f1411173c0e48cb24a1cba224/sdk/metrics/src/main/java/io/opentelemetry/sdk/metrics/export/PeriodicMetricReader.java#L161-L197) | register에서 start 호출, scheduleAtFixedRate로 주기 실행. 기본 interval 숫자는 원고에서 단정하지 않는다. |
| [PeriodicMetricReader.java 267~309행](https://github.com/open-telemetry/opentelemetry-java/blob/b4b3a1b354425c3f1411173c0e48cb24a1cba224/sdk/metrics/src/main/java/io/opentelemetry/sdk/metrics/export/PeriodicMetricReader.java#L267-L309) | exportAvailable로 중복 실행 억제, collect 후 export. 전송 진행 중이면 수집을 시작하지 않는 경우와 수집 후 exporter 실패를 구별한다. exporter 실패 로그와 Reader 실행 결과가 다르므로 flush 완료=backend 저장이라고 하지 않는다. |
| [SdkMeter.java 136~166행](https://github.com/open-telemetry/opentelemetry-java/blob/b4b3a1b354425c3f1411173c0e48cb24a1cba224/sdk/metrics/src/main/java/io/opentelemetry/sdk/metrics/SdkMeter.java#L136-L166) | reader-specific collection, 수집 lock, observable callback 호출 후 storage.collect. callback의 파괴적 외부 상태 읽기는 Reader 집계 독립성과 다른 문제다. |
| [PrometheusMetricReader.java 19~78행](https://github.com/open-telemetry/opentelemetry-java/blob/b4b3a1b354425c3f1411173c0e48cb24a1cba224/exporters/prometheus/src/main/java/io/opentelemetry/exporter/prometheus/PrometheusMetricReader.java#L19-L78) | MetricReader이면서 Prometheus MultiCollector, cumulative 선택, collectAllMetrics 결과 변환. OTel도 pull을 지원한다는 직접 근거. |

## 공식 문서

- [OTel Metrics SDK](https://opentelemetry.io/docs/specs/otel/metrics/sdk/#metricreader): 다수 Reader 수집 상태의 독립성. 최신 웹의 development 기능을 고정 Java 구현에 소급 적용하지 않는다.
- [OTel Metrics data model](https://opentelemetry.io/docs/specs/otel/metrics/data-model/#temporality): delta/cumulative, reset/gap, 변환과 시간 의미. 5·4·9 표와 장애 조건은 이 모델을 설명하기 위해 만든 계산 예시다.
- [Micrometer Registry](https://docs.micrometer.io/micrometer/reference/concepts/registry.html): MeterRegistry, SimpleMeterRegistry, CompositeMeterRegistry의 구분.
- [Micrometer Prometheus](https://docs.micrometer.io/micrometer/reference/implementations/prometheus.html#_configuring): scrape 문자열과 별도 HTTP 노출. Spring Boot Actuator 자동 구성과 일반 Java 앱을 구별한다.
- [Micrometer OTLP](https://docs.micrometer.io/micrometer/reference/implementations/otlp.html): 주기 HTTP 전송 구현. Micrometer=pull이라는 이분법의 반례.
- [Micrometer histogram/percentile](https://docs.micrometer.io/micrometer/reference/concepts/histogram-quantiles.html): client percentile의 비집계성, 서버의 Histogram 기반 추정과의 차이.
- [Prometheus data model](https://prometheus.io/docs/concepts/data_model/): 이름·label 조합의 시계열과 서버 저장 역할.
- [Prometheus Histogram/summary](https://prometheus.io/docs/practices/histograms/): classic/native Histogram과 미리 계산한 quantile의 차이. 특정 exporter/version 조합의 native 지원은 실행 확인하지 않았다.
- [Prometheus rate](https://prometheus.io/docs/prometheus/latest/querying/functions/#rate): Counter reset 처리와 범위에서의 초당 증가율 추정. 관측 전에 사라진 증가량까지 재구성하는 것으로 과장하지 않는다.

## 원고 검증과 한계

- HTML/SVG 명시적 중첩·XML·ID 검사 통과.
- template style block과 원고 style block의 문자열 동일성 검사 통과. 모바일 긴 식별자는 wrapper의 인라인 overflow-wrap으로 처리하며 정본 CSS는 수정하지 않았다.
- 일반 mask-check 통과. 회사·조직 자료를 쓰지 않았고 외부 조직 목록을 이용한 검사는 하지 않았다.
- 캡처 manifest JSON 파싱 및 두 raw 전체 파일 SHA-256 대조 통과.
- 본문 예제의 컴파일/실행, Java SDK 빌드, Prometheus scrape 서버 실행, exporter 장애 재현, 성능 측정은 하지 않았다.
- 8장의 재현 절차는 후속 실험 설계이지 실제 PASS 결과가 아니다.
- PNG 생성과 로컬 브라우저 렌더링 확인은 통합 담당자 단계다. 독립 퇴고·원자료 감사도 별도 담당자가 수행한다. 작성자 자체 점검을 독립 감사로 표시하지 않는다.
- 로컬 HTML 초안이며 발행·업로더 sync·커밋·푸시는 수행하지 않았다.
