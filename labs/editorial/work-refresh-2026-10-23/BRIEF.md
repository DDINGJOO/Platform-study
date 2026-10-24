# 모든 작성자·검토자의 공통 기준

루트: `/Users/dding/orca/Platform-study`. 전체 목록과 배정 번호는 이 폴더 `baseline.json`의 `articles`에 있다. 사용자는 Work 112편 전부의 AI처럼 보이는 문체와 누락 태그를 수정하고 기존 블로그에 올리도록 요청했다. 한 글마다 작성 에이전트를 별도로 배정한다. 작성자는 배정된 HTML 한 개와 `writers/번호.json`만 편집한다. 다른 글·공통 파일·manifest·스킬·허용 목록·원본 저장소는 수정하지 않는다. 재위임하지 않는다.

## 먼저 읽기

- `/Users/dding/.codex/agents/executor.toml`의 설치된 executor 역할(작성자), 검토자는 설치된 code-reviewer/verifier 역할
- `/Users/dding/orca/Platform-study/.codex/skills/blog-post-pipeline/SKILL.md`와 연결된 source-skill.md
- `/Users/dding/orca/Platform-study/.codex/skills/tistory-sketch-post/SKILL.md`와 연결된 source-skill.md
- `/Users/dding/orca/Platform-study/.codex/skills/tistory-sketch-post/references/easy-read-guide.md`
- `/Users/dding/orca/Platform-study/.codex/skills/tistory-sketch-post/references/svg-sketch-guide.md`
- `/Users/dding/orca/Platform-study/.codex/skills/tistory-sketch-post/assets/template.html`
- 톤 참고: `/Users/dding/orca/Platform-study/posts/open-source-contribute/spring-cloud-config/02_2편 - 매칭은 느슨하게, lastRefresh는 그대로 둔 이유.html`. 이 글을 수정하거나 문장을 복사하지 않는다. 아래 사용자 요구가 기존 스킬의 과장된 훅·교훈 예시보다 우선한다.

## 목표 문체

실무자가 동료에게 문제와 선택을 설명하는 자연스러운 한국어 해요체다. 문장을 무조건 짧게 끊거나 모든 글을 같은 틀로 바꾸지 않는다. 앞뒤 원인이 이어지는 문단을 쓴다. 당시 무엇을 확인했고, 왜 고쳤고, 어디까지 확인했는지가 보이면 된다.

- `거짓말했다`, `네 발 얻어맞았다`, `지뢰`, `박제`, `도장`, `지도`, `문을 닫다`, `돈을 먹다` 같은 불필요한 비유·의인화·과장 제거.
- `질문은 하나입니다`, `진짜 문제는 따로`, `핵심은 X가 아니라 Y`, `오늘의 교훈`, `규칙은 하나`처럼 반복되는 수사와 매번 등장하는 반전·명언을 문맥에 맞게 다시 쓴다. 실제 잘못과 수정 이유는 남긴다.
- `이 글은 ... 기록이에요` 같은 집필 설명, 매 절 끝 같은 결론 반복, 강제적인 번호 나열, 과도한 굵은 글씨·형광펜을 줄인다. 표·단계·비교가 유용하면 유지한다.
- 인용·코드 밖 엠대시는 없애되 문장별로 자연스럽게 고친다. 임의 감정·대화·새벽 장애·성과·원인·수치·완료 시점을 만들지 않는다.
- 글을 읽고 직접 다듬는다. 기계적인 일괄 치환만으로 완료하지 않는다. 전문 용어는 필요한 자리에서 짧게 풀되 새 사실을 추가하지 않는다.
- 도입·본문·절 제목·콜아웃·캡션·요약을 모두 읽는다. 마지막 요약은 해당 글의 결정과 검증 범위를 담백하게 적고 명언으로 끝내지 않는다.

예: `이름은 다섯 번 거짓말했다` → 실제 내용이 이름과 소유권 판별의 차이라면 `리소스 이름만으로 삭제 대상을 정하지 않기`. `안내문이 거짓말을 했다` → `라벨을 붙여 재실행해도 이전 이벤트의 라벨을 읽어 실패했어요`.

## 보존과 제목·목차

기존 파일 경로·편 번호·기술적 인과·실행 여부·과거 날짜·수치·버전·제약을 유지한다. `.obsv-code`, `<pre>`, 인라인 `<code>`, 이미지, 외부 href, CSS는 원문 그대로 보존한다. 코드 주석에 과장된 표현이 있어도 인용으로 남긴다. SVG는 개수·속성·도형·좌표·식별자를 그대로 두고 **텍스트 라벨만** 비유를 없애는 정도로 수정할 수 있다. CSS를 수정하지 않는다.

수치 보존은 실제 측정값·자원 개수·기간을 뜻한다. `두 파일을 보면 5초 만에 알 수 있다`처럼 근거 없는 속도 과장은 측정치로 취급하지 않고 담백한 문장으로 바꾼다. 원자료 상태는 변경 개수만 보고하고 비공개 경로·값을 보고서에 나열하지 않는다.

보고서의 ADR 근거는 고정 커밋·ADR 번호·문서 제목 또는 슬러그로 적는다. 현재 자료 파일명의 12자리 날짜+일련번호는 불필요하므로 `docs/adr/*-문서슬러그.md`처럼 패턴으로 줄일 수 있다. 날짜형 문서 번호를 실제 계정 ID로 오인해 `{계정ID}`로 쓰지 않는다.

시리즈 박스는 작성자가 편집하지 않는다. 모든 글의 제목이 모인 뒤 리더가 같은 형식으로 `현재 편 + 직전 두 편`을 만들고 실제 기존 글 링크를 연결한다. 존재하지 않는 편을 추가하지 않는다.

파일명을 바꾸지 않는다. 표시 제목은 `writers/번호.json`에 `suggested_subject`로 제안한다. 접두어·편 번호를 제외한 구체적인 제목 한 개이며 그대로 유지해도 될 만큼 이미 정확하면 기존 제목을 둔다. 리더가 `tistory-series.json` titles에 통합하므로 글마다 임의로 공통 설정을 편집하지 않는다.

## 태그

`<!-- tags: ... -->`가 없으면 추가하고, 있으면 글 내용과 맞는지 검토한다. 공통 태그는 `baseline.json`에 기록되어 있다. 공통 태그와 중복하지 않는 글별 검색어 3~4개를 선정한다(총합 열 개 이하). 실제 다룬 도구·에러·설정·개념을 쓰며 회사명·내부 약어·막연한 `개발`, `공부`, `회고`를 추가하지 않는다. lead 주석은 기존 사실로 80~150자로 다듬는다.

## 근거와 개인정보

자료 저장소는 읽기 전용이다. 글 쓰려고 저장소 파일을 수정·커밋·푸시하지 않는다. `/Users/dding/orca/platform-IaC`는 최초 조회 이후 외부 작업으로 변경된 파일이 생겼다. 각자 조회 시점의 상태를 보존하고 그 변경을 정리하거나 되돌리지 않는다. IaC 설명을 바꿀 때 필요하면 기존 코드·ADR·git 이력을 직접 읽되 최신 코드로 당시 실행을 바꾸지 않는다. 원자료의 현재 워킹트리보다 글이 인용한 당시 고정 커밋을 우선한다. 그 외 실습은 이 저장소 labs의 기존 원자료를 읽는다. 이번 작업은 문체 편집이므로 새 API·기술 주장·상태 업데이트를 만들지 않는다. 원자료로 확인하지 못한 기존 주장이 있으면 보고하고 독단적으로 확정하지 않는다.

기존 글의 절대 회사 금액도 발행 전에 비율·배수로 정리한다. 보호 코드에 금액이 남아 있으면 작성자는 실제 값을 복사하지 말고 위치만 보고한다. 리더가 해당 코드의 변경 전후 정확한 해시를 cost-redactions.json에 기록하고 별도 독립 검수를 받는다. 이 예외는 기록된 금액 비교 블록에만 적용되며 실행 코드·CSS·기하 구조의 보존을 완화하지 않는다.

조직명·사람·내부 저장소·실제 계정·비공개 URL·전역 고유 자원명·절대 금액을 추가하지 않는다. 자리표시자와 기존 마스킹을 보존한다. 미조치 취약점·비공개 보안 제보를 쓰지 않는다. 실제 원본 값을 보고서·채팅에도 복사하지 않는다. `~/.config/blog-mask.txt`는 저장소 밖에서 검사에만 사용한다.

## 완료 조건

배정 글 전체를 읽고 편집한 뒤 실제로 구조 검사와 조직 마스킹을 실행한다:

```sh
python3 .codex/skills/tistory-sketch-post/scripts/validate_html.py '배정 파일'
python3 .claude/skills/blog-post-pipeline/assets/mask-check.py '배정 파일' --extra /Users/dding/.config/blog-mask.txt
python3 labs/editorial/work-refresh-2026-10-23/validate.py --only 번호
```

`writers/번호.json`에는 `number`, `path`, `suggested_subject`, `specific_tags`, `changes`(실제 대표 수정 2~4개), `validation`, `source_checks`, `unresolved`를 기록한다. 지적된 것 외의 원자료 모순을 찾으면 플래그한다. 자신의 글을 승인하거나 독립 감사했다고 표현하지 않는다. 커밋·push·Tistory 작업은 리더가 담당한다.
