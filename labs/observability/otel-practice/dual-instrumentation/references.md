# 기술 근거 (2026-10-23 확인)

공식 문서는 탐색 도구로 열고 확인했다. 최신 reference URL은 확인 시 4.1.2로 리다이렉트되어, 실행은 4.1.1 고정 소스·실제 jar 메타데이터와 대조했다. 문서는 설정의 의미를 뒷받침하며 3/4/7, 실제 parent 구조와 MDC 값은 이 lab 실행 증거다.

- [Spring Boot tracing](https://docs.spring.io/spring-boot/reference/actuator/tracing.html): OTLP 스타터, `RestClient.Builder`에 의한 전파, `traceId`/`spanId` 로그 상관관계, Observation→Tracing handler.
- [Spring Boot observability](https://docs.spring.io/spring-boot/reference/actuator/observability.html): Spring Micrometer 계측과 OTel agent의 의미 체계가 다름, `management.opentelemetry.enabled`의 no-op SDK 의미.
- [Boot v4.1.1 MicrometerTracingAutoConfiguration](https://github.com/spring-projects/spring-boot/blob/v4.1.1/module/spring-boot-micrometer-tracing/src/main/java/org/springframework/boot/micrometer/tracing/autoconfigure/MicrometerTracingAutoConfiguration.java): Observation handler 등록 클래스와 조건. agent 기준군의 명시적 제외 대상.
- [Boot v4.1.1 OpenTelemetryTracingAutoConfiguration](https://github.com/spring-projects/spring-boot/blob/v4.1.1/module/spring-boot-micrometer-tracing-opentelemetry/src/main/java/org/springframework/boot/micrometer/tracing/opentelemetry/autoconfigure/OpenTelemetryTracingAutoConfiguration.java): Boot Tracer 생성 대상. 정확한 클래스명은 빌드 jar의 AutoConfiguration.imports와 대조.
- 빌드 jar `spring-boot-micrometer-tracing-4.1.1.jar`의 `META-INF/spring-configuration-metadata.json`: `management.tracing.enabled`는 deprecated error, replacement는 `management.tracing.export.enabled`. export off와 tracing handler 제외를 구분.
- [Java agent instrumentation suppression](https://opentelemetry.io/docs/zero-code/java/agent/disable/): 개별 계측의 on/off 및 agent의 기본 semconv 억제. agent가 자기 내부의 중복을 억제한다고 별도 Boot SDK의 중복도 없다고 단정하지 않는다.
- [Java agent v2.32.0 Logback MDC instrumentation](https://github.com/open-telemetry/opentelemetry-java-instrumentation/blob/v2.32.0/instrumentation/logback/logback-mdc-1.0/javaagent/src/main/java/io/opentelemetry/javaagent/instrumentation/logback/mdc/v1_0/LoggingEventInstrumentation.java): `ILoggingEvent.getMDCPropertyMap/getMdc` 반환값에 agent context trace/span ID를 넣는다. MDC.get API와 실제 출력 값이 다를 수 있는 이유.
- [Java agent v2.32.0 MDC config](https://github.com/open-telemetry/opentelemetry-java-instrumentation/blob/v2.32.0/instrumentation/logback/logback-mdc-1.0/javaagent/README.md): agent 기본 키 `trace_id`, `span_id`.
