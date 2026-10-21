# OTel 심화판 01–08 독립 사실관계 퇴고

- 검토일: 2026-10-21
- 역할: 작성자·최종 감사자와 분리된 사실관계 퇴고자
- 대상: `posts/CS/Observability/otel/`의 01–08 HTML 본문 전체, 각 편의 source manifest, 관련 공개 upstream 원문과 공식 문서, 저장된 실험 코드·출력·검증 기록
- 결과: **수정 필수 사실 오류 0건**. CRITICAL 0 / HIGH 0 / MEDIUM 0 / LOW 0.
- 판단 범위: API·기본값·코드 경로·버전 구분·수치·실행 결과의 일치. 문체 취향이나 원고 분량을 오류로 세지 않았다.

## 독립 확인 방식

기존 개요판의 검토 결과를 재사용하지 않고 심화판 8편의 본문을 모두 읽었다. 위험도가 큰 주장부터 공개 고정 커밋의 원문을 직접 열어 대조했다. 비교 제품은 공식 문서의 관련 절을 확인했다. 전수 URL 크롤링은 하지 않았다.

소스 기준은 Java v1.67.0 `b4b3a1b354425c3f1411173c0e48cb24a1cba224`, Collector v0.163.0 `5177a6a85ca3783068077e25aec6cebbe1d50d1f`, Java instrumentation v2.32.0 `1b8644f8eb11d90295b1c313391aa84edeeec6e2`다. 8개 `source-manifest.json`의 저장소·커밋·파일·발췌 범위를 읽어 본문의 참조 대상과 대조했다. 이미지 생성·시각 감사와 별도로, 이 검토에서는 코드가 설명하는 실제 동작을 확인했다.

## 편별 대조 결과

### 01. API와 SDK

`01_1편 - API와 SDK는 왜 나뉘어 있을까.html` 전체를 읽었다. SDK 객체 생성, recording 상태, exporter 전달, 원격 저장을 분리한 설명은 맞다. 특히 processor가 없으면 noop tracer를 반환하는 이 버전의 예외를 빠뜨리지 않았다. 부모가 있는 noop span의 유효한 SpanContext 보존을 recording과 구분한 설명도 API-only 실험 코드 및 저장 출력과 일치한다.

직접 확인한 핵심 근거: [SdkTracerProvider의 no-processor 분기](https://github.com/open-telemetry/opentelemetry-java/blob/b4b3a1b354425c3f1411173c0e48cb24a1cba224/sdk/trace/src/main/java/io/opentelemetry/sdk/trace/SdkTracerProvider.java#L98-L107), `otel-01-api-sdk/NoopProbe.java`, `otel-01-api-sdk/validation.json`, `otel-runtime-probes/RuntimeProbes.java`의 `apiSdk()`.

판정: 지적 0건, 핵심 경로 대조 확신도 높음.

### 02. Context와 스레드

`02_2편 - 스레드가 바뀌면 컨텍스트는 어떻게 이어질까.html` 전체를 읽었다. 기본 ThreadLocal 저장소와 Scope의 조건부 복원, 명시적으로 캡처한 Context와 제출 시점의 캡처, 로컬 attach와 원격 inject/extract를 구분한 설명에서 사실 오류를 찾지 못했다. 잘못된 순서의 close가 항상 초기화하는 동작이 아니라는 설명은 실제 `closed` 플래그의 위치까지 원문과 맞는다. Reactor 자동 모드의 새 구독 적용 및 등록한 ThreadLocalAccessor 조건도 공식 문서와 일치한다.

직접 확인한 핵심 근거: [ThreadLocalContextStorage](https://github.com/open-telemetry/opentelemetry-java/blob/b4b3a1b354425c3f1411173c0e48cb24a1cba224/context/src/main/java/io/opentelemetry/context/ThreadLocalContextStorage.java#L17-L58), [Reactor Context-Propagation 지원](https://projectreactor.io/docs/core/release/reference/advanced-contextPropagation.html), 런타임 probe의 단일 worker·예외·복원 검사.

판정: 지적 0건, 핵심 경로 대조 확신도 높음.

### 03. 배치 큐와 전송

`03_3편 - 전송이 밀리면 스팬은 어디서 사라질까.html` 전체를 읽었다. BSP가 큐의 기존 항목을 밀어내는 대신 새 항목의 `offer` 실패를 폐기로 기록하는 설명, worker의 drain·배치·export 순서, timeout join과 취소의 차이, forceFlush 성공과 exporter/backend 성공을 구분한 설명은 고정 원문과 일치한다. export 인자가 복사본이 아니라 읽기 전용 view이며 이후 batch가 clear된다는 설명도 원문과 맞는다.

직접 확인한 핵심 근거: [BSP queue/worker/flush](https://github.com/open-telemetry/opentelemetry-java/blob/b4b3a1b354425c3f1411173c0e48cb24a1cba224/sdk/trace/src/main/java/io/opentelemetry/sdk/trace/export/BatchSpanProcessor.java#L228-L370). 실험의 queue=2, batch=1, 첫 export pending, 추가 종료 5개, 최종 전달 3개·미전달 3개는 `GateExporter`, latch, 이름 검증 및 저장 stdout/stderr와 일치한다. 일반적인 유실률이나 처리량 측정으로 확대하지 않았다.

판정: 지적 0건, 핵심 경로·저장 실험 기록 대조 확신도 높음.

### 04. 샘플링

`04_4편 - 샘플링하면 무엇이 남고 무엇이 빠질까.html` 전체를 읽었다. Java 구현의 하위 64비트·절댓값·임계값 비교, ParentBased의 5개 위임 분기와 기본 AlwaysOn/Off, RECORD_ONLY와 processor의 unsampled 필터를 분리한 설명은 원문과 일치한다. 10% 독립 선택에서 실패 n건을 모두 놓칠 확률 `(1-0.1)^n` 및 예시 반올림 값도 맞다.

직접 확인한 핵심 근거: [TraceIdRatioBasedSampler](https://github.com/open-telemetry/opentelemetry-java/blob/b4b3a1b354425c3f1411173c0e48cb24a1cba224/sdk/trace/src/main/java/io/opentelemetry/sdk/trace/samplers/TraceIdRatioBasedSampler.java), [ParentBasedSampler](https://github.com/open-telemetry/opentelemetry-java/blob/b4b3a1b354425c3f1411173c0e48cb24a1cba224/sdk/trace/src/main/java/io/opentelemetry/sdk/trace/samplers/ParentBasedSampler.java). 저장 실험은 remote 부모와 명시적 sampler 비교이며, local 부모 모든 분기를 실행했다고 쓰지 않았다.

현행 사양의 TraceIdRatioBased deprecated, 최소 2027-01-01까지의 동작 보존 요구, ProbabilitySampler의 Development 상태·56비트 규칙을 Java 고정 구현과 구분했다. 날짜를 일괄 삭제 일정으로 해석하지 않은 것도 정확하다. [현행 Tracing SDK 사양](https://opentelemetry.io/docs/specs/otel/trace/sdk/#traceidratiobased)과 직접 대조했다. Jaeger adaptive를 remote head로 설명하고 tail과 구분한 내용은 [Jaeger 2.22 공식 문서](https://www.jaegertracing.io/docs/2.22/architecture/sampling/#adaptive-sampling)와 일치한다.

판정: 지적 0건, 직접 대조한 구현·현행 사양 확신도 높음.

### 05. 메트릭 집계와 Reader

`05_5편 - 메트릭은 어디서 집계되고 누가 가져갈까.html` 전체를 읽었다. Reader의 temporality/default aggregation 선택 역할, 누적 저장소와 delta 저장소 분기, Reader별 상태와 callback 실행의 구분, PeriodicMetricReader의 중복 export 방지 gate를 설명한 내용은 원문과 일치한다. 진행 중 export 때문에 수집 자체를 건너뛰는 경로와 수집 뒤 export 실패를 구분했다. 누적 시작 시각을 JVM 시작 시각으로 단정하지 않은 점도 구현과 맞다.

직접 확인한 핵심 근거: [DefaultSynchronousMetricStorage](https://github.com/open-telemetry/opentelemetry-java/blob/b4b3a1b354425c3f1411173c0e48cb24a1cba224/sdk/metrics/src/main/java/io/opentelemetry/sdk/metrics/internal/state/DefaultSynchronousMetricStorage.java), [CumulativeSynchronousMetricStorage](https://github.com/open-telemetry/opentelemetry-java/blob/b4b3a1b354425c3f1411173c0e48cb24a1cba224/sdk/metrics/src/main/java/io/opentelemetry/sdk/metrics/internal/state/CumulativeSynchronousMetricStorage.java), [PeriodicMetricReader](https://github.com/open-telemetry/opentelemetry-java/blob/b4b3a1b354425c3f1411173c0e48cb24a1cba224/sdk/metrics/src/main/java/io/opentelemetry/sdk/metrics/export/PeriodicMetricReader.java).

판정: 지적 0건, 직접 대조한 저장·수집 경로 확신도 높음. 새로운 메트릭 실험을 실행한 것으로 서술하지 않았다.

### 06. Collector

`06_6편 - Collector를 두면 무엇을 중앙에서 바꿀 수 있을까.html` 전체를 읽었다. 설정 정의와 파이프라인 활성화의 차이, processor 순서, pipeline별 processor 인스턴스, downstream 먼저 시작/upstream 먼저 종료 순서는 graph 원문과 맞다. YAML의 `otlp_grpc/backend`는 이 고정 버전의 exporter 문서가 사용하는 `otlp_grpc` 종류와 일치한다. 과거 버전의 `otlp` 이름만 기억해 오류로 판정하지 않았다.

직접 확인한 핵심 근거: [graph 생성·생명주기](https://github.com/open-telemetry/opentelemetry-collector/blob/5177a6a85ca3783068077e25aec6cebbe1d50d1f/service/internal/graph/graph.go), [OTLP gRPC exporter 설정](https://github.com/open-telemetry/opentelemetry-collector/blob/5177a6a85ca3783068077e25aec6cebbe1d50d1f/exporter/otlpexporter/README.md), [exporterhelper queue 설정](https://github.com/open-telemetry/opentelemetry-collector/blob/5177a6a85ca3783068077e25aec6cebbe1d50d1f/exporter/exporterhelper/README.md#sending-queue), [QueueBatch.Send/Shutdown](https://github.com/open-telemetry/opentelemetry-collector/blob/5177a6a85ca3783068077e25aec6cebbe1d50d1f/exporter/exporterhelper/internal/queuebatch/queue_batch.go#L93-L108). `wait_for_result=false` 기본값과 Offer 경계, 종료 때 retry가 멈춘 상태라는 설명도 맞다.

[Prometheus Agent 공식 문서](https://prometheus.io/docs/prometheus/latest/prometheus_agent/)의 전송용 WAL 및 질의·규칙 평가 제외, [Alloy 소개](https://grafana.com/docs/alloy/latest/introduction/)의 Collector 배포판·Prometheus/Loki/Pyroscope 지원을 직접 대조했다. 이 제품 비교를 런타임 성능이나 저장 내구성 검증으로 확대하지 않았다.

판정: 지적 0건, 직접 대조한 설정·그래프·큐 경로 확신도 높음. YAML의 실제 배포 성공까지 검증한 것은 아니다.

### 07. 자동 계측

`07_7편 - 자동 계측은 애플리케이션을 어디까지 알 수 있을까.html` 전체를 읽었다. 고정 Java agent의 타입·메서드 matcher, 동기 Scope 복원 후 end, 비동기 반환 시 Scope 복원과 Future 완료 시 end, `CompletableFutureWrapper`에 HTTP child가 아닌 parent Context를 넘기는 설명은 관련 세 파일의 실제 호출과 일치한다. 원래 Future에 취소를 전달하는 override도 존재한다.

직접 확인한 핵심 근거: [HttpClientInstrumentation](https://github.com/open-telemetry/opentelemetry-java-instrumentation/blob/1b8644f8eb11d90295b1c313391aa84edeeec6e2/instrumentation/java-http-client/javaagent/src/main/java/io/opentelemetry/javaagent/instrumentation/javahttpclient/HttpClientInstrumentation.java), [CompletableFutureWrapper](https://github.com/open-telemetry/opentelemetry-java-instrumentation/blob/1b8644f8eb11d90295b1c313391aa84edeeec6e2/instrumentation/java-http-client/library/src/main/java/io/opentelemetry/instrumentation/javahttpclient/internal/CompletableFutureWrapper.java), [ResponseConsumer](https://github.com/open-telemetry/opentelemetry-java-instrumentation/blob/1b8644f8eb11d90295b1c313391aa84edeeec6e2/instrumentation/java-http-client/library/src/main/java/io/opentelemetry/instrumentation/javahttpclient/internal/ResponseConsumer.java).

OBI의 Linux amd64/arm64, kernel/BTF·권한 조건과 애플리케이션 의미의 관찰 한계는 [OBI 공식 소개](https://opentelemetry.io/docs/zero-code/obi/)의 Requirements/Limitations와 대조했다. agent·OBI·Observation bridge를 실제 실행했다고 쓰지 않았다.

판정: 지적 0건, 직접 대조한 Java HTTP 계측 경로 확신도 높음.

### 08. 의미 규약과 카디널리티

`08_8편 - 같은 요청을 같은 이름으로 기록하려면 무엇이 필요할까.html` 전체를 읽었다. [공식 HTTP migration 문서](https://opentelemetry.io/docs/specs/semconv/non-normative/http-migration/)의 attribute 이름, duration metric 이름·ms→s 변경, 초기 stable 전환의 opt-in 범위를 대조했다. `http`·`http/dup`를 모든 버전·신호에 공통인 스위치로 일반화하지 않았다.

span당 attribute 수, metric 조합 수, 민감정보를 별도 축으로 구분한 설명은 맞다. `40×4×3×5=2400`은 가능한 조합 계산이며 실제 backend series 수를 보장하는 것으로 쓰지 않았다. View 필터 적용 후 map 조회, 기존 handle 재사용, overflow용 1개 슬롯 예약 및 측정값의 합산, exemplar에는 원래 attributes가 전달될 수 있다는 설명은 [CumulativeSynchronousMetricStorage](https://github.com/open-telemetry/opentelemetry-java/blob/b4b3a1b354425c3f1411173c0e48cb24a1cba224/sdk/metrics/src/main/java/io/opentelemetry/sdk/metrics/internal/state/CumulativeSynchronousMetricStorage.java)와 [DefaultSynchronousMetricStorage](https://github.com/open-telemetry/opentelemetry-java/blob/b4b3a1b354425c3f1411173c0e48cb24a1cba224/sdk/metrics/src/main/java/io/opentelemetry/sdk/metrics/internal/state/DefaultSynchronousMetricStorage.java)의 실제 코드와 일치한다.

판정: 지적 0건, 직접 대조한 migration·저장·exemplar 경로 확신도 높음.

## 실행 기록과 검증 한계

`otel-runtime-probes/RuntimeProbes.java` 전체, `actual.txt`, `validation.json`, `README.md`를 직접 읽었다. 4개 probe가 검사하는 조건과 본문에 제시한 결과 사이의 불일치는 찾지 못했다. 검증 기록에는 공개 JAR 5개의 고정 해시, Java 25.0.3·`--release 11`, probe별 5회 동일 출력과 exit 0이 있다. API-only 실험은 별도의 `NoopProbe.java`, README, validation 기록과 대조했다.

이 패널이 probe를 새로 실행한 것은 아니다. 저장된 결과의 주장 범위와 코드의 assertion을 대조한 검토이며, 최종 실행 감사와 구별한다. Maven JAR가 아닌 upstream 전체 빌드, OTLP 서버·백엔드 영속화, 성능, metrics/Collector/agent 통합 실행은 이 결과로 검증되지 않는다. 원고도 해당 한계를 명시한다.

상단 최근 3편 박스 및 중복 캡처 고지 정리는 root의 병행 편집 범위로 두었다. PNG의 최종 바이트·잘림·육안 확인, 전체 링크 검사, 마스킹 전수 감사, 발행 준비 여부는 이 사실관계 판정에 포함하지 않는다. HTML·Java 소스는 읽기 전용으로 검토했으므로 이 패널에서 LSP·lint·build를 실행했다고 주장하지 않는다.

## 변경 경계

원고 8편과 공통 자료는 수정하지 않았다. 이 보고서 파일만 새로 생성했다. 재위임·외부 댓글·커밋·푸시·발행은 하지 않았다.
