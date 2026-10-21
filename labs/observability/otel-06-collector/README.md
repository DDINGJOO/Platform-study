# OTel 06: Collector 구성과 운영 경계의 원자료

이 디렉터리는 6편 HTML 초안의 공개 원자료와 확인 범위를 기록한다. Collector 배포나 부하·장애 주입 시험 결과를 담는 실험실이 아니다.

## 기준

- 원문 저장소: `open-telemetry/opentelemetry-collector`
- 태그: `v0.163.0`
- 고정 커밋: `5177a6a85ca3783068077e25aec6cebbe1d50d1f`
- 공식 웹 문서 확인일: 2026-10-21
- 글: `posts/CS/Observability/otel/06_6편 - Collector를 두면 무엇을 중앙에서 바꿀 수 있을까.html`

## 캡처와 소스 읽기

`source-manifest.json`은 raw 원문의 파일 전체 SHA-256과 줄 범위를 기록한다. 태그나 발췌 텍스트의 해시가 아니다. 작성자가 raw URL을 다시 받아 Python hashlib로 확인했으며 연구 노트와 일치했다.

- `service/pipelines/config.go` L50–66: receiver/processor/exporter 참조 목록 및 receiver/exporter 필수 검사. L68–79의 processor 중복 검사도 본문에서 읽는다.
- `service/internal/graph/graph.go` L267–290: receiver → capabilities → processor 순서 → fanout → exporter 연결. L76–141의 Build/createNodes, L216–250의 종류별 노드 생성, L294–327의 buildComponents, L406–507의 시작/종료 경로를 추가 확인한다.
- `exporter/exporterhelper/internal/queuebatch/queue_batch.go` L62–103: 큐 설정 전달, Offer 호출, 종료 경계.
- `exporter/exporterhelper/internal/base_exporter.go` L95–153: 큐 sender 연결, Send 경로와 retry → queue → wrapped exporter 종료 순서.
- 같은 커밋의 `exporter/exporterhelper/README.md`: wait_for_result, block_on_overflow, sizer, enqueue 실패와 retry 경계, persistent queue 설명.
- `exporter/otlpexporter/metadata.yaml`: 예제의 현재 type `otlp_grpc`, deprecated type `otlp`, trace/metric/log stable 및 core/contrib 배포판 포함을 확인했다.
- `exporter/exporterhelper/internal/queuebatch/config.go` L20–89: WaitForResult·BlockOnOverflow·Sizer 설정과 persistent queue 조합의 검사를 추가 확인했다. 본문은 wait_for_result의 모든 조합 지원을 주장하지 않는다.

루트 담당자가 두 PNG를 `posts/CS/Observability/otel/images/06/`에 생성했다. 원문 파일 해시, 줄 텍스트 동일성, 렌더링 잘림 검사를 통과했다고 전달받았다. PNG는 실제 고정 소스의 로컬 렌더링이며 동작 테스트 화면이 아니다.

## 주요 공식 문서

- https://opentelemetry.io/docs/collector/#when-to-use-a-collector
- https://opentelemetry.io/docs/collector/configuration/
- https://opentelemetry.io/docs/collector/deploy/agent/
- https://opentelemetry.io/docs/collector/deploy/gateway/
- https://opentelemetry.io/docs/collector/resiliency/
- https://opentelemetry.io/docs/collector/scaling/
- https://opentelemetry.io/docs/specs/otlp/
- https://opentelemetry.io/docs/security/handling-sensitive-data/
- https://prometheus.io/docs/prometheus/latest/prometheus_agent/
- https://grafana.com/docs/alloy/latest/introduction/
- https://grafana.com/docs/alloy/latest/introduction/how-alloy-works/
- https://grafana.com/docs/alloy/latest/troubleshoot/debug/

## 검증 범위와 한계

본문 YAML은 정의와 service pipeline 연결을 설명하는 가정이다. 운영 수치 권장, 전체 보안 설정, 해당 바이너리의 설정 validate 실행 또는 배포 성공을 주장하지 않는다. 예제 endpoint는 예약된 example.com 도메인이며 실제 주소·비밀값을 포함하지 않는다.

앱/agent/gateway/목적지 중단, 디스크 장애, tail sampling 재분배, 제품 간 성능·비용 비교는 실행하지 않았다. 구조 검사·일반 마스킹·CSS 동일성 검사는 로컬 정적 검증이며 독립 퇴고·원자료 감사·브라우저 검수와 구분한다.

2026-10-21 작성자 정적 검증 결과:

- `validate_html.py`: explicit HTML/SVG structure PASS.
- 일반 `mask-check.py`: HTML/manifest/README 3개 파일 모두 깨끗함. 조직별 비공개 마스킹 규칙을 검사했다는 뜻은 아니다.
- 템플릿 style 블록 바이트 동일성 PASS.
- 본문 p 텍스트 10,358자(공백·영문 포함, CSS·코드·용어 상자·캡션 제외), h2 10개, 용어 상자 7개, SVG 2개, PNG 참조 2개.
- 두 PNG 상대 경로 존재 확인 PASS. 본문 em dash·일본어 가나 검사 모두 0건.
- 실제 Collector 바이너리 validate·YAML 배포·동작 시험은 실행하지 않았음.
