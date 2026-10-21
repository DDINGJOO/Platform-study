# OpenTelemetry Java: 제어된 런타임 실험

OpenTelemetry Java **1.67.0** 공개 Maven 아티팩트로 API/SDK, 컨텍스트, 배치 유실,
샘플링 결정을 실제 실행해 확인한다. 상위 소스를 수정하거나 전체 프로젝트를 빌드하는 실험은 아니다.

```sh
python3 labs/observability/otel-runtime-probes/verify.py --repeat 5
```

JDK 11 이상과 Python 표준 라이브러리만 필요하다. 러너는 필요한 공개 JAR 다섯 개를 임시
디렉터리에 받아 고정 SHA-256을 검증한다. 전역 의존성 설치, 인증 정보, 실제 exporter 연결,
글 발행은 없다. JAR와 클래스 파일은 종료 시 삭제된다. 각 실험을 별도 JVM에서 실행한다.

## 검사하는 네 가지 경계

1. **API/SDK**: 동일한 Span API에서 명시적 noop root는 기록하지 않고 컨텍스트도 유효하지 않다.
   **이 버전은 SDK를 만들기만 해도 기록하는 것이 아니다.** processor가 하나도 없으면 SDK가
   noop tracer를 돌려줘 root span의 recording=false, context-valid=false가 나온다.
   exporter 없이 종료만 세는 사용자 정의 processor를 붙이면 유효한 recording span이 만들어지고
   종료 콜백도 온다. 마지막으로 SimpleSpanProcessor와 메모리 exporter를 연결해 종료 후 전달을 검사한다.
2. **컨텍스트**: 단일 worker에 `worker-baseline` 컨텍스트를 유지한다. 일반 task와 캡처한
   `Context.wrap` task가 서로 다른 값을 읽는지 확인하고, wrapped task가 의도적으로 예외를 던진 뒤에도
   같은 worker에서 기존 컨텍스트가 복구되는지 확인한다. 호출 스레드의 원래 컨텍스트도 확인한다.
3. **배치**: 큐 크기 2, 배치 크기 1로 설정한다. 첫 export는 완료되지 않은
   `CompletableResultCode`를 반환하게 하고, 진입 latch를 기다린 다음 추가 span 다섯 개를 종료한다.
   최초 export가 아직 pending임을 확인한 뒤 해제하고 forceFlush한다. 종료한 여섯 span 중
   최초 하나와 큐에 들어간 두 span만 exporter에 전달됐는지 이름과 개수를 모두 검사한다.
4. **샘플링**: 프로그램으로 만든 SDK의 기본 설정에서 root, sampled remote parent,
   unsampled remote parent를 비교한다. 명시적 always-on/off도 비교한다. 사용자 정의
   RECORD_ONLY sampler는 recording=true, sampled=false를 만들며, SimpleSpanProcessor의
   `setExportUnsampledSpans` 설정에 따라 메모리 exporter에 도착하는지 여부가 달라짐을 검사한다.
   기본/always-on/off 비교에는 종료만 세는 processor를 넣어 no-processor 최적화를 우회한다.

출력은 실제 검사 값과 PASS 표시다. 반복 실행에서도 같은 출력인지 확인한다. timeout은
멈춤 방지 장치이고, 실행 순서는 latch와 완료 신호로 제어한다. sleep, 성능 수치, 시간에 근거한
성공 판정은 사용하지 않는다.

## 해석 범위

- 큐 실험의 3개 미전달은 이 설정과 제어된 순서의 결과다. 모든 SDK 설정에서의 유실률이 아니다.
- 메모리 exporter 호출 성공은 OTLP 전송이나 저장소 내구성을 뜻하지 않는다.
- `RECORD_ONLY`만으로 exporter 도착 여부를 단정하지 않는다. processor의 필터와 구성이 별도 경계다.
- 기본 sampler 결과는 자동 구성이 없는 `SdkTracerProvider.builder()` 기준이다. 에이전트나 환경 변수의
  sampling 설정을 포함하지 않는다.
- 유효한 parent context, 저장소 영속화, 모든 비동기 라이브러리의 자동 전파, 성능은 별도 문제다.

## 고정 원본 참조

태그 `v1.67.0`, 커밋 `b4b3a1b354425c3f1411173c0e48cb24a1cba224`의 다음 공개 코드를 대조했다.

- [Context.wrap](https://github.com/open-telemetry/opentelemetry-java/blob/b4b3a1b354425c3f1411173c0e48cb24a1cba224/context/src/main/java/io/opentelemetry/context/Context.java#L235-L245)
- [BatchSpanProcessor 큐 등록](https://github.com/open-telemetry/opentelemetry-java/blob/b4b3a1b354425c3f1411173c0e48cb24a1cba224/sdk/trace/src/main/java/io/opentelemetry/sdk/trace/export/BatchSpanProcessor.java#L228-L241)
- [기본 sampler](https://github.com/open-telemetry/opentelemetry-java/blob/b4b3a1b354425c3f1411173c0e48cb24a1cba224/sdk/trace/src/main/java/io/opentelemetry/sdk/trace/SdkTracerProviderBuilder.java#L29-L37)
- [processor가 없을 때 noop 최적화](https://github.com/open-telemetry/opentelemetry-java/blob/b4b3a1b354425c3f1411173c0e48cb24a1cba224/sdk/trace/src/main/java/io/opentelemetry/sdk/trace/SdkTracerProvider.java#L98-L107)
- [SimpleSpanProcessorBuilder unsampled 설정](https://github.com/open-telemetry/opentelemetry-java/blob/b4b3a1b354425c3f1411173c0e48cb24a1cba224/sdk/trace/src/main/java/io/opentelemetry/sdk/trace/export/SimpleSpanProcessorBuilder.java#L18-L33)

공개 아티팩트의 좌표·다운로드 URL·해시와 실행 결과는 러너 마지막 `VALIDATION_JSON`에 나온다.
표준 출력은 [actual.txt](actual.txt), 반복 횟수·표준 오류·검증 범위까지 담은 기록은
[validation.json](validation.json)에 저장했다. 배치 실험에서 실제 SDK가 남기는 queue-full
경고도 검증한다. 로그 포맷에서 시각만 빼 반복 실행을 비교하며 경고를 숨기지는 않는다.
저장된 파일은 과거 실행 기록이며 재실행 결과가 우선한다.
