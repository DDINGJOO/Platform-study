# OTel 아키텍처 시리즈 05–08: 공개 1차 자료 연구 노트

조사일: 2026-10-21. 용도: 긴 한국어 학습 글의 집필·검수 및 실제 소스 스크린샷 제작. 자료를 읽고 확인한 노트이며, 아래 관찰 예시는 실행한 실험 결과가 아니다. 비공개 advisory/fork는 접근하거나 인용하지 않았다. 의존성 채택 결정이 아니라 각 도구의 책임 경계를 비교하는 근거다.

## 고정 버전과 재현 규칙

| 저장소 | 소스 태그 | 전체 커밋 SHA | 릴리스 공개일 |
| --- | --- | --- | --- |
| open-telemetry/opentelemetry-java | v1.67.0 | `b4b3a1b354425c3f1411173c0e48cb24a1cba224` | 2026-10-09 |
| open-telemetry/opentelemetry-collector | v0.163.0 | `5177a6a85ca3783068077e25aec6cebbe1d50d1f` | 2026-10-14 |
| open-telemetry/opentelemetry-java-instrumentation | v2.32.0 | `1b8644f8eb11d90295b1c313391aa84edeeec6e2` | 2026-10-03 |

Collector 태그는 annotated tag이며 tag object `f810321641f1506c0ba8c5131af98ebcdaa6d2fd`를 위 commit으로 역참조했다. 스크린샷은 tag 이름이 아니라 commit permalink를 기준으로 한다.

- 아래 `full_file_sha256`은 해당 raw URL의 **파일 전체 바이트**에 대한 SHA-256이다. 발췌문 해시나 Git blob SHA가 아니다. raw 다운로드를 `shasum -a 256`으로 확인했다.
- 현재 웹 문서는 별도로 움직인다. 확인 당시 OTel specification 1.61.0, semantic conventions 1.44.0, OTLP 1.11.1, Micrometer 1.17.1, Micrometer Tracing 1.7.1, Alloy 문서 v1.21이었다. Java SDK 1.67.0과 사양 번호가 같아야 한다고 해석하지 않는다.
- 각 편 2개의 screenshot source range를 제공한다. 07의 두 범위는 같은 원본 파일에 있으므로 전체 파일 해시가 같다.
- 스크린샷 범위 밖의 코드를 숨겨 근거를 과장하지 않는다. 그림 하단에 저장소·태그·경로·줄 범위·permalink를 표기하고, 텍스트 분석에서도 같은 링크를 제공한다.

## 05. Metrics: 측정값은 어디서 집계되고, 누가 읽는가

### 중심 질문과 설명 흐름

"OTel도 Micrometer도 숫자를 보내는데 무엇이 다른가?"를 push/pull의 이분법으로 끝내지 않는다. API의 measurement, SDK의 aggregation/View, Reader의 collection/temporality, Exporter의 backend 전송을 분리해서 읽는다. 개별 측정값이 항상 모두 원형 그대로 전송되는 구조가 아니라는 점을 먼저 설명하면 비용과 손실의 관계를 연결하기 쉽다.

개념 흐름: Instrument 측정 → View로 stream/attributes/aggregation 구성 → SDK 집계 상태 → MetricReader가 수집 → MetricExporter 또는 scrape 응답. 이는 개념도이며 모든 구현 내부에 이 순서의 독립 객체가 반드시 하나씩 있다는 주장은 아니다.

### Screenshot 05-A: Reader의 책임은 전송 스케줄만이 아니다

- Repository: `open-telemetry/opentelemetry-java`; tag: `v1.67.0`
- Commit: `b4b3a1b354425c3f1411173c0e48cb24a1cba224`
- Path: `sdk/metrics/src/main/java/io/opentelemetry/sdk/metrics/export/MetricReader.java`
- Range: **L24–L42**
- Permalink: https://github.com/open-telemetry/opentelemetry-java/blob/b4b3a1b354425c3f1411173c0e48cb24a1cba224/sdk/metrics/src/main/java/io/opentelemetry/sdk/metrics/export/MetricReader.java#L24-L42
- Raw: https://raw.githubusercontent.com/open-telemetry/opentelemetry-java/b4b3a1b354425c3f1411173c0e48cb24a1cba224/sdk/metrics/src/main/java/io/opentelemetry/sdk/metrics/export/MetricReader.java
- full_file_sha256: `4dc9fc384ad642c74c486fef82f5fd36d6be6e9531cbdedbfdc3d731039f9c0d`
- 관찰: Reader가 `AggregationTemporalitySelector`, `DefaultAggregationSelector`를 상속한다. Provider가 `CollectionRegistration`을 제공하며 Reader 구현이 `collectAllMetrics()`를 호출한다.
- 캡션 후보: "MetricReader는 ‘몇 초마다 보낼까’뿐 아니라 어떤 집계·시간 구간의 데이터를 읽을지도 관여한다."

### Screenshot 05-B: exporter 요구가 Reader 설정으로 이어진다

- Repo/tag/commit: 위와 동일.
- Path: `sdk/metrics/src/main/java/io/opentelemetry/sdk/metrics/export/PeriodicMetricReader.java`
- Range: **L86–L94**
- Permalink: https://github.com/open-telemetry/opentelemetry-java/blob/b4b3a1b354425c3f1411173c0e48cb24a1cba224/sdk/metrics/src/main/java/io/opentelemetry/sdk/metrics/export/PeriodicMetricReader.java#L86-L94
- Raw: https://raw.githubusercontent.com/open-telemetry/opentelemetry-java/b4b3a1b354425c3f1411173c0e48cb24a1cba224/sdk/metrics/src/main/java/io/opentelemetry/sdk/metrics/export/PeriodicMetricReader.java
- full_file_sha256: `47197ab58920a1293a605d0e7d72b8b9d2b577fb69ce0cd751ff5e7fa5c0d237`
- 관찰: 이 Reader는 instrument type별 temporality와 default aggregation을 exporter에 위임한다. Reader/Exporter를 분리했다고 backend의 데이터 요구까지 사라지는 것은 아니다.
- 캡션 후보: "역할은 나뉘어 있지만, 내보낼 대상이 원하는 temporality와 aggregation은 수집 구성에 영향을 준다."

추가로 읽은 소스: 같은 commit의 `SdkMeterProviderBuilder.java` L119–L149는 View 등록 시 attribute filter/cardinality limit을 보관하고 Reader를 별도로 등록한다. `PeriodicMetricReader.java` L267–L291는 중복 export 실행을 제어하고 `collectAllMetrics()` 결과를 export한다. 2개 스크린샷 제한 때문에 본문 텍스트 근거로만 사용해도 된다.

### 공식 문서와 비교 근거

1. [OTel Metrics SDK](https://opentelemetry.io/docs/specs/otel/metrics/sdk/) — View, aggregation, MetricReader, temporality, reader별 상태를 규정한다. 특히 `#metricreader`, `#cardinality-limits`.
2. [Micrometer MeterRegistry](https://docs.micrometer.io/micrometer/reference/concepts/registry.html) — MeterRegistry가 meter를 만들고 보관하며 각 monitoring system 구현이 있다. CompositeMeterRegistry는 여러 registry로 fan-out할 수 있다. 따라서 "Micrometer는 한 vendor에만 묶이고 OTel만 추상화한다"는 비교는 틀리다.
3. [Micrometer Prometheus](https://docs.micrometer.io/micrometer/reference/implementations/prometheus.html) — `PrometheusMeterRegistry.scrape()`의 결과를 HTTP endpoint로 노출하고 Prometheus가 scrape하는 구성. Registry 객체 하나를 만들었다고 모든 앱에서 자동으로 HTTP 서버가 열리는 것은 아니다. Spring Boot Actuator 통합은 별도 맥락이다.

### 깊게 풀어 쓸 내용 / 오해 방지

- Delta는 직전 collection 이후 구간, cumulative는 동일한 시작점을 기준으로 누적하는 시간 해석이다. 예를 들어 동기 counter의 `(T0,T1], (T1,T2]`와 `(T0,T1], (T0,T2]`를 구별한다. 단순히 누적값을 두 번 더해서는 안 된다는 분석은 이 모델에서 도출되는 설명이다.
- 사양은 같은 Provider의 여러 Reader를 지원하며 한 Reader의 delta 수집이 다른 Reader 상태를 소비하지 않아야 한다고 규정한다. "Reader 두 개가 같은 하나의 delta 버킷을 빼앗는다"라고 쓰지 않는다.
- Reader는 pull 수집도 지원한다. MetricReader.java L65–L77도 Prometheus 같은 pull-based reader를 명시한다. **OTel=push, Micrometer=pull**로 표를 만들지 않는다. Micrometer도 대상별 push registry가 있고 OTel도 pull reader가 있다.
- Prometheus는 client instrumentation API만이 아니라 scrape, 시계열 저장, query 등을 갖는 시스템이다. OTel SDK와 Prometheus server를 단일 계층의 대체품으로 비교하지 않는다.
- 유연한 reader/view/exporter 경계의 대가는 설정·집계 의미·backend 변환을 이해해야 한다는 점으로 해석할 수 있다. 이는 소스에 쓰인 성능 보증이나 프로젝트의 공식 동기 진술이 아니라 아키텍처를 읽은 **해석**으로 표시한다.
- 실행 예시를 추가한다면 동일한 3회 측정 후 collection 두 번을 관찰해 delta/cumulative를 대조한다. 현재 노트에서는 실행하지 않았다.

## 06. Collector: 중간 서버 한 대를 추가하면 무엇이 달라지는가

### 중심 질문과 설명 흐름

"SDK가 직접 exporter로 보내도 되는데 Collector가 왜 필요한가?"에서 출발한다. 전송 홉을 추가하는 만큼 운영 지점도 생긴다. 대신 재시도·배치·필터·라우팅 등의 정책을 앱 밖에 모을 수 있다. Collector가 항상 필수이거나 장애를 없애 준다는 식으로 서술하지 않는다.

### Screenshot 06-A: 컴포넌트 정의와 pipeline 구성을 구별한다

- Repository: `open-telemetry/opentelemetry-collector`; tag: `v0.163.0`
- Commit: `5177a6a85ca3783068077e25aec6cebbe1d50d1f`
- Path: `service/pipelines/config.go`
- Range: **L50–L66**
- Permalink: https://github.com/open-telemetry/opentelemetry-collector/blob/5177a6a85ca3783068077e25aec6cebbe1d50d1f/service/pipelines/config.go#L50-L66
- Raw: https://raw.githubusercontent.com/open-telemetry/opentelemetry-collector/5177a6a85ca3783068077e25aec6cebbe1d50d1f/service/pipelines/config.go
- full_file_sha256: `4f8312d7aaedd86e47e8f4d60c68c152c4fc92a9bd92457abad9d61e9b897304`
- 관찰: PipelineConfig에 receivers/processors/exporters 참조 목록이 있으며 receiver와 exporter가 하나 이상인지 검사한다. processor는 이 검사에서 필수가 아니다.

### Screenshot 06-B: 설정의 나열이 실제 처리 그래프가 된다

- Repo/tag/commit: 위와 동일.
- Path: `service/internal/graph/graph.go`
- Range: **L267–L290**
- Permalink: https://github.com/open-telemetry/opentelemetry-collector/blob/5177a6a85ca3783068077e25aec6cebbe1d50d1f/service/internal/graph/graph.go#L267-L290
- Raw: https://raw.githubusercontent.com/open-telemetry/opentelemetry-collector/5177a6a85ca3783068077e25aec6cebbe1d50d1f/service/internal/graph/graph.go
- full_file_sha256: `a395b3a411e1d3636142ef0f3b72785c8449ede5ff9a0918b7991d7e29955f1e`
- 관찰: receiver → capabilities node → 설정 순서의 processor chain → fanout → exporters를 연결한다. exporter가 하나여도 fanout node는 만들어지며 그 경우 noop처럼 동작한다는 주석이 있다.
- 캡션 후보: "YAML의 processors 순서는 장식이 아니다. graph 생성 코드에서 실제 연결 순서가 된다."

### 공식 문서와 비교 근거

1. [Collector 개요: When to use a collector](https://opentelemetry.io/docs/collector/#when-to-use-a-collector) — 개발·소규모 환경에서는 backend 직접 전송도 유효하다. 일반적으로 Collector 사용을 권하며 retry, batching, encryption, sensitive-data filtering 등의 추가 처리를 분리할 수 있다고 설명한다.
2. [Collector configuration](https://opentelemetry.io/docs/collector/configuration/) — top-level에 receiver/processor/exporter를 정의하는 것만으로 활성화되지 않는다. `service.pipelines`가 사용을 연결한다. processor 적용 순서는 목록 순서다. 동일 processor 이름을 여러 pipeline에서 참조하면 pipeline별 별도 인스턴스가 생긴다.
3. [Prometheus Agent mode](https://prometheus.io/docs/prometheus/latest/prometheus_agent/) — Prometheus binary의 운영 모드. scrape API·semantics·configuration·discovery는 유지하면서 query, alerting, rule evaluation, 통상적인 local TSDB 기능을 끄고 remote write용 WAL을 쓴다. **디스크를 전혀 쓰지 않는다는 뜻이 아니다.** 로컬 query 없는 agent와 full Prometheus server의 저장·질의 역할을 구별한다.
4. [Grafana Alloy 소개](https://grafana.com/docs/alloy/latest/introduction/) — OTel Collector distribution이며 Prometheus pipeline과 Loki/Pyroscope 지원 등을 함께 제공한다.
5. [How Grafana Alloy works](https://grafana.com/docs/alloy/latest/introduction/how-alloy-works/) — 모듈식 component를 연결하는 pipeline 및 표현식 기반 설정. 저장 backend로 전달하며 pipeline 상태를 보는 debug UI도 있다. **"Alloy에는 UI가 없다"는 문장은 틀리다.** telemetry 검색·장기 저장 backend와 이 UI의 목적이 다르다.
6. [Collector resiliency](https://opentelemetry.io/docs/collector/resiliency/) — queue/retry/persistent storage를 켜야 하는 구성·용량·장애 경계를 다루는 근거. Collector가 있다고 무한 buffering, 무손실, 정확히 한 번을 보장하지 않는다.

### 깊게 풀어 쓸 내용 / 오해 방지

- SDK 직접 전송 / OTel Collector / Prometheus Agent / Alloy는 같은 이름만 다른 binary가 아니다. 비교 축을 **무엇을 수집하는가, 어디서 정책을 적용하는가, 어떤 protocol로 내보내는가, 저장·질의는 누가 맡는가**로 잡는다.
- 직접 전송은 프로세스와 네트워크 구성을 줄이는 선택으로 설명할 수 있다. Collector는 정책의 중앙화/분리 가능성과 별도 배포·관찰·확장·장애 지점을 함께 만든다는 해석이 가능하다. 보편적인 성능 우열은 측정 없이 주장하지 않는다.
- receiver는 push를 받는 경우도, scrape처럼 pull하는 경우도 있다. receiver=항상서버로 정의하지 않는다.
- pipeline 순서가 의미를 바꾼다. 예컨대 필터/변환이 배치 앞인지 뒤인지가 처리 대상과 정책 적용 시점에 영향을 줄 수 있다. 특정 processor 순서를 모든 구성의 유일한 정답이라고 일반화하지 않는다.
- component id의 `type/name`과 service의 참조를 구별한다. 아무 type을 YAML에 쓰면 plugin이 자동 다운로드된다는 설명을 하지 않는다. distribution에 포함된 factory·지원 신호·안정성을 확인해야 한다.
- Alloy 문서 v1.21에는 native OTel engine/YAML 통합도 보인다. 따라서 "Alloy는 언제나 오직 자체 문법만 지원한다"는 오래된 단정은 피한다. 이 글은 Collector v0.163.0의 graph source를 읽고, Alloy는 현재 공식 문서의 역할만 비교한다.
- Prometheus Agent 페이지의 임시 WAL buffer 설명은 버전별 구현·설정 영향을 받을 수 있으므로 글의 핵심에 고정된 최대 시간 보증으로 사용하지 않는다.

## 07. 자동 계측: 코드를 바꾸지 않았는데 누가 span을 시작했나

### 중심 질문과 설명 흐름

Java agent의 "자동"은 무엇을 알고 있기 때문에 가능한지 matcher와 advice를 읽는다. 이어서 자동 라이브러리 경계, 직접 쓴 business span, Observation handler, eBPF의 관측 지점을 구분한다. 네 방식 중 하나가 나머지를 항상 대체한다는 구도로 만들지 않는다.

### Screenshot 07-A: 관측할 타입과 메서드를 명시적으로 고른다

- Repository: `open-telemetry/opentelemetry-java-instrumentation`; tag: `v2.32.0`
- Commit: `1b8644f8eb11d90295b1c313391aa84edeeec6e2`
- Path: `instrumentation/java-http-client/javaagent/src/main/java/io/opentelemetry/javaagent/instrumentation/javahttpclient/HttpClientInstrumentation.java`
- Range: **L42–L64**
- Permalink: https://github.com/open-telemetry/opentelemetry-java-instrumentation/blob/1b8644f8eb11d90295b1c313391aa84edeeec6e2/instrumentation/java-http-client/javaagent/src/main/java/io/opentelemetry/javaagent/instrumentation/javahttpclient/HttpClientInstrumentation.java#L42-L64
- Raw: https://raw.githubusercontent.com/open-telemetry/opentelemetry-java-instrumentation/1b8644f8eb11d90295b1c313391aa84edeeec6e2/instrumentation/java-http-client/javaagent/src/main/java/io/opentelemetry/javaagent/instrumentation/javahttpclient/HttpClientInstrumentation.java
- full_file_sha256: `1c249809cb978054d106186d84a0f8f8e739d2edab9ef8183b2fbe4bb9600521`
- 관찰: `java.net.http.HttpClient` 하위 타입을 matcher로 선택하고 public `send`/`sendAsync`에 advice를 연결한다. 특정 facade 타입을 제외한다. 자동 계측은 범용적인 모든 의미 추론이 아니라 알려진 라이브러리의 실행 경계에 맞춘 코드다.

### Screenshot 07-B: 자동 계측에도 context와 수명 관리가 있다

- Repository: `open-telemetry/opentelemetry-java-instrumentation`; tag: `v2.32.0`
- Commit: `1b8644f8eb11d90295b1c313391aa84edeeec6e2`
- Path: `instrumentation/java-http-client/javaagent/src/main/java/io/opentelemetry/javaagent/instrumentation/javahttpclient/HttpClientInstrumentation.java`
- Range: **L80–L94**
- Permalink: https://github.com/open-telemetry/opentelemetry-java-instrumentation/blob/1b8644f8eb11d90295b1c313391aa84edeeec6e2/instrumentation/java-http-client/javaagent/src/main/java/io/opentelemetry/javaagent/instrumentation/javahttpclient/HttpClientInstrumentation.java#L80-L94
- Raw: https://raw.githubusercontent.com/open-telemetry/opentelemetry-java-instrumentation/1b8644f8eb11d90295b1c313391aa84edeeec6e2/instrumentation/java-http-client/javaagent/src/main/java/io/opentelemetry/javaagent/instrumentation/javahttpclient/HttpClientInstrumentation.java
- full_file_sha256: `1c249809cb978054d106186d84a0f8f8e739d2edab9ef8183b2fbe4bb9600521`
- 관찰: parent `Context.current()`를 얻고 `shouldStart`를 검사한 뒤 `instrumenter.start`, `makeCurrent`를 수행한다. 종료에서는 scope를 닫고 instrumenter를 끝낸다. 02편의 context/scope 논의를 agent 내부 동작과 연결할 수 있다.
- 한계: 이 범위는 synchronous advice 안의 lifecycle이다. **sendAsync도 메서드 반환 즉시 span이 끝난다**고 설명하지 않는다. 같은 파일 L138–L167은 별도의 async advice 및 future completion 처리를 한다.

### 공식 문서와 비교 근거

1. [OTel Java Agent](https://opentelemetry.io/docs/zero-code/java/agent/) — bytecode를 동적으로 주입하여 지원 라이브러리·framework의 inbound/outbound HTTP·DB 등 경계 telemetry를 캡처한다. 페이지 자체가 manual instrumentation과 API 확장을 연결한다.
2. [Extending the Java agent with the API](https://opentelemetry.io/docs/zero-code/java/agent/api/) — agent와 OTel API를 조합해 custom spans/metrics를 추가하는 근거. 이 URL은 agent 개요에서 공식 링크 대상이며 집필 시 최종 내용을 다시 열어 예제를 선택하면 된다.
3. [Micrometer Observation introduction](https://docs.micrometer.io/micrometer/reference/observation/introduction.html) — ObservationRegistry에 handler를 등록해 start/stop/error/event/scope lifecycle에 반응한다. timers/spans/log 동작을 instrumented code와 분리할 수 있다.
4. [Micrometer Tracing](https://docs.micrometer.io/tracing/reference/) — `micrometer-tracing-bridge-brave` 또는 `micrometer-tracing-bridge-otel`과 exporter/reporter를 구성한다고 명시한다. Observation/Micrometer와 OTel은 공존할 수 있는 다른 계층이다.
5. [OpenTelemetry eBPF Instrumentation(OBI)](https://opentelemetry.io/docs/zero-code/obi/) — limitations 절은 custom spans, application attributes, business events 및 관측 지점에서 알 수 없는 in-process telemetry에 언어별/수동 계측이 필요할 수 있다고 명시한다. OBI를 모든 eBPF 도구의 공통 기능표로 일반화하지 않는다.

### 깊게 풀어 쓸 내용 / 오해 방지

- 자동 agent는 어떤 라이브러리를 어떤 버전·메서드 모양에서 지원하는지가 중요하다. 지원표와 runtime 호환성을 무시하고 "JAR 하나면 모든 호출·모든 의미가 보인다"고 쓰지 않는다.
- manual API는 결제 승인/재고 예약 같은 업무 경계를 개발자가 명시할 수 있다. 대신 어디서 start/end하고 어떤 속성을 넣을지 소유해야 한다. 이것은 알려진 source 경계와 사용자 정의 의미의 차이를 설명하는 예시이지, 해당 example 서비스를 실제 계측했다는 주장이 아니다.
- Observation의 mutable `Observation.Context`와 OTel의 immutable `Context`는 이름만 같고 책임·변경 모델이 다르다. 같은 객체처럼 대입하여 설명하지 않는다.
- eBPF는 kernel만 관찰할 수 있다고 단정하지 않는다. 도구별 user-space probe/언어 지원도 있다. 정확한 설명은 **선택한 probe와 runtime/protocol 지원이 관찰 가능한 정보를 제한한다**는 것이다. TLS, runtime, propagation 지원 여부도 해당 제품·버전의 문서로 확인해야 한다.
- OBI 현재 문서는 Linux/architecture/kernel/BTF 및 권한 요구사항을 명시한다. "코드 변경 없음"이 "권한·배포 변경·오버헤드 없음"이라는 뜻은 아니다. 보편적인 숫자 성능 비교는 하지 않는다.
- agent+manual 또는 agent+Observation 조합을 보여줄 때 중복 계측/이중 span 가능성을 점검한다. `shouldStart`가 존재한다는 것만으로 임의 조합의 모든 중복이 자동 제거된다고 주장하지 않는다.

## 08. 데이터의 이름과 비용: OTLP가 통한다고 같은 뜻일까

### 중심 질문과 설명 흐름

OTLP를 지원하는 두 시스템이 서로 데이터를 주고받을 수 있다는 사실과, 속성의 의미·단위·자원 식별·카디널리티 정책이 맞는다는 사실은 별개다. protocol, semantic conventions, resource/scope, signal별 비용, privacy를 차례로 분리한다.

### Screenshot 08-A: SpanLimits는 한 span의 크기 예산이다

- Repository: `open-telemetry/opentelemetry-java`; tag: `v1.67.0`
- Commit: `b4b3a1b354425c3f1411173c0e48cb24a1cba224`
- Path: `sdk/trace/src/main/java/io/opentelemetry/sdk/trace/SpanLimitsBuilder.java`
- Range: **L14–L25**
- Permalink: https://github.com/open-telemetry/opentelemetry-java/blob/b4b3a1b354425c3f1411173c0e48cb24a1cba224/sdk/trace/src/main/java/io/opentelemetry/sdk/trace/SpanLimitsBuilder.java#L14-L25
- Raw: https://raw.githubusercontent.com/open-telemetry/opentelemetry-java/b4b3a1b354425c3f1411173c0e48cb24a1cba224/sdk/trace/src/main/java/io/opentelemetry/sdk/trace/SpanLimitsBuilder.java
- full_file_sha256: `d84fe43f5fe2839d7a9eac39a54049d561c33d14590ce0f3b8bccbff98dccce4`
- 관찰: attributes/events/links 및 event/link당 attribute 수에 각각 기본 한도가 있다. L29–L41 setter Javadoc도 attributes **per Span**임을 명시한다. 이 제한은 여러 span에서 생기는 서로 다른 user.id 값의 개수를 제한하지 않는다.
- 주의: L25는 attribute-value-length 기본값을 상수로 참조할 뿐이다. 이 발췌문만 보고 문자열 길이 기본값까지 임의 숫자로 적지 않는다.

### Screenshot 08-B: Metric cardinality는 attribute 조합별 상태의 수다

- Repo/tag/commit: 위와 동일.
- Path: `sdk/metrics/src/main/java/io/opentelemetry/sdk/metrics/internal/state/CumulativeSynchronousMetricStorage.java`
- Range: **L96–L120**
- Permalink: https://github.com/open-telemetry/opentelemetry-java/blob/b4b3a1b354425c3f1411173c0e48cb24a1cba224/sdk/metrics/src/main/java/io/opentelemetry/sdk/metrics/internal/state/CumulativeSynchronousMetricStorage.java#L96-L120
- Raw: https://raw.githubusercontent.com/open-telemetry/opentelemetry-java/b4b3a1b354425c3f1411173c0e48cb24a1cba224/sdk/metrics/src/main/java/io/opentelemetry/sdk/metrics/internal/state/CumulativeSynchronousMetricStorage.java
- full_file_sha256: `5a0a5381f6521f8569f5376a123a5a23dcfa37722b1f8f2fb6c4a12c250d7806`
- 관찰: attributesFilter 적용 후 attribute set으로 aggregator handle을 찾는다. 새 조합을 보관할 여유가 없으면 overflow attribute set으로 전환한다. 개별 차원을 잃고 합쳐지는 것이지 단순히 모든 초과 측정값을 버리는 코드가 아니다.
- 한계: 이 screenshot은 **cumulative synchronous metric storage** 구현이다. async/delta에서도 내부 코드가 완전히 같다고 쓰지 않는다. 사양은 그 경우들을 별도로 규정한다. 같은 버전의 `DefaultSynchronousMetricStorage.java` L42–L62는 overflow용 한 slot을 예약함을 명시하므로 "설정 한도와 일반 조합의 정확한 개수가 언제나 1:1" 같은 단정도 피한다.

### 공식 문서와 비교 근거

1. [Semantic conventions 개념](https://opentelemetry.io/docs/concepts/semantic-conventions/) — operations/data의 공통 명명·의미 규약. trace/metric/log/profile/resource에 적용된다.
2. [OTLP 1.11.1](https://opentelemetry.io/docs/specs/otlp/) — encoding, transport, delivery mechanism. gRPC/HTTP와 Protobuf payload schema를 규정한다. 한 hop의 request acknowledgement가 전체 multi-hop pipeline의 end-to-end 무손실 보장은 아니라고 명시한다.
3. [Resources](https://opentelemetry.io/docs/concepts/resources/) — telemetry를 생산하는 entity의 속성. process, container, pod, service.name 등을 설명한다. 거래마다 바뀌는 transaction/user 값을 resource에 넣는 개념이 아니다.
4. [Instrumentation scope](https://opentelemetry.io/docs/concepts/instrumentation-scope/) — telemetry를 만드는 논리적 software 단위. name과 optional version/schema_url/attributes. resource의 서비스 정체성과 scope의 계측 library/module 출처는 다르다.
5. [Metrics SDK cardinality limits](https://opentelemetry.io/docs/specs/otel/metrics/sdk/#cardinality-limits) — 서로 다른 attribute 조합의 수를 다룬다. View attribute filtering 뒤에 한도를 적용하는 모델과 overflow aggregation을 규정한다. SDK default cardinality limit은 사양에서 SHOULD 2000이므로 모든 언어·버전·구성을 무조건 2000으로 단정하지 않는다.
6. [Micrometer Observation components](https://docs.micrometer.io/micrometer/reference/observation/components.html#_defaultmeterobservationhandler) — DefaultMeterObservationHandler가 low-cardinality key values만 meter tags에 사용하고 high-cardinality 값은 제외함을 명시한다. low/high는 데이터 타입 차이가 아니라 계측 API에서 의도·대상 신호를 구분하는 정책이다.
7. [Prometheus data model](https://prometheus.io/docs/concepts/data_model/) — metric name+label set이 time series를 식별하며 label 값을 바꾸거나 label을 추가/제거하면 새 series가 된다.
8. [Handling sensitive data](https://opentelemetry.io/docs/security/handling-sensitive-data/) — 필요한 데이터만 수집하는 minimization, instrumentation 출력 검토, Collector redaction/filter/transform 등을 다룬다. 민감한 의미를 OTel이 스스로 보편적으로 판별할 수 없으며 작은 입력 공간의 hash가 익명성을 보장하지 않음을 경고한다.

### 깊게 풀어 쓸 내용 / 오해 방지

- `http.request.method` 같은 이름이 일치하는 것, 단위/값 의미가 일치하는 것, OTLP payload가 파싱되는 것은 서로 다른 호환성 층위다. 기존 대시보드·query·backend indexing 정책까지 자동 이식된다는 보장은 아니다.
- SpanLimit의 attribute count/length와 metric cardinality를 별도 예제로 대조한다. 한 span에 key 두 개만 있어도 한 metric에 user ID를 계속 새 값으로 넣으면 시계열 조합이 늘 수 있다. 반대로 한 span의 많은 속성은 그 span 크기의 문제다.
- `method × route × status` 조합 수를 곱하는 예시는 **가능한 조합의 상한 모델**이다. 실제 값의 상관관계, 미관측 조합, resource/scope 분할 및 backend 변환을 무시한 실측 수치로 제시하지 않는다.
- low-cardinality라고 자동으로 비민감하지 않으며 high-cardinality라고 항상 PII도 아니다. `has_hiv=true/false`는 값이 둘이어도 민감할 수 있는 개념 예시다. 개인정보 법률 판단이 아니라 cardinality와 sensitivity가 다른 축이라는 설명으로 한정한다.
- span 값 길이를 자르는 설정은 secret을 감추는 보안 정책이 아니다. metric View attribute filtering 역시 전체 telemetry pipeline의 PII 제거 보장으로 부풀리지 않는다. exemplar/다른 signal/다른 exporter/로그 등 별도 경로를 검토해야 한다.
- "high-cardinality는 trace에 넣으면 공짜"라고 하지 않는다. backend indexing·storage·retention 비용 및 민감정보 문제는 여전히 존재한다. 다만 metrics처럼 attribute 조합마다 집계 상태/series가 늘어나는 비용 모델과 구별한다.
- semconv의 각 영역·속성 안정성과 마이그레이션은 별도 확인 대상이다. 현재 문서 이름을 과거 Java SDK/agent 버전의 모든 기본 출력에 소급하지 않는다.

## 작성자에게 전달할 경계

- 공식 문서의 규범, 특정 릴리스 구현의 관찰, 아키텍처 trade-off에 대한 필자의 해석을 문장으로 구별한다.
- 비교의 결론은 특정 제품의 일방적 승리가 아니라 앱 내부 계측·집계·수집 파이프라인·저장/질의가 어디에 놓였는지의 이해여야 한다.
- 이 노트에는 측정한 latency/CPU/메모리 수치나 실행한 local demo가 없다. 새 실험을 한다면 입력·설정·기대값·실제 출력·한계를 별도 기록한 뒤에만 결과로 쓴다.
- 코드 스크린샷은 실제 pinned source를 렌더링한다. AI 이미지 생성으로 코드를 재현하지 않는다.
