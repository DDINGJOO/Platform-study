# OTel 심화판 독립 논리 퇴고

- 검토일: 2026-10-21
- 역할: 작성자·최종 원자료 감사자와 분리된 논리 검토자
- 판정: **APPROVE, 논리 관점의 수정 필수 지적 0건**
- 심각도: Critical 0 / High 0 / Medium 0 / Low 0
- 확신도: 검토한 본문·그림·캡션 사이의 일관성은 높음. 실제 배포 환경의 동작을 보증하는 판정은 아님.

## 검토 범위

`posts/CS/Observability/otel/`의 01–08 HTML 전체를 읽고, 인라인 SVG의 제목·설명·도형 문구와 본문·캡션을 교차 대조했다. 코드 이미지 6개는 실제 PNG도 열어 확인했다. 설치된 code-reviewer 역할, 리뷰 브리프, blog-post-pipeline과 tistory-sketch-post의 지침 및 지정 참고자료를 적용했다. 글은 수정하지 않았다.

길이 자체는 결함으로 취급하지 않았다. 상단에 현재 편을 포함한 최근 최대 3편만 표시하고 전체 목록은 별도로 두지 않는 최신 요청, 원문 출처 고지의 하단 축약 작업도 결함으로 세지 않았다.

아래 위치는 검토 당시 HTML 줄 번호이며 병행 편집으로 이동할 수 있다. 각 행은 결함이 아니라 확인한 논리 경계다.

| 파일·위치 | 확인한 문구와 경계 | 결과 |
| --- | --- | --- |
| `01_1편 - API와 SDK는 왜 나뉘어 있을까.html:57`, `:66`, `:76` | “API가 있으면 반드시 기록하는 것은 아니에요”, “전송까지 보장하지 않아요”. API no-op, SDK의 무프로세서 최적화, 기록 스팬, 프로세서 관찰, exporter 호출, 백엔드 저장을 분리한다. | 충돌 없음 |
| `02_2편 - 스레드가 바뀌면 컨텍스트는 어떻게 이어질까.html:60`, `:87`, `:122`, `:200` | “Scope를 닫는 것은 초기화가 아니라 복원”. 불변 Context와 현재 실행의 저장소, 캡처와 활성화, 작업 재사용과 제출 시 래핑, 로컬 연결과 원격 전파가 구분된다. 잘못된 Scope 닫기 순서의 예도 복원 경로와 일치한다. | 충돌 없음 |
| `03_3편 - 전송이 밀리면 스팬은 어디서 사라질까.html:68`, `:80`, `:171`, `:207` | “큐에 넣지 못한 스팬은 다시 시도하지 않아요”. SDK 배치 큐의 동작으로 범위가 한정되며 exporter 내부 재시도나 Collector 큐와 혼동하지 않는다. join의 대기는 취소가 아니고, flush 결과도 저장 확인과 분리한다. | 충돌 없음 |
| `04_4편 - 샘플링하면 무엇이 남고 무엇이 빠질까.html:127`, `:151`, `:164`, `:216` | “기록, sampled, export는 서로 다른 단계”. RECORD_ONLY의 기록 상태와 프로세서의 전송 정책을 분리한다. 희귀 실패 확률에는 독립성·무작위성·무손실 가정이 있고, tail의 판단 범위와 선택 편향을 함께 설명한다. | 충돌 없음 |
| `05_5편 - 메트릭은 어디서 집계되고 누가 가져갈까.html:61`, `:86`, `:142`, `:154`, `:196` | View의 집계 전 속성 필터, Reader별 상태, 수집과 전송의 분리. SDK Reader 독립성과 애플리케이션 콜백의 파괴적 읽기를 별도로 다룬다. cumulative의 총량 회복 조건을 같은 상태의 존속·후속 도착으로 제한한다. | 충돌 없음 |
| `06_6편 - Collector를 두면 무엇을 중앙에서 바꿀 수 있을까.html:96`, `:144`, `:162`, `:191`, `:212` | “받았다는 응답은 어디까지의 성공일까요?” 큐 수락, 영속 큐 도달, 백엔드 저장을 분리한다. 파이프라인별 processor 인스턴스와 설정 순서, 앞단 batch의 손실 가능성, 이미 전송된 민감정보의 경계가 그림과 맞는다. | 충돌 없음 |
| `07_7편 - 자동 계측은 애플리케이션을 어디까지 알 수 있을까.html:72`, `:91`, `:170`, `:185`, `:221` | “Scope와 Span의 종료”. 동기 send와 Future 완료 콜백의 수명을 구분하고 즉시 예외 경로도 설명한다. 라이브러리 경계 관찰과 업무 의미, OTel Context와 Observation.Context, agent·eBPF의 관찰 조건을 섞지 않는다. | 충돌 없음 |
| `08_8편 - 같은 요청을 같은 이름으로 기록하려면 무엇이 필요할까.html:37`, `:88`, `:98`, `:134`, `:159` | OTLP 형식과 의미 규칙, 스팬 속성 수와 시계열 수, overflow의 숫자 보존과 원래 조합 구분의 상실을 분리한다. 집계 키 필터와 exemplar 등 다른 경로, 카디널리티와 민감성도 구분한다. | 충돌 없음 |

실제 결함이 확인되지 않아 결함별 문구·심각도·확신도·최소 수정안 항목은 생성하지 않았다. 표현 취향이나 더 긴 설명을 위한 선택적 보충을 필수 수정으로 만들지 않았다.

## 편 사이의 핵심 대조

1. **01 ↔ 04:** API no-op이 부모 문맥을 유지할 수 있다는 설명과, SDK DROP이 새 SpanContext를 만들고 비기록 스팬을 반환한다는 설명은 대상 경로가 다르다. 둘을 같은 비기록 생성 방식으로 일반화하지 않는다.
2. **01 ↔ 03 ↔ 06:** 생성·종료·프로세서 관찰·exporter 호출·큐 수락·백엔드 저장을 연속된 동일 보장으로 취급하지 않는다. Collector를 추가해도 SDK에서 기록하지 않았거나 이미 버린 데이터를 되살리지 못한다는 경계가 유지된다.
3. **02 ↔ 07:** Scope 복원과 Span 종료는 다른 작업이다. 비동기 반환 시 Scope를 닫고 저장한 Context로 완료 콜백에서 계측을 끝내는 07의 설명은 02의 실행 문맥 모델과 일치한다.
4. **05 ↔ 08:** View가 집계 상태 생성 전 키를 줄일 수 있다는 설명은 “그 속성이 모든 전송 경로에서 삭제된다”는 주장으로 확대되지 않는다. 08의 exemplar 주의사항 및 overflow가 원래 속성 조합을 보존하지 못한다는 설명과 양립한다.
5. **비교 계층:** Micrometer API·Registry와 Prometheus 서버, SDK head 선택과 Collector tail 선택, OTel과 Jaeger, Collector와 Alloy·Prometheus Agent를 제품 이름만으로 일대일 대체재라고 비교하지 않는다. 책임·위치·입력·출력의 기준이 본문에 제시되어 있다.

## 근거 대조와 검증

논리 결론에 영향을 주는 경계는 다음 공개 원자료와 직접 대조했다.

- [Java v1.67.0 SdkTracerProvider](https://github.com/open-telemetry/opentelemetry-java/blob/b4b3a1b354425c3f1411173c0e48cb24a1cba224/sdk/trace/src/main/java/io/opentelemetry/sdk/trace/SdkTracerProvider.java#L98-L107): SpanProcessor가 없는 Provider의 no-op 경로.
- [Java v1.67.0 BatchSpanProcessor](https://github.com/open-telemetry/opentelemetry-java/blob/b4b3a1b354425c3f1411173c0e48cb24a1cba224/sdk/trace/src/main/java/io/opentelemetry/sdk/trace/export/BatchSpanProcessor.java#L280-L373): flush 완료 경로, exporter 결과 대기 및 finally의 batch 초기화.
- [Java v1.67.0 CumulativeSynchronousMetricStorage](https://github.com/open-telemetry/opentelemetry-java/blob/b4b3a1b354425c3f1411173c0e48cb24a1cba224/sdk/metrics/src/main/java/io/opentelemetry/sdk/metrics/internal/state/CumulativeSynchronousMetricStorage.java#L45-L149): 기록 시 원래 속성 전달, 집계 키 필터, 기존 handle과 overflow 처리.
- [Instrumentation v2.32.0 HttpClientInstrumentation](https://github.com/open-telemetry/opentelemetry-java-instrumentation/blob/1b8644f8eb11d90295b1c313391aa84edeeec6e2/instrumentation/java-http-client/javaagent/src/main/java/io/opentelemetry/javaagent/instrumentation/javahttpclient/HttpClientInstrumentation.java#L138-L167): 비동기 Scope 종료, 예외 경로, Future 완료 연결.
- [OTel Metrics SDK 사양](https://opentelemetry.io/docs/specs/otel/metrics/sdk/): cardinality overflow에 포함되는 측정의 집계 보존과 원래 속성 구분의 차이, 수집과 비동기 콜백의 관계.
- [OTLP 사양](https://opentelemetry.io/docs/specs/otlp/): 한 client/server 구간의 응답과 다중 구간 end-to-end 보장의 구분.
- [Micrometer Observation 구성요소](https://docs.micrometer.io/micrometer/reference/observation/components.html): 변경 가능한 Observation.Context 및 기본 Meter handler의 태그 처리 범위.
- [OTel 민감정보 처리 문서](https://opentelemetry.io/docs/security/handling-sensitive-data/): 수집 최소화와 후처리의 경계, 예측 가능한 값에 대한 해시의 한계.

실제 실행한 정적 검증:

```text
python3 .agents/skills/tistory-sketch-post/scripts/validate_html.py posts/CS/Observability/otel/*.html
결과: 8편 모두 valid explicit HTML/SVG structure
```

이 결과는 명시적 HTML/SVG 구조 검증이며 브라우저 레이아웃이나 기술 주장 전체의 증명은 아니다. 애플리케이션 코드 변경이 없는 본 검토에서 LSP/typecheck는 적용 대상이 아니다.

`otel-runtime-probes/README.md`, `actual.txt`, `validation.json`의 저장된 실행 기록을 읽고 본문의 인용 범위와 비교했다. API/SDK·Context·Batch·Sampling 네 probe가 각각 5회 통과했다는 기록은 본문과 맞는다. 검토자가 이 실행을 새로 반복했다고 주장하지 않는다. 메모리 exporter 수신과 네트워크 전송·백엔드 저장을 혼동하지 않으며, 앞 네 probe를 메트릭·Collector·Java agent의 실행 검증으로 확대하지 않는다.

PNG 실물 확인은 다음 6개로 제한했다. 모두 파일명·코드 행·강조 구간이 주변 본문과 일치했다.

- `images/03/batch-export.png`
- `images/04/parent-decision.png`
- `images/05/metric-reader.png`
- `images/06/pipeline-graph.png`
- `images/07/httpclient-scope.png`
- `images/08/metric-cardinality.png`

## 남은 검증 경계

논리 퇴고는 완료했다. 별도 최종 원자료 감사와 통합자의 최종 렌더링·경로 검증을 대신하지 않는다. 이 보고서는 모든 이미지의 시각 검수, Collector 실행, 실제 서비스 간 전파, 네트워크·백엔드 영속성, 성능 수치 또는 배포 호환성을 검증했다는 뜻이 아니다.
