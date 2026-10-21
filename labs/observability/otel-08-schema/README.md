# 08: 데이터 의미와 제한을 구분해 읽기

공개 공식 문서와 Java v1.67.0의 고정 소스를 읽어 작성한 로컬 초안이다. 조직 자료나 비공개 보안 제보는 사용하지 않았다. Collector나 Prometheus를 실행한 결과, 처리량·비용 실측을 주장하지 않는다.

## 코드 캡처

- 저장소: `open-telemetry/opentelemetry-java`
- 릴리스: `v1.67.0`
- 커밋: `b4b3a1b354425c3f1411173c0e48cb24a1cba224`
- `source-manifest.json`에 전체 원문 SHA-256, 줄 범위, 불변 permalink를 기록했다.
- 원문은 수정하지 않고 공통 `../otel-01-api-sdk/capture.py`로 렌더링한다. 생성은 통합 담당자가 실행한다.
- 대상: `posts/CS/Observability/otel/images/08/{span-limits,metric-cardinality}.png`.

## 읽은 호출 경로

1. `SdkSpan.setAttribute()` L333–350 → `AttributesMap.create()`에 `SpanLimits`의 개수·길이를 전달 → `AttributesMap.put()`에 저장한다. 제한 적용은 의미·개인정보 판정과 다르다.
2. `SynchronousMetricStorage.create()` L47–65 → 등록한 View의 attribute filter·cardinality limit를 저장소에 전달한다.
3. `DefaultSynchronousMetricStorage.create()` L65–85 → Reader의 temporality에 따라 누적/델타 저장소를 고른다. 생성자 L42–62는 overflow용 한 슬롯을 예약한다.
4. `CumulativeSynchronousMetricStorage.doRecordLong/Double()` L50–57 → `getAggregatorHandle()` L96–120에서 집계용 속성 필터, 기존 조합 조회, 한도 초과 시 overflow 선택 → 원래 속성을 handle에 전달한다.
5. `collect()` L124–156 → 각 handle의 집계값과 Resource·InstrumentationScopeInfo를 MetricData에 포함한다.

주의: 누적 동기 저장소 한 구현 경로를 모든 비동기/델타 계측 동작으로 일반화하지 않는다. map size 검사와 putIfAbsent가 분리돼 있으므로 동시성 경계까지 정확히 한 번의 순차 삽입처럼 서술하지 않는다. 원래 속성을 exemplar 후보에 제공하는 경로 때문에 View 필터를 개인정보 삭제 보장으로 표현하지 않는다.

## 공식 문서 (2026-10-21 확인)

- [Semantic conventions](https://opentelemetry.io/docs/concepts/semantic-conventions/)
- [OTLP](https://opentelemetry.io/docs/specs/otlp/)
- [Resources](https://opentelemetry.io/docs/concepts/resources/)
- [Instrumentation scope](https://opentelemetry.io/docs/concepts/instrumentation-scope/)
- [HTTP migration](https://opentelemetry.io/docs/specs/semconv/non-normative/http-migration/)
- [HTTP spans](https://opentelemetry.io/docs/specs/semconv/http/http-spans/)
- [Metrics SDK: cardinality](https://opentelemetry.io/docs/specs/otel/metrics/sdk/#cardinality-limits)
- [Metrics SDK: exemplars](https://opentelemetry.io/docs/specs/otel/metrics/sdk/#exemplar)
- [Micrometer Observation components](https://docs.micrometer.io/micrometer/reference/observation/components.html) (표시 버전 1.17.1)
- [Prometheus data model](https://prometheus.io/docs/concepts/data_model/)
- [Prometheus naming](https://prometheus.io/docs/practices/naming/)
- [Handling sensitive data](https://opentelemetry.io/docs/security/handling-sensitive-data/)

## 검증 범위

작성자는 HTML 구조·일반 마스킹 검사 결과만 보고한다. 독립 퇴고·원자료 감사와 PNG 렌더링·브라우저 검사는 통합 단계의 별도 작업이다. 본문의 계약 테스트 항목과 숫자 예시는 설계 제안·설명용 가정이며 실행 로그가 아니다.
