# 4편 근거: 샘플링 결정과 부모 정책

2026-10-21 공개 공식 문서와 Java v1.67.0 소스를 읽은 기록이다. 동일 버전의 공개 Maven 아티팩트로 실행한 최소 부모 정책·RECORD_ONLY 실험 결과도 대조했다. 부하 실험, 서비스 호출, 실제 수집률 측정은 수행하지 않았다. 초기 개요를 확장해 호출 경로·정책별 반례·Collector 및 Jaeger 정책의 역할 비교를 포함했다.

## 고정한 구현

- 저장소: `open-telemetry/opentelemetry-java`
- 태그: `v1.67.0`
- 커밋: `b4b3a1b354425c3f1411173c0e48cb24a1cba224`
- 캡처와 원문 파일의 SHA-256: [source-manifest.json](source-manifest.json)
- 출력: `posts/CS/Observability/otel/images/04/ratio-decision.png`, `parent-decision.png`

캡처는 고정 커밋의 원문을 수정 없이 로컬 코드 뷰어에서 렌더링한 이미지다. 본문에는 파일명·줄 번호·버전·원문 링크와 텍스트 풀이를 함께 제공한다. PNG 생성과 브라우저 확인은 시리즈 통합 단계에서 수행한다.

## 읽은 범위와 주장

1. [TraceIdRatioBasedSampler.java L37-L80](https://github.com/open-telemetry/opentelemetry-java/blob/b4b3a1b354425c3f1411173c0e48cb24a1cba224/sdk/trace/src/main/java/io/opentelemetry/sdk/trace/samplers/TraceIdRatioBasedSampler.java#L37-L80): ratio로 임계값을 만들고 `Math.abs(getTraceIdRandomPart(traceId)) < idUpperBound`를 검사한다. L111-L112는 trace ID 뒤쪽 64비트 읽기다. 결과는 L30-L32의 `recordAndSample` 또는 `drop`이다. 모든 SDK의 공통 알고리즘이라고 하지 않는다.
2. [Sampler.java L77-L92](https://github.com/open-telemetry/opentelemetry-java/blob/b4b3a1b354425c3f1411173c0e48cb24a1cba224/sdk/trace/src/main/java/io/opentelemetry/sdk/trace/samplers/Sampler.java#L77-L92): 알고리즘은 API 계약으로 고정되지 않으며 `ParentBased`의 root sampler로 사용하는 것을 권고한다. 코드는 기존 구현 학습용이지 현행 모든 환경의 설정 권고가 아니다.
3. [ParentBasedSampler.java L32-L76](https://github.com/open-telemetry/opentelemetry-java/blob/b4b3a1b354425c3f1411173c0e48cb24a1cba224/sdk/trace/src/main/java/io/opentelemetry/sdk/trace/samplers/ParentBasedSampler.java#L32-L76): 유효한 부모가 없으면 root로 위임한다. 부모가 있으면 remote/local 및 sampled 여부로 위임 대상을 선택한다. 기본값은 sampled 부모에 alwaysOn, 그 외 alwaysOff이며, builder로 바꿀 수 있다.
4. [공식 Trace SDK 사양](https://opentelemetry.io/docs/specs/otel/trace/sdk/#sampling): DROP, RECORD_ONLY, RECORD_AND_SAMPLE은 기록 여부와 sampled 플래그를 구분한다. RECORD_ONLY가 어떤 설정에서도 절대 export되지 않는다고 쓰지 않는다.
5. [공식 Trace SDK 사양의 TraceIdRatioBased 절](https://opentelemetry.io/docs/specs/otel/trace/sdk/#traceidratiobased): 현재 문서는 ProbabilitySampler로의 전환을 설명한다. 원래 구현 동작은 최소 2027-01-01까지 제거·변경하지 않도록 요구하며, 그 날짜에 Java API가 반드시 사라진다는 뜻이 아니다.
6. [공식 Sampling 문서](https://opentelemetry.io/docs/concepts/sampling/): head는 전체 trace 결과를 보고 결정하지 않는다. tail은 받은 스팬들을 바탕으로 더 늦게 결정하지만, 저장 상태와 처리 자원이 필요하다. 이미 head에서 기록하지 않은 정보를 복구할 수 있다는 보장은 없다.

## 심화판에서 추가로 대조한 원자료

- [SdkTracerProvider.java L98-L107](https://github.com/open-telemetry/opentelemetry-java/blob/b4b3a1b354425c3f1411173c0e48cb24a1cba224/sdk/trace/src/main/java/io/opentelemetry/sdk/trace/SdkTracerProvider.java#L98-L107): 프로세서가 하나도 없으면 no-op TracerBuilder를 반환한다. SDK 객체와 샘플러를 만드는 것만으로 아래 경로가 실행된다고 단정하지 않는다.
- [SdkSpanBuilder.java L182-L277](https://github.com/open-telemetry/opentelemetry-java/blob/b4b3a1b354425c3f1411173c0e48cb24a1cba224/sdk/trace/src/main/java/io/opentelemetry/sdk/trace/SdkSpanBuilder.java#L182-L277): 부모/ID 선택 → shouldSample → decision/tracestate → SpanContext flags → 비기록 Span 또는 SdkSpan 생성 → 샘플러 속성 합치기.
- [SdkSpan.java L560-L583](https://github.com/open-telemetry/opentelemetry-java/blob/b4b3a1b354425c3f1411173c0e48cb24a1cba224/sdk/trace/src/main/java/io/opentelemetry/sdk/trace/SdkSpan.java#L560-L583): 종료 시 필요한 프로세서 onEnd 호출.
- [BatchSpanProcessor.java L118-L123](https://github.com/open-telemetry/opentelemetry-java/blob/b4b3a1b354425c3f1411173c0e48cb24a1cba224/sdk/trace/src/main/java/io/opentelemetry/sdk/trace/export/BatchSpanProcessor.java#L118-L123) 및 [Builder.java L32-L53](https://github.com/open-telemetry/opentelemetry-java/blob/b4b3a1b354425c3f1411173c0e48cb24a1cba224/sdk/trace/src/main/java/io/opentelemetry/sdk/trace/export/BatchSpanProcessorBuilder.java#L32-L53): 기본은 sampled만 worker에 추가하지만 exportUnsampledSpans 옵션으로 달라질 수 있다. RECORD_ONLY의 export 금지를 모든 구성에 일반화하지 않는다.
- [Collector Contrib tail sampling README](https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/52328b62aef67653eaea51dfead90f8050fbba72/processor/tailsamplingprocessor/README.md): 커밋 `52328b62aef67653eaea51dfead90f8050fbba72`로 고정했다. 기본 trace-complete와 span-ingest를 구분한다. 같은 trace의 라우팅, 결정 전 용량 초과 제거, 늦은 스팬 및 결정 캐시 조건을 읽었다. 원문에 있는 모든 기본값을 재현했다고 하지 않는다.
- [Jaeger 2.22 sampling](https://www.jaegertracing.io/docs/2.22/architecture/sampling/): remote는 SDK에 head 정책을 배포하는 기능이다. adaptive는 관측 데이터를 이용해 서비스/엔드포인트별 목표 samples-per-second에 맞는 확률을 조정한다. 에러 보존 규칙이나 고정 바이트 대역폭 보장과 구분한다. Jaeger와 OTel을 상호 배타적인 제품으로 비교하지 않는다.

## 설명용 계산과 반례

- 실패 건수가 n으로 주어지고 독립적인 trace별 포함 확률 p가 실패 여부와 독립이라는 가정에서 `P(실패 n건을 전부 놓침)=(1-p)^n`이다. p=0.1, n=1/5/20/50일 때 각각 90%/59.049%/12.157665...%/0.515377...%이다. 실측이 아니다.
- 같은 trace 안의 ParentBased 자식 스팬들은 독립 표본이라고 하지 않는다. 임의 입력에 대한 정확한 비율 보장도 하지 않는다.
- 전체 요청 100건 중 에러 1건인데 선택 결과는 성공 9건+에러 1건인 가정에서, 선택 결과의 단순 오류율 10%와 원래 오류율 1%는 다르다. tail 전 집계도 앞 SDK의 DROP을 자동 복구하지는 않는다.

## 확인 한계

- 실제 최소 실행 기록은 [공통 런타임 프로브](../otel-runtime-probes/README.md), [actual.txt](../otel-runtime-probes/actual.txt), [validation.json](../otel-runtime-probes/validation.json), [RuntimeProbes.java](../otel-runtime-probes/RuntimeProbes.java)를 직접 읽고 대조했다. OpenJDK 25.0.3, javac --release 11, Maven 1.67.0 JAR 고정 해시 검증, 5회 반복 출력 일치다. 상위 소스 전체 빌드나 서비스 간 전파 실험은 아니다.
- 기본 sampler 실행은 종료만 세는 processor를 등록해 no-processor 최적화를 우회했다. root 및 원격 sampled/unsampled 부모를 검사했고, 명시적 alwaysOn/alwaysOff는 sampler 자체를 바꾼 사례다. 모든 로컬/원격 분기를 실행했다고 하지 않는다.
- 사용자 정의 RECORD_ONLY sampler는 SimpleSpanProcessor의 setExportUnsampledSpans(false/true)에 따라 메모리 exporter 도착 수가 0/1로 달라졌다. 본문에서 소스로 설명한 BatchSpanProcessor 실행 결과로 바꾸어 인용하지 않는다.
- 부하·수집률·네트워크 OTLP 전송·백엔드 영구 저장·성능은 측정하지 않았다.
- 10% 설정을 임의의 작은 요청 묶음에 적용하면 정확히 10%가 나온다고 보장하지 않는다.
- 부모 정책을 따른다는 것은 샘플링 결정에 관한 설명이며, 모든 서비스의 스팬 수집·전송·보관 성공을 뜻하지 않는다.
- 공개 공식 자료만 사용했다. 비공개 보안 제보나 조직 자료는 포함하지 않았다.
