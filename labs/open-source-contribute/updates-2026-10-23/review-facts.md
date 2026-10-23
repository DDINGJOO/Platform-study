# 오픈소스 기여 글 최신화 · 사실관계 독립 퇴고

기준: `4719a097d08cfc471415a226f872cc3e1b65f549` 대비 네 HTML 수정 diff. 공통 BRIEF·sources.md·status.json, 조사 시점 GitHub API 원응답과 공식 원문을 읽었다. 작성자·최종 감사자와 다른 code-reviewer가 검토했으며 글·원자료·upstream은 수정하지 않았다.

## 라운드 결과

| 글 | 라운드 1 | 반영·재검 |
|---|---|---|
| Spring Cloud Config 1편 | APPROVE · 지적 0건 | 추가 수정 요구 없음 |
| Spring Cloud Config 2편 | APPROVE · 지적 0건 | 추가 수정 요구 없음 |
| Spinnaker 2편 | LOW 1건 · COMMENT | 저자가 합계 표현 수정. 라운드 2 재검 APPROVE · 잔여 0건 |
| Debezium 2편 | APPROVE · 지적 0건 | 추가 수정 요구 없음 |

현재 네 글의 사실관계 관점 판정은 **APPROVE · 잔여 지적 0건**이다.

### 라운드 1 지적과 라운드 2 확인

LOW: Spinnaker 2편 170행의 최초 문장 `각 PR에서 고친 파일 다섯 개(#8208 네 개, #8209 한 개)`는 각 PR이 다섯 개라는 표현과 괄호의 합계가 충돌했다. 원자료는 #8208 네 파일, #8209 한 파일로 총 다섯 파일이다. 최소 수정안 `두 PR에서 고친 파일은 합계 다섯 개`를 리더에게 전달했다. 저자가 해당 표현을 수정했으며 같은 행을 다시 읽어 원자료 범위와 일치함을 확인했다. 검토자가 원문을 직접 고치지 않았다.

## 편별 근거 대조

### Spring Cloud Config 1편

- 35행: OPEN·CHANGES_REQUESTED·미머지 상태가 API 원응답과 일치한다. 주 구현·재현 시점 `3ba94c12`와 최신 변경을 분리했다.
- 142~170행의 정정: 하나의 링크 없는 샘플을 모든 Bitbucket Server push로 일반화한 과거 설명을 명시적으로 철회한다. `repo:refs_changed`의 `repository.links.clone[].href`, `pr:merged`의 `pullRequest.toRef.repository.links.clone[].href`, 링크가 없을 때 만료 없이 애플리케이션 알림을 유지하는 설명이 현재 추출기·엔드포인트와 일치한다.
- [Atlassian 지원 Jenkins 플러그인의 고정 fixture](https://github.com/jenkinsci/atlassian-bitbucket-server-integration-plugin/blob/41c40fcdcf852fe9f3b3d7897780a281b8d1a590/src/test/resources/webhook/refs_changed_body.json#L29-L39)에 HTTP·SSH clone 링크가 실제 존재함을 확인했다. 이 샘플의 존재를 모든 배포 환경에 clone 링크가 있다는 주장으로 확대하지 않는다.
- [f6c23d31 공식 diff](https://github.com/spring-cloud/spring-cloud-config/commit/f6c23d31cfd52a38d2395c4b126b718be1d70a93)의 문서·테스트 수정과 본문이 일치한다. 기존 링크 처리의 새 구현이라고 주장하지 않으며 원래 이슈 전체 해결·종료도 주장하지 않는다.
- 과거 코드 블록은 당시 코드라고 명시한다. CSS·SVG는 기준 커밋과 바이트 비교에서 동일했다. 기존 코드 블록 9개 중 변경된 하나는 Bitbucket URL 위치를 정정한 표이며, 나머지 8개는 동일하다.

### Spring Cloud Config 2편

- 36행 및 275행: 초기 여섯 요청과 `53b59abc`의 코드·테스트 결과를 보존한다. 새 head를 직접 실행했다고 표현하지 않는다.
- 307~311행: 추가 인라인 요청 세 건의 원문 시각은 2026-10-22 13:24:11Z·13:27:04Z·13:29:21Z다. 후속 리뷰와 작성자 응답을 구분한다. `WebhookRepositoryUris` 삭제와 인터페이스의 정적 `addCloneUris`/`addUri` 이동을 실제 diff로 확인했다.
- boolean 반환·`MultipleJGitEnvironmentRepository`의 `|=` 누적은 모든 기본·패턴·자리표시자 저장소를 호출한다. 엔드포인트의 `!expired && !failed` 조건은 URI 미매칭·예외 경로를 구분하며, 예외를 무시하고 성공으로 돌리는 변경은 아니다. 본문의 조건 설명이 실제 코드와 일치한다.
- Bitbucket clone 링크 있음·없음 테스트가 실제 추가·보존됐고 `pr:merged` 대상 저장소 경로도 일치한다. 구 버전 PR 본문 설명보다 최신 코드·수정 커밋을 기준으로 삼는다.
- 312~313행: API head `f6c23d31`, OPEN·CHANGES_REQUESTED 및 승인 없음과 일치한다. 최신 head check-runs는 DCO 성공 한 개이며, 이를 전체 테스트 성공으로 확대하지 않는다. lastRefresh 논점의 후속 승인·합의가 없다는 범위를 유지한다.
- 기존 코드 블록 11개 및 CSS·SVG가 기준 커밋과 모두 동일했다.

### Spinnaker 2편

- 31·81·169행: [#8208](https://github.com/spinnaker/spinnaker/pull/8208)·[#8209](https://github.com/spinnaker/spinnaker/pull/8209)의 OPEN·REVIEW_REQUIRED, 리뷰·인라인·일반 댓글 각각 0건이 원응답과 같다. #8207은 OPEN이며 댓글 두 개 모두 작성자 계정이었다.
- 113·153행: 과거 재현 SHA `d91a2724c3`·`92bd5f89b3`를 유지하고 `당시`를 추가한다. 기존 재현 명령·출력 7개 블록은 기준 커밋과 모두 동일하다.
- 170행: 각 PR의 마지막 두 커밋이 10월22일 main 병합임을 원 커밋 목록에서 확인했다. 최신 head `9e5c3b725519`·`182ca9d32ac3`가 일치한다. 조사자가 만든 해시 목록만 믿지 않고 공식 raw.githubusercontent.com에서 구·신 10개 blob을 직접 받아 SHA-256을 다시 계산했다. #8208 네 파일·#8209 한 파일 모두 구·신 원문 바이트가 같았다. 이 비교는 해당 다섯 파일에 한정하며 전체 main 변경이 없다는 뜻이 아니다.
- 171행: 각 PR check-runs 6개를 독립 집계했다. build 두 개·wrapper 검증·Summary 성공, update rule 실패, Merge Queue neutral다. 실패 체크 원문은 GitHub가 Mergify 앱의 `workflows` 권한 부재로 workflow 갱신을 거부했다는 내용이다. 본문은 이를 기여 코드 테스트 실패와 구분하며 전체 성공·머지 준비 완료를 주장하지 않는다.
- CSS·SVG는 기준 커밋과 동일하다.

### Debezium 2편

- 31·145행: [#8225](https://github.com/debezium/debezium/pull/8225)는 OPEN·head `73aa4a2a` 그대로이며 승인 없음이다. upstream grammars-v4 #5039 MERGED 상태와 구분한다. 이번 최신화에서 코드 변경이나 새 승인을 주장하지 않는다.
- 146행: [10월22일 09:10:20Z 댓글](https://github.com/debezium/debezium/pull/8225#issuecomment-6337086657)의 작성자는 PR 작성자다. `ArcInstanceResolver`·`ArcServiceProviderContributor` 컴파일 오류 및 수정 모듈 범위 설명, 모든 커밋 접두사 설명이 댓글 원문과 일치한다. 본문은 이를 작성자 설명으로 한정하며 메인테이너의 근본 원인 확인·승인으로 표현하지 않는다.
- 147행: head check-runs 58개를 원응답에서 독립 집계해 성공36·실패6·skipped16을 확인했다. [run 39574509122](https://github.com/debezium/debezium/actions/runs/39574509122)의 jobs 55개는 성공33·실패6·skipped16이다. 서로 다른 범위를 정확히 구분하며 과거 성공30 집계와의 차이를 개선·회귀로 해석하지 않는다.
- 기존 재현·실패 로그 7개 블록 및 CSS·SVG가 기준 커밋과 동일했다. 기존 로컬 실행 범위를 새 head 결과로 바꾸지 않는다.

## 검증 범위

읽은 조사 원자료는 `/tmp/opensource-pr-raw.json`, `/tmp/opensource-extra-raw.json`, `/tmp/opensource-ci-raw.json`, `/tmp/opensource-spinnaker-file-comparison.json`이며 공통 조사 시각의 공개 API 원응답이다. 메타 요약만으로 판정하지 않고 리뷰·댓글·커밋 diff·개별 체크 원문 및 공식 raw 파일을 직접 대조했다. 임시 API 응답의 개인 이메일 등 불필요한 부가 필드는 글이나 이 보고서로 옮기지 않았다.

업스트림 새 head의 테스트는 실행하지 않았다. 과거 테스트 출력 자체를 재현하는 감사가 아니라 수정 diff가 새 조회 근거와 일치하며 과거 증거를 보존하는지 검토했다. LSP 진단 도구는 제공되지 않아 실행하지 못했다. 이번 변경은 HTML 설명이며 언어 서버 타입 검증의 대상 코드를 수정하지 않는다. 전체 HTML 구조·마스킹·브라우저·업로드 검증과 최종 독립 감사는 리더의 별도 절차다.
