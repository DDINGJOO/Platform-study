# 독립 원자료 감사

판정: **PASS**. 핵심 주장 32건 중 **확인 32 / 불일치 0 / 확인 불가 0 / 과장 0**. 추가 수정 요구 없음.

감사자 `final_audit`는 네 작성자 및 네 퇴고자와 다른 에이전트다. 퇴고 승인 대신 최종 HTML, 서비스 코드, Collector 설정, 원시 실행 자료, 실제 화면을 직접 대조했다. 2026-10-23 13:22 UTC 이후 읽기 전용 재검증을 수행했으며, 파일 수정·실습 재실행·증거 덮어쓰기를 하지 않았다. 이 보고서는 감사자의 최종 보고를 루트 에이전트가 저장한 것이다.

아래 경로는 `labs/observability/otel-practice/`를 기준으로 한다. 대상 글은 `posts/CS/Observability/otel-practice/`의 네 편이다.

| ID | 판정 | 주장과 직접 대조한 근거 |
|---|---|---|
| 01-01 | 확인 | `collector-loss/service.py`는 SDK 없이 OTLP JSON을 만들고 요청당 스팬 1개, 고정 1ms를 넣는다. 글도 실제 지연 측정으로 주장하지 않는다. |
| 01-02 | 확인 | `memory.yaml`, `disk.yaml`: 큐 요청 단위 크기 100, 소비자 1, 비동기 수락, 포화 거절, 재시도 시간 제한 없음. 본문 설정과 일치한다. |
| 01-03 | 확인 | 정상 10개, 단순 장애 후 양쪽 20개 저장은 생성 ID·수신 행·현재 Tempo와 일치한다. 장애는 게이트웨이 HTTP 503으로 한정한다. |
| 01-04 | 확인 | 수락 후 SIGKILL에서 메모리 20개 유실, 동일 볼륨 디스크 20개 복구. 실행기의 종료·재시작·sentinel 및 현재 수신/Tempo 자료로 확인했다. |
| 01-05 | 확인 | 포화: 생성 140, 수락 100, 거절 40, 저장 100. 개별 응답·ID 집합과 일치하며 고정 수락량으로 일반화하지 않는다. |
| 01-06 | 확인 | 처리 후 첫 응답 503: 고유 3개, 수신 6행, 추가 전달 3회. 실제 패킷 손실이나 Tempo 중복 표시로 주장하지 않는다. |
| 01-07 | 확인 | stored는 SQLite 커밋된 고유 ID, missing은 수락 집합 대비 누락, duplicates는 추가 수신 행이다. 조회·재해 내구성과 구분한다. |
| 01-08 | 확인 | `python3 -B collector-loss/verify.py`를 새로 실행해 7개 시나리오 및 현재 Tempo의 173개 스팬을 조회했다. 결과·복구 트레이스 PNG의 수치와 ID가 일치한다. |
| 02-01 | 확인 | `tail-sampling/app/service.py`: 실제 ParentBased/TraceIdRatioBased(0.25), 모드별 독립 ID, 요청별 부모·자식 두 스팬. |
| 02-02 | 확인 | 세 주 모드 각각 정상 40·오류 10·느림 10과 지연 전송 2건, 총 HTTP 요청 182건은 요청 목록·응답·로그와 일치한다. |
| 02-03 | 확인 | ERROR 또는 관측 시간 200ms 초과 정책이다. HTTP 500과 OTel ERROR를 구분하며, 고정 latency 구현은 가장 이른 시작과 가장 늦은 종료의 차이다. |
| 02-04 | 확인 | 정상/오류/느림 저장은 Head 10/3/1, Tail 0/10/10, Head→Tail 0/5/1이다. SDK 선택·Collector 출력·Tempo와 일치한다. |
| 02-05 | 확인 | Head 오류 3건과 Head→Tail 5건은 다른 ID 집합이다. 글은 추가 복구로 해석하지 않으며, SDK 미선택 ID는 해당 Collector/Tempo에도 없다. |
| 02-06 | 확인 | 자식 작업 종료 시각은 약 15ms 구간이고 전송만 5초 지연한다. late-long 길이 15.96ms, wait 2초 부재·8초 두 스팬 존재를 확인했다. |
| 02-07 | 확인 | `collector-metrics.txt`의 비선택 결정 캐시 적중 1과 본문이 일치한다. 부재 관찰은 기대 도착 뒤 추가 10초로 한정한다. |
| 02-08 | 확인 | `python3 -B tail-sampling/verify.py --live`로 182개 ID를 새로 조회해 41개 트레이스·82개 스팬과 부모를 대조했다. PNG의 ID·322.9ms·결과가 일치한다. |
| 03-01 | 확인 | 같은 jar의 세 구성 및 agent 기준군의 두 자동 설정 제외가 `dual-instrumentation/compose.yaml`에 있다. export off를 계측 제거와 구분한다. |
| 03-02 | 확인 | Boot 4.1.1, agent 2.32.0, SDK 1.66.0/1.62.0은 빌드 설정·실행 자료·스팬 resource와 부합한다. |
| 03-03 | 확인 | 현재 Tempo의 9개 트레이스에 normalize/assert_graph를 새로 적용했다. 구성별 3회 모두 3/4/7개, SERVER/CLIENT/INTERNAL 2/1/0·2/1/1·4/2/1이다. |
| 03-04 | 확인 | both의 HTTP SERVER 두 scope 및 시간 중첩, 같은 URL CLIENT 중첩을 확인했다. quote는 별도 업무 의미이며 총개수만으로 중복을 판정하지 않는다. |
| 03-05 | 확인 | 단독 CLIENT의 부모는 quote, both에서는 quote와 Spring CLIENT가 바깥 agent SERVER의 자식이다. 실제 parent ID·그림·화면이 일치한다. |
| 03-06 | 확인 | quote 안 MDC span ID는 단독에서 quote, both에서 바깥 SERVER다. 응답·스팬 집합·요청별 실제 로그 3행을 대조했다. |
| 03-07 | 확인 | agent 단독 MDC API와 출력 로그의 snake_case ID 차이는 실제 자료 및 고정 agent의 LoggingEvent MDC 반환값 주입 소스와 부합한다. |
| 03-08 | 확인 | 두 Grafana PNG가 첫 측정 trace ID에 대응한다. 단독 4개/11.69ms, both 7개/21.46ms는 원자료 11.687875/21.455208ms와 일치한다. 성능 비교로 주장하지 않는다. |
| 04-01 | 확인 | `sensitive-data/service.py`, 원시 자료 및 현재 Tempo/Loki에서 모드당 요청 3·스팬 9·예외 3·로그 6을 확인했다. |
| 04-02 | 확인 | 원시 필드를 재계수했다. raw 표식 속성 6·예외 3·상태 3·로그 6, narrow는 속성만 0이다. |
| 04-03 | 확인 | scrubbed 변환이 실제 pipeline에 연결돼 있고 처리된 속성·예외·상태·로그 표식은 0이다. exception.stacktrace 삭제도 확인했다. |
| 04-04 | 확인 | scrubbed에서도 표식 HTTP baggage 3건·원본 콘솔 6건이 남는다. http-responses.json·source-console.txt와 일치한다. |
| 04-05 | 확인 | minimized는 발생 시 기록을 생략하고 baggage tier만 남긴 문맥을 한 번 attach/finally detach한다. trace context를 지우는 코드가 아니다. |
| 04-06 | 확인 | minimized 표식 baggage/콘솔 0, tier=gold 전달 3, 요청별 연결된 스팬 3개를 현재 Tempo ID·부모 및 응답에서 확인했다. |
| 04-07 | 확인 | 현재 12개 트레이스·36개 스팬, Loki 모드별 6개·총 24개 로그를 조회했다. raw/narrow 자료는 여전히 표식을 포함하고, 글도 과거 삭제로 주장하지 않는다. |
| 04-08 | 확인 | Grafana 네 패널의 run-e768cc, 각 6행 및 raw/narrow 원문·scrubbed 치환·minimized 생략이 Loki 원자료와 일치한다. 결과 PNG·본문 표도 일치한다. |

3편의 새 Tempo 응답은 최초 저장 응답에 있던 `flags`를 생략했으나, ID·이름·scope·속성·시간·부모와 결론은 동일했다. 원시 JSON의 바이트 동일성으로 판정하지 않았다.

## 공식 대조 자료

- [Collector 복원력](https://opentelemetry.io/docs/collector/resiliency/): 메모리·영속 큐 및 유실 조건.
- [Tail sampling 0.162.0](https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/v0.162.0/processor/tailsamplingprocessor/README.md), [같은 버전 latency 구현](https://raw.githubusercontent.com/open-telemetry/opentelemetry-collector-contrib/v0.162.0/processor/tailsamplingprocessor/internal/sampling/latency.go): 판단 입력·시간 계산.
- [Java agent 2.32.0 LoggingEvent 계측](https://raw.githubusercontent.com/open-telemetry/opentelemetry-java-instrumentation/v2.32.0/instrumentation/logback/logback-mdc-1.0/javaagent/src/main/java/io/opentelemetry/javaagent/instrumentation/logback/mdc/v1_0/LoggingEventInstrumentation.java): MDC API와 출력 주입의 차이.
- [Transform processor 0.162.0](https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/v0.162.0/processor/transformprocessor/README.md), [OTel baggage](https://opentelemetry.io/docs/concepts/signals/baggage/): 변환 범위와 별도 HTTP 전파.

수신=저장=내구성, tail의 모든 오류 보존, 총 스팬 수=중복, Collector 처리=모든 개인정보 삭제라는 확대 주장의 반례를 우선 점검했다. 글들은 확인하지 않은 조건을 명시한다. 후속 A/A′/B 및 Netflix 도구는 ROADMAP에서 미구현으로 구분한다.

3편은 두 SDK·브리지·agent 버전 및 동기 HTTP 구현에 영향을 받으므로 일반화 범위가 가장 좁다. 본문이 그 한계를 명시하고 현재 조합의 반복 결과와 부모·로그 관계를 증명하므로 미해결 감사 항목은 아니다.

## 감사 대상 최종 HTML SHA-256

```text
01 a4dd3f1ad26aa60c2ff5d2fd1112d373d51e2f80407fb1b35a4f09e89a65eb07
02 e01310c2003198716ed314b8be82f6e1ffb818cbf2c6003dba04afc13f11e8b2
03 9f73130269299c13a51f9e80c74f7c4dbbb0767836e4b515919d14836f4fc28b
04 b73c52bf6c3baba6ba3832adcb8ada27b0495e99a094b3c77cd256f3a3a5bf22
```
