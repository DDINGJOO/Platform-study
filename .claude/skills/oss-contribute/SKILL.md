---
name: oss-contribute
description: 오픈소스 기여를 처음부터 끝까지 관리한다. 후보 찾기, 중복 확인, main 재현, 수정, 되돌림 실패 검증, 저장소 관례에 맞춘 커밋·PR 초안, 승인 후 DDINGJOO 로 푸시, PR 추적과 핑, 기록 아카이빙, 개인 노션 「오픈소스 PR」 DB 갱신, 머지 뒤 회고 글·경력기술서 재료로 넘기기. "오픈소스 기여", "컨트리뷰트", "PR 체크", "pr 체크", "리뷰 안 와", "핑", "다음 기여" 요청에 쓴다.
---

# 오픈소스 기여 관리

기여 한 건은 **재현 → 수정 → 증명 → 제출 → 추적 → 기록** 이다. 어느 단계든 빠지면
나중에 회고 글도, 경력기술서도, 리뷰어 질문에 대한 답도 쓸 수 없다.

## 절대 규칙

- **푸시·PR·이슈·코멘트는 사람이 승인한 뒤에만 한다.** 초안을 보여 주고 멈춘다. 한국어 번역본을 같이 보여 준다(사용자가 원문을 바로 읽지 않는다).
- **계정은 DDINGJOO 다.** `gh auth switch` 를 하지 않는다(활성 계정이 바뀌면 다른 작업이 깨진다). 아래처럼 그 명령에만 토큰을 건다.
  ```bash
  GH_TOKEN=$(gh auth token --user DDINGJOO) gh pr create ...
  git -c credential.helper= -c credential.helper='!f() { test "$1" = get && { echo username=DDINGJOO; echo "password=$(gh auth token --user DDINGJOO)"; }; }; f' push origin HEAD
  ```
  커밋 작성자: `DDINGJOO <173995233+DDINGJOO@users.noreply.github.com>`
- **AI 흔적.** 커밋·PR·코멘트에 도구 흔적을 남기지 않는 것이 기본이다. 저장소가 생성형 AI 사용 고지를 요구하면(`references/repos.md` 에 표시) 그 저장소 규칙을 따르되, PR 전에 사람에게 다시 확인한다.
- **이슈 양식이 있는 저장소에서는 API 로 이슈를 만들지 않는다.** 양식 라벨이 빠진다(Keycloak #54050, OpenTelemetry #20846 두 번 반복). 양식 칸별 내용을 사용자에게 주고 웹에서 열게 한다.
- **수정 전 코드에서 실패하지 않는 테스트는 증명이 아니다.** 본 코드만 되돌려 실패하는 것까지 확인하고 기록한다.
- **업무 정보를 섞지 않는다.** 회사명·내부 서비스명·업무 저장소를 이슈·PR·기록 어디에도 쓰지 않는다.

## 1. 후보 찾기와 중복 확인

- 출처: 실제로 쓰는 라이브러리를 돌려 보다 발견, 이슈 목록(`good first issue`, `help wanted`), 코드 읽기, 리뷰어가 남긴 후속 항목.
- 착수 전에 반드시 확인한다.
  ```bash
  GH_TOKEN=$(gh auth token --user DDINGJOO) gh search issues -R <owner/repo> "<핵심어>" --state all
  GH_TOKEN=... gh search prs   -R <owner/repo> "<핵심어>" --state all
  ```
  열린 PR 이 이미 있으면 멈추고 보고한다. 메인테이너가 거절한 방향이면 기록만 남긴다.
- `CONTRIBUTING.md`, `AGENTS.md`, PR 템플릿, 이슈 템플릿을 읽고 `references/repos.md` 에 없으면 추가한다.
- **이슈 연결이 필요한 저장소인지 먼저 본다.** 이슈 없이 PR 만 올리면 라벨·담당 팀이 안 붙어 리뷰가 오지 않는 저장소가 있다(Keycloak). 템플릿이 있으면 이슈는 웹 양식으로 연다(API 로 만들면 템플릿 라벨이 빠진다).

## 2. 재현 (main 기준)

- 클론은 스크래치패드에 `--filter=blob:none`. 끝나면 지운다.
- **릴리스가 아니라 main 에서 재현한다.** 메이저 개발 중에는 이름·모듈이 바뀐다(OpenTelemetry 3.0).
- 메모리 8GB. Maven `MAVEN_OPTS=-Xmx2g`, Gradle `--no-daemon --max-workers=2 -Dorg.gradle.jvmargs=-Xmx2g`. 해당 모듈·해당 테스트만. 무거운 빌드는 동시에 둘 이상 돌리지 않는다.
- 재현이 기본 의존성에서 안 되면 최신 의존성(`-PtestLatestDeps=true` 등)으로도 본다. 버그가 특정 버전에서만 나타날 수 있다.

## 3. 수정과 증명

1. 실패하는 테스트를 먼저 쓴다(수정 전 실패 로그 보관).
2. 고친다. 공개 API·시맨틱 컨벤션·하위 호환에 영향이 있으면 근거 문서를 `analysis.md` 에 적는다.
3. 수정 후 통과, **본 코드만 되돌리면 실패**, 관련 모듈 테스트 통과, 포매터 적용.
4. 커밋은 저장소 관례대로(`references/repos.md`). 브랜치는 포크 저장소에.

## 4. 제출

- PR 본문 초안을 `pr-draft.md` 로 쓴다. 저장소 템플릿·관례를 따르고, 재현 방법과 되돌림 실패 결과를 짧게 넣는다.
- 영문 초안 + 한국어 번역을 사람에게 보여 주고 승인받는다.
- 올린 뒤 `pr-draft.md` 맨 위에 PR 링크를 적고, 노션 DB 를 동기화한다.

## 5. 추적

```bash
python3 .claude/skills/oss-contribute/scripts/oss_tracker.py sync    # 개인 노션 「오픈소스 PR」 갱신
python3 .claude/skills/oss-contribute/scripts/oss_tracker.py stale   # 리뷰 없이 5일 지난 열린 PR
```

"PR 체크" 요청에는 sync 결과에서 바뀐 것만 보고한다(새 리뷰, 상태 변화, 머지). 바뀐 것이 없으면 그렇게 말한다.

**핑 기준**: 마지막 활동이 내 것이고 5영업일 이상 반응이 없으면 핑 초안을 쓴다.
- 이전에 내 PR 을 리뷰한 사람이 있으면 그 사람을 부른다. 없으면 CODEOWNERS·영역 담당을 찾는다.
- PR 여러 개가 한 이슈에 묶여 있으면 이슈에 한 번만 남긴다(알림을 여러 번 보내지 않는다).
- CI 실패가 내 변경과 무관하면, 같은 시기 다른 PR 의 같은 잡 실패와 비교해 근거를 붙인다.
- 30일 무반응이면 프로필에서 내리고 노션에서만 관리한다.

## 6. 기록 (아카이빙)

원본은 Platform-study `labs/open-source-contribute/<프로젝트>/<작업>/` 에 둔다. 프로젝트 폴더의 `README.md` 가 색인이다.

| 파일 | 내용 |
|---|---|
| `journal.md` | 시간순 일지. 의심한 것, 실행한 명령, 결과, **틀린 판단과 바꾼 이유**. 지우지 않는다 |
| `repro.md` | 수정 전 실패 · 수정 후 통과 · 되돌림 실패. 명령과 개수, 걸린 시간 |
| `analysis.md` | 원인 위치(파일:줄, 커밋), 라이브러리 동작 근거, 스펙 근거 링크 |
| `pr-draft.md` · `patch.diff` | PR 초안, 최종 diff |
| `logs/` | 원본 증거. 빌드 출력, JUnit XML |
| (이미지 없음) | 스크린샷은 만들지 않는다(2026-10-22 결정). 증거는 `logs/` 의 빌드 출력과 JUnit XML 이고, 글에는 실패 메시지를 코드 블록으로 옮긴다 |

리뷰가 오면 리뷰 내용과 대응(수용·반박·근거)을 `journal.md` 에 이어 쓴다.
확인하지 않은 것은 "확인 안 함" 으로 적는다. 나중에 "어떻게 확인했냐" 에 답할 수 없는 문장을 남기지 않는다.

**공개 저장소에 커밋할 때 거른다.** PR 원장 JSON(봇·도구 이름이 그대로 있다), 로컬 경로가 찍힌 빌드 로그, 작업 지시서는 커밋하지 않는다. `mask-check.py --extra ~/.config/blog-mask.txt` 를 통과시킨다.

## 7. 노션 (개인 노션만)

- 「프로젝트 관리」의 「오픈소스 기여」 상위 행 + 저장소별 하위 행. 새 저장소에 기여하면 하위 행을 만들고 `scripts/oss_tracker.py` 의 `PROJECT_OF` 에 추가한다(허용 목록이라 추가하지 않으면 추적되지 않는다).
- 「오픈소스 PR」 DB: PR·이슈 한 건이 한 행. 상태·날짜·마지막 활동은 스크립트가, `다음 행동`·`기록`·`회고 글` 은 사람이 쓴다.
- 하위 행 `F/U` 에는 날짜와 함께 덧붙인다. 머지되면 상태를 확인하고 Done 여부를 묻는다.
- 회사 노션에는 쓰지 않는다.

## 8. 머지 뒤

- 회고 글: `posts/open-source-contribute/<프로젝트>/` (tistory-sketch-post 형식, 카테고리 `Open Source/<프로젝트>`). 근거는 이 폴더의 기록과 재현 결과만 쓴다. "다시 한다면" 같은 가정형은 쓰지 않는다.
- 경력기술서 재료: `project-brief` 스킬로 「오픈소스 기여」 행의 하위 페이지를 갱신한다.
- GitHub 프로필 README(DDINGJOO/DDINGJOO)의 표에서 In Review → Merged 로 옮긴다.
