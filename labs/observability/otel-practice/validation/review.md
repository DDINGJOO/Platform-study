# 독립 퇴고 기록

2026-10-23. 작성자는 `collector_lab`, `sampling_lab`, `dual_lab`, `privacy_lab`이며 아래 퇴고자와 분리했다. 네 퇴고자는 글 네 편을 모두 읽었고 원본을 수정하지 않았다. 수정은 각 파일의 작성자가 담당했다.

| 관점 | 독립 퇴고자 | 최초 판정 | 수정 후 |
|---|---|---|---|
| 사실관계 | `review_facts` | APPROVE, 지적 0건 | 추가 수정 요구 없음 |
| 논리 모순 | `review_logic` | APPROVE, 지적 0건 | 추가 수정 요구 없음 |
| 독자 시점 | `review_reader` | REQUEST CHANGES, MEDIUM 1건·LOW 1건 | APPROVE, 잔여 0건 |
| 문장 일관성 | `review_style` | APPROVE, 지적 0건 | 추가 수정 요구 없음 |

## 라운드 1: 지적 2건 → 반영 2건

1. **MEDIUM, 깨끗한 checkout에서 재캡처 도구 누락.** 네 `capture.py`가 기존 untracked `.codex/skills/blog-post-pipeline/assets` 링크에 의존했다. 실제로 추적되는 `.claude/skills/blog-post-pipeline/assets`를 참조하도록 네 스크립트와 README 명령을 수정했다. 공통 검증기의 template 경로도 같은 이유로 tracked `.claude` 원본을 사용하도록 수정했다. HTML 검사 스크립트 자체는 tracked `.codex` 경로를 유지한다.
2. **LOW, 2편 요청별 원자료 안내 오류.** trace ID와 SDK 선택 여부를 보라는 명령이 집계 `summary.json`을 출력했다. 요청별 `trace_id`·`sdk_sampled`가 있는 `out/requests.json`으로 수정했다.

독자 퇴고자는 변경 범위를 다시 읽고, 도구 파일의 tracked 여부와 요청 182개의 해당 필드 존재, Python 구문을 확인했다. 재검 결과 잔여 지적은 0건이다. 캡처·원실험을 다시 만들어 지적을 덮지 않았다.

별도 브라우저 검사에서는 3편의 긴 inline code가 모바일 390px에서 문서 폭을 411px로 늘리는 문제를 발견했다. 해당 글의 inline code에 줄바꿈을 허용하고 템플릿 CSS는 유지했다. 최종 레이아웃 결과는 `checks.json`에 기록한다.

## 판정 근거

- 사실관계: 1편 수락·거절·저장·중복 수치와 실제 Tempo의 173개 고유 스팬을 재조회했다. 2편 요청 182개 및 저장 41개 트레이스·82개 스팬을 ID·부모 관계로 대조했다. 3편 9개 트레이스의 3/4/7 스팬·scope·HTTP 중첩·MDC를 재검했다. 4편 12개 트레이스·36개 스팬의 연결과 모드별 표식 수치를 대조했다. 고정 버전 queue/latency/Logback/baggage 공개 소스를 읽었다.
- 논리: 수락과 생성의 분모, 서로 다른 head sampling ID의 비대응 비교, 지연 전송과 실행 시간, 총 스팬과 의미 중복, 신규 텔레메트리와 원본 콘솔·HTTP baggage·기존 데이터의 범위를 점검했다. 확인한 원자료와 모순되는 결론을 찾지 못했다.
- 독자: 네 편, 공통·개별 README 다섯 개와 새 ROADMAP을 읽고 질문·용어·재현·트러블슈팅·상대 링크를 점검했다. 위 두 건을 반영했다.
- 문장: 지정한 기존 실습 글과 해요체·시제·용어·강조·비유·엠대시·장별 반복을 대조했다. 수정할 비자명한 불일치를 찾지 못했다.

이 보고서는 퇴고 결과다. 별도 감사자 `final_audit`의 원자료 감사와 형식·마스킹·브라우저 검증을 대신하지 않는다. LSP 도구는 제공되지 않아 실행하지 않았으며 Python AST, 실제 실행기의 단언, Compose 설정과 브라우저 검증을 사용한다.
