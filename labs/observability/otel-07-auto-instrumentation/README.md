# 07 자동 계측: 원자료와 검증 범위

2026-10-21 로컬 초안. 이 디렉터리는 agent 실행 실험을 담지 않는다. 소스 분석과 실제 실행을 구분하기 위한 기록이다. 발행·커밋·푸시는 하지 않았다.

## 산출물

- 본문: `posts/CS/Observability/otel/07_7편 - 자동 계측은 애플리케이션을 어디까지 알 수 있을까.html`
- 원자료 캡처 목록: `source-manifest.json`
- 본문 이미지 경로: `images/07/httpclient-matcher.png`, `images/07/httpclient-scope.png`
- PNG는 manifest의 고정 원문을 바꾸지 않고 로컬 코드 뷰어에서 렌더링했다. 공통 캡처 단계에서 2개 생성 완료를 보고받았고 두 파일의 존재를 독립 확인했다. 공통 단계의 태그 전체 SHA, 파일 해시, 원문 텍스트 동일성 및 행 잘림 검사 PASS 보고와 브라우저의 실제 본문 시각 검수는 구분한다.

## 소스 고정

- 공개 저장소: `open-telemetry/opentelemetry-java-instrumentation`
- 태그: `v2.32.0`
- 커밋: `1b8644f8eb11d90295b1c313391aa84edeeec6e2`
- 핵심 파일: `instrumentation/java-http-client/javaagent/src/main/java/io/opentelemetry/javaagent/instrumentation/javahttpclient/HttpClientInstrumentation.java`
- 파일 전체 SHA-256: `1c249809cb978054d106186d84a0f8f8e739d2edab9ef8183b2fbe4bb9600521`
- raw URL을 `curl -fsSL`로 읽고 `shasum -a 256`으로 독립 확인했다. 해시는 발췌문이나 Git blob ID가 아니다.

## 읽은 실제 경로

1. `classLoaderOptimization()` 및 `typeMatcher()`는 알려진 타입을 고른다. `java.net.` 또는 `jdk.internal.` namespace, HttpClient 상속, facade 제외를 모두 구분했다.
2. `transform()`이 public `send`와 `sendAsync`에 각각 다른 advice를 연결한다. 동기 메서드의 두 인자 조건과 비동기 조건은 동일하다고 쓰지 않았다.
3. 동기 `AdviceScope.start()`는 현재 Context, `shouldStart`, `instrumenter.start`, `makeCurrent`를 연결한다. 종료 advice는 scope가 있는 경우에만 `close` 및 `instrumenter.end`를 수행한다.
4. 비동기 `AsyncAdviceScope`는 CallDepth로 중첩을 구분한다. 메서드 반환 경계에서 Scope를 닫고, 메서드 자체의 예외는 즉시 종료하며, 정상 Future 반환은 완료 콜백으로 종료한다.
5. `ResponseConsumer.accept()`가 응답/Throwable과 저장한 Context를 `instrumenter.end`에 전달한다.
6. `CompletableFutureWrapper.wrap()`은 전달받은 Context를 현재로 만든 상태에서 완료를 전달한다. 이 호출자의 인자는 `parentContext`다. `cancel()`이 원본 Future에 취소를 전달한다는 구현은 확인했지만 모든 조합의 취소 의미 보존을 실행 검증했다고 주장하지 않았다.

보조 소스도 같은 커밋이다.

- [HttpClientInstrumentation.java](https://github.com/open-telemetry/opentelemetry-java-instrumentation/blob/1b8644f8eb11d90295b1c313391aa84edeeec6e2/instrumentation/java-http-client/javaagent/src/main/java/io/opentelemetry/javaagent/instrumentation/javahttpclient/HttpClientInstrumentation.java)
- [ResponseConsumer.java](https://github.com/open-telemetry/opentelemetry-java-instrumentation/blob/1b8644f8eb11d90295b1c313391aa84edeeec6e2/instrumentation/java-http-client/library/src/main/java/io/opentelemetry/instrumentation/javahttpclient/internal/ResponseConsumer.java)
- [CompletableFutureWrapper.java](https://github.com/open-telemetry/opentelemetry-java-instrumentation/blob/1b8644f8eb11d90295b1c313391aa84edeeec6e2/instrumentation/java-http-client/library/src/main/java/io/opentelemetry/instrumentation/javahttpclient/internal/CompletableFutureWrapper.java)

## 직접 확인한 현재 공식 문서

문서는 2026-10-21 확인 기준이다. 현재 문서 내용을 모든 과거 agent 버전에 소급하지 않는다.

- [Java agent](https://opentelemetry.io/docs/zero-code/java/agent/): bytecode 기반 지원 라이브러리 계측.
- [agent + API](https://opentelemetry.io/docs/zero-code/java/agent/api/): 추가 업무 계측과 agent의 조합.
- [지원 라이브러리](https://opentelemetry.io/docs/zero-code/java/agent/supported-libraries/): 버전과 신호별 범위. Java HTTP Client는 Java 11 이상이다.
- [계측 억제](https://opentelemetry.io/docs/zero-code/java/agent/disable/#instrumentation-span-suppression-behavior): 중첩 라이브러리와 semconv/span-kind/none 전략. 임의의 SDK/Handler/agent 조합까지 자동 중복 제거된다는 근거로 사용하지 않는다.
- [Micrometer Observation 1.17.1](https://docs.micrometer.io/micrometer/reference/observation/introduction.html): lifecycle, Handler, mutable Observation.Context, Convention.
- [Micrometer Tracing 1.7.1](https://docs.micrometer.io/tracing/reference/): OTel/Brave bridge와 exporter/reporter의 역할.
- [OBI](https://opentelemetry.io/docs/zero-code/obi/): probe 관찰 범위, Linux/architecture/kernel/BTF/권한 조건, 애플리케이션 의미의 한계. 모든 eBPF 도구의 공통 기능표로 쓰지 않는다.
- [OTel 오류 처리 사양](https://opentelemetry.io/docs/specs/otel/error-handling/): 업무 동작 보호와 실행 시 처리되지 않은 예외 억제의 요구. 구현의 완전성을 증명하는 자료로 사용하지 않는다.
- [민감정보 처리](https://opentelemetry.io/docs/security/handling-sensitive-data/): 필요한 값만 수집하고 출력을 검토하며 추가 처리 경로를 확인한다.

## 예시와 검증 한계

- HTTP 200이지만 승인 거절인 결제 예시, 수동 동기 Span 코드, 테스트 입력 제안은 가상 예시다.
- 본문의 의사 코드는 원본의 핵심 종료 분기를 설명하기 위한 요약이다. 중첩/null 처리를 생략했다고 명시했다.
- 수동 코드는 Tracer가 주입되어 있다는 가정이며 컴파일·실행한 샘플이 아니다. 예시 속성 이름은 표준 결제 속성이 아니다.
- agent, Java HTTP Client 네트워크 호출, OBI, Observation bridge를 실행하지 않았다. 공유 SDK runtime probe를 agent 검증 근거로 사용하지 않았다.
- CPU, 메모리, 지연, 전파, 취소, 중복 계측 및 개인정보 처리의 실제 서비스 검증은 남아 있다.
- HTML/SVG 구조 검사, 일반 비밀값 패턴 검사, template CSS 일치는 로컬에서 별도 실행해 결과를 보고한다. 독립 퇴고·사실 감사와 브라우저 시각 검수는 이 작성자의 자기 검사를 대신하지 않는다.

## 작성자 로컬 검사 결과

- `validate_html.py` 본문 대상: 명시적 HTML/SVG 구조 PASS.
- `mask-check.py` 본문·README·manifest 대상: 일반 패턴 검사 PASS. 조직 전용 allow/deny 입력을 주입한 검사는 아니다.
- template의 `<style>` 내용과 본문 CSS 바이트 단위 문자열 일치 PASS.
- 공통 시리즈 8개 항목 및 7편만 굵게 표시 PASS.
- PNG 상대 경로 존재, manifest basename, 캡처당 26행 이하 검사 PASS.
- em dash 및 금지 SVG 기본 도형 없음.
- 본문 집계: style/SVG/code/comment/HTML 태그를 제외한 비공백 10,273자, 한글 음절 7,483자. 장 10개, 용어 6개, SVG 2개, PNG 2개, 코드/의사 코드 2개다.
- 독립 퇴고·원자료 감사·브라우저 미리보기는 통합 담당 단계이며 이 결과에 포함하지 않는다.
