# 03. Java agent와 Micrometer Tracing을 같이 켜면 어떻게 될까

동일 Spring Boot 앱을 agent / micrometer / both 세 구성으로 실행하고 `/checkout → checkout.quote Observation → RestClient → /inventory`를 실제 요청한다. 요청은 외부 `traceparent` 없이 시작한다. Collector가 Tempo에 보낸 고유 span ID 집합, scope, parent 관계, HTTP 대상·실행 구간, 실제 stdout 로그를 대조한다.

## 실행

Docker Desktop(Compose v2와 BuildKit), Python 3 필요. Gradle/Maven 의존성 및 Java agent 다운로드에 최초 네트워크 접근이 필요하다. 호스트에 Java나 Gradle 설치는 필요 없다.

```bash
cd labs/observability/otel-practice/dual-instrumentation
python3 run.py                   # Docker build/up + readiness + 각 구성 3회 요청 + 검증
python3 run.py --no-build        # 소스/이미지 변경이 없을 때만
cat out/results.txt
# 실제 로컬 UI
open http://localhost:27300/d/dual-instrumentation
# 정리: 이 실습 프로젝트만 종료 (다른 프로젝트에 영향 없음)
docker compose down
```

`run.py`는 매 실행 시 이 lab의 `out/` 파일을 지우고 새 증거로 교체한다. 이전 실행은 먼저 다른 디렉터리에 보관한다. 각 요청의 응답 `receivedTraceparent`에서 **이번 요청에서 새로 만들어진 trace ID**를 얻고 그 ID로 Tempo를 polling한다. 예전 trace 검색 결과를 합산하지 않는다. 준비 완료와 span 도착은 polling하며, timeout/ID/그래프 검증 실패 시 비정상 종료한다. 기본 assertion은 이 고정 버전의 관찰 결과를 회귀 검증하므로 버전 변경 시 실패를 검토해야 한다.

기본 `--requests 3`은 학습용 반복이지 통계적 부하 시험이 아니다. 브라우저의 `/ready` 확인 요청은 별도 trace이며 측정에 섞이지 않는다. 기본 Compose 프로젝트명 `otel-practice-03`, 모든 호스트 포트는 loopback 바인딩이다.

## 구성과 버전

| 대상 | 버전 | 로컬 주소 |
|---|---|---|
| Java runtime | Eclipse Temurin 21 (실행 시 21.0.12.1) | 컨테이너 |
| Spring Boot / Micrometer Tracing | 4.1.1 / 1.7.1 | 아래 서비스 |
| Java agent / 내장 OTel SDK | 2.32.0 / 1.66.0 | agent, both |
| Boot 의존 OTel SDK | 1.62.0 | micrometer, both |
| Collector contrib | 0.162.0 | Docker network only |
| Tempo | 2.10.8 | http://localhost:27320 |
| Grafana | 13.2.3 | http://localhost:27300 |
| agent / micrometer / both 앱 | 동일 jar | http://localhost:27381 / 27382 / 27383 |

각 Java 컨테이너는 `-Xmx256m`, 512m 제한. Grafana는 1g이다. 256m와 512m에서 Explore 로딩 중 OOM(exit137)이 확인되어 올렸고 자동 플러그인 사전 설치·업데이트를 껐다. Grafana 익명 Admin은 로컬 실습 전용이다.

- **agent:** `-javaagent:/otel/agent.jar`. 같은 jar에서 Spring의 `MicrometerTracingAutoConfiguration` 및 `OpenTelemetryTracingAutoConfiguration`을 제외하고 Boot SDK를 끈다. Observation/Micrometer 측정 자체는 남지만 트레이싱 handler는 제외한다. 상세 클래스명은 compose 참고.
- **micrometer:** agent 없이 Boot `spring-boot-starter-opentelemetry`를 사용한다. 스타터가 Micrometer bridge와 OTLP 의존성을 포함한다. `RestClient.Builder`를 Spring에서 주입받아 생성한다.
- **both:** agent와 Boot 트레이싱 기본 자동 설정을 모두 켠다. 이것은 중첩 문제를 관찰할 비교군이며 운영 권장 설정이 아니다.
- 샘플링은 전부 기록하도록 고정. trace export는 HTTP/protobuf, `collector:4318/v1/traces`를 사용한다. 로그는 Docker stdout으로 수집하며 Loki는 쓰지 않는다.

`management.opentelemetry.enabled=false`만으로 agent 기준군을 정의하지 않았다. SDK가 no-op이어도 Micrometer handler/전파가 남을 수 있어 불필요한 context/MDC 효과를 피하려고 관련 자동 설정을 명시적으로 제외했다. `management.tracing.enabled`는 Boot 4에서 제거된 속성이므로 사용하지 않는다. `management.tracing.export.enabled=false`도 export를 끄는 속성이므로 handler 제거와 구분한다.

## 실제 결과

실행 시각 및 고유 ID는 `out/summary.json`, 원시 Tempo 응답은 `out/*-tempo.json`, 정규화한 scope/resource/parent는 `out/*-spans.json`, 해당 실행의 로그는 `out/application.log`에 남는다.

| 구성 | 요청 수 | 요청별 고유 스팬 | SERVER / CLIENT / INTERNAL | scope |
|---|---:|---:|---|---|
| agent | 3 | 3 | 2 / 1 / 0 | Tomcat, JDK HTTP client |
| micrometer | 3 | 4 | 2 / 1 / 1 | org.springframework.boot |
| both | 3 | 7 | 4 / 2 / 1 | 위 두 경로 모두 |

개수뿐 아니라 각 `/checkout`, `/inventory`의 SERVER 두 개가 **다른 scope에서 같은 HTTP 작업을 겹치는 시간에 기록**한 것, CLIENT 두 개가 같은 URL을 겹치는 시간에 기록한 것을 assert했다. 모든 스팬은 하나의 trace ID에 속했고 parent는 같은 trace 안의 스팬 또는 비어 있는 로컬 루트였다. 추적된 실제 로그의 span ID도 그 요청의 내보낸 스팬 집합에 포함됐다.

Micrometer 단독은 `/checkout → checkout.quote → HTTP client → /inventory` 순서다. both에서는 `checkout.quote`와 Spring HTTP client가 agent `/checkout` 바로 아래에 놓였고, 로그의 `spanId`도 quote가 아니라 agent `/checkout`을 가리켰다. 이 결과를 비동기·다른 라이브러리·다른 버전으로 일반화하지 않는다.

agent의 로그 `trace_id`는 LoggingEvent에 계측되어 들어가는 값이다. `MDC.get("trace_id")`가 비어 있다고 실제 출력의 상관관계까지 없다고 판단하면 안 된다. 그래서 응답에 담은 MDC API 값과 실제 로그 문자열을 따로 수집한다. Micrometer 로그는 기본 camelCase `traceId`/`spanId`를 사용한다.

## 실제 브라우저 캡처

이미 설치된 Playwright와 Chrome을 사용한다. 별도 설치 명령은 실행하지 않는다.

```bash
/Users/dding/.local/share/tistory-uploader/venv/bin/python capture.py
```

사용 환경에 맞게 Python 경로를 바꾸면 된다. `capture.py`는 최신 `summary.json`의 trace ID로 실제 Grafana Explore를 연다. `checkout.quote`, `4 spans`/`7 spans`, 해당 ID와 오류 부재를 확인하고, 표시된 텍스트 마스킹 검사를 통과해야 캡처한다. `out/*-grafana-body.txt`, `out/explore-urls.json`과 글의 `images/lab-03/*.png`가 연결된다. 출력 캡처는 `out/results.txt`를 term-shot으로 렌더링한 것으로 실제 터미널 GUI 화면을 찍었다고 주장하지 않는다. 다시 실행하면 캡처도 다시 해야 ID가 맞는다.

## 관찰 한계

동기 HTTP 자기 호출과 직접 Observation 한 개만 검증했다. 비동기 context 전파, JDBC, annotation 계측, 외부 traceparent 유무에 따른 차이, 오류 요청, 메모리/CPU/지연 비용은 비교 대상이 아니다. 스팬 개수는 이 구성의 결과이며 Java agent와 Micrometer를 함께 켜면 모든 버전에서 무조건 두 배라는 주장은 하지 않는다. 운영에서는 사용하는 라이브러리별로 어떤 쪽이 HTTP·DB·사용자 정의 구간을 담당할지 정한 뒤 실제 parent와 로그 상관관계를 다시 검사해야 한다.

공식 문서와 고정 소스의 확인 범위는 [references.md](references.md)에 정리했다.
