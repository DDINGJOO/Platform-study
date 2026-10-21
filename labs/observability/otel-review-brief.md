# OTel 심화판 독립 퇴고 브리핑

검토 대상은 `posts/CS/Observability/otel/`의 01–08 HTML이다. 기존 개요판 네 편의 검토 결과를 재사용하지 않는다. 분량 상한은 사용자 요청으로 해제했다. 길다는 이유만으로 줄이지 말고, 중복·빈약한 인과·설명되지 않은 전제·실제 오류를 구체적으로 지적한다.

최신 편집 요청: 상단 시리즈 박스는 현재 편을 포함한 최근 세 편만 표시한다(4편은 2·3·4편). 별도의 전체 목차는 제공하지 않는다. 긴 SHA·확인일·로컬 캡처 방식 고지는 도입·각 캡처에서 반복하지 않고 하단 참고 자료와 lab으로 옮긴다. root가 이 편집과 이미지 생성을 통합 중이므로 초기 지적의 줄 번호가 바뀔 수 있다. 이 변경을 누락이나 근거 삭제로 오판하지 말고 기술적 의미와 실제 주장 검토에 집중한다.

## 읽을 지침과 원자료

- `/Users/dding/orca/Platform-study/.agents/skills/blog-post-pipeline/SKILL.md` 및 `source-skill.md` 전체
- `/Users/dding/orca/Platform-study/labs/observability/otel-series-brief.md`
- 공개 upstream 원문, 각 편의 `source-manifest.json`, 공식 문서 링크
- 실제 실험은 `labs/observability/otel-runtime-probes/{RuntimeProbes.java,actual.txt,validation.json,README.md}`와 01편의 별도 API-only 실험이다.

책임은 설치된 `code-reviewer` 역할의 **독립 퇴고자**다. 글 작성자와 다르며 최종 원자료 감사자와도 다르다. 자식 에이전트를 만들거나 글·공통 자료를 수정하지 않는다. 자기 담당 관점만 읽기 전용으로 검토하고, 지정된 새 보고서에 결과를 기록한다. 공개 원자료만 사용하고 인증 전환·비공개 포크·조직 자료·발행은 다루지 않는다.

## 네 관점

1. 사실관계: 버전·구체 API·기본값·코드 경로·공식 문서·수치·실행 결과의 일치. 외부 사실은 기억이 아닌 1차 원문으로 확인한다.
2. 논리: 앞뒤 문장·다이어그램·캡션·편 간 주장 충돌, 전송 수락과 저장 완료 혼동, 대안 비교 계층의 불일치, 조건을 빠뜨린 보장.
3. 독자: 첫 등장 용어·약어·맥락 누락, 설명이 필요한 중간 단계, 비교의 선택 기준, 실제 코드 스크린샷과 텍스트의 연결. 초보 설명을 핑계로 중요한 조건을 없애지 않는다.
4. 문장: 해요체·시제·표기·목록 병렬성, 사실/해석/가정/실행의 구분, 비유·엠대시·근거 없는 경험 서술, 설명의 불필요한 반복. 고정된 템플릿의 글꼴·팔레트는 재론하지 않는다.

각 지적은 파일과 줄, 현재 문구, 문제가 되는 근거, 최소 수정안을 함께 적는다. 중요도와 확신도를 표시한다. 취향만 다른 제안은 수정 필수 오류로 세지 않는다. 문제가 없으면 검토 범위와 근거를 쓰고 0건이라고 명시한다.

## 알려진 구분

- Java 1.67.0 SDK는 processor가 없으면 noop tracer를 반환한다. SDK 생성과 기록·내보내기는 별도다.
- `SimpleSpanProcessor`는 호출 스레드에서 exporter를 호출하지만 비동기 결과를 기다리지 않는다. BSP의 `join(timeout)`은 취소가 아니며 flush 성공도 backend 영구 저장 확인이 아니다.
- Context 값 객체의 불변성·기본 저장소·Scope 복원·작업 캡처·헤더 전파는 서로 다른 경계다.
- TraceIdRatioBased 현행 사양 deprecated와 Java stable/incubator 지원을 구분한다. 2027-01-01은 일괄 삭제 일정이 아니다. Jaeger adaptive는 remote head이며 tail과 같지 않다.
- OTel도 pull Reader가 있고 Micrometer도 push Registry가 있다. Collector·Prometheus 서버·Agent mode·Alloy의 역할은 다르며 조합 가능하다.
- Java agent의 알려진 library boundary, 수동 업무 의미, Observation, eBPF의 관찰 범위를 구분한다. 07은 실제 agent를 실행한 글이 아니다.
- 한 span의 attribute 수와 metric의 attribute 조합 수, 개인정보 민감성은 다른 축이다. overflow 집계는 모든 초과 측정값의 무조건 폐기와 같지 않다.
- 기존 실험을 새 metrics/Collector/agent의 실행 근거로 쓰지 않는다. 성능 수치나 백엔드 내구성을 측정한 적은 없다.

수정은 root가 파일별로 담당하고, 재검은 수정된 주장과 주변 맥락을 확인한다. 라운드 결과와 독립 감사는 별도로 기록한다.
