# 오픈소스 글 최신화 독립 원자료 감사

## 판정

**PASS — 확인 22건 / 불일치 0건 / 확인 불가 0건 / 과장 0건.**

기준 커밋 `4719a097d08cfc471415a226f872cc3e1b65f549`와 현재 네 HTML의 변경 주장을 작성자·퇴고자와 분리해 대조했다. BRIEF·sources·status의 결론을 그대로 승인하지 않고, 임시 raw 응답과 공식 GitHub REST·고정 SHA raw 파일을 직접 읽었다. 이번 감사는 최신화 diff가 대상이며 기존 글 전체의 과거 실험을 새로 재실행한 감사가 아니다.

2026-10-23 재조회에서도 공식 REST의 head와 상태가 조사 스냅샷과 일치했다. GitHub 웹 페이지 캐시에 최신 head가 보이지 않는 경우에는 고정 SHA 코드와 REST 결과를 우선했다. 원글·upstream·기존 원자료는 수정하지 않았고 테스트/재현 실험을 다시 실행하지 않았다.

## Spring Cloud Config 1편

대상: `posts/open-source-contribute/spring-cloud-config/01_1편 - 웹훅이 가리킨 저장소만 만료시키기.html`

| ID | 판정 | 변경 주장 | 직접 확인한 근거 |
|---|---|---|---|
| SCC1-01 | 확인 | PR3342는 OPEN·미병합이며 최신 head는 f6c23d31이다. | 공식 `/repos/spring-cloud/spring-cloud-config/pulls/3342`에서 state=open, merged=false, head.sha=f6c23d31cfd52a38d2395c4b126b718be1d70a93 재확인. |
| SCC1-02 | 확인 | 당시 링크 없는 샘플로 Server push 전체에 URL이 없다고 일반화한 설명을 정정했다. | Atlassian 공개 Event payload의 repo:refs_changed 샘플에는 repository.links가 없지만, 고정 Jenkins 통합 플러그인 refs_changed_body.json의 repository.links.clone에는 http/ssh 둘이 있다. 서로 다른 샘플이므로 보편적 부재 주장은 성립하지 않는다. 본문은 당시 코멘트를 역사적 기록으로 남기고 바로 정정한다. |
| SCC1-03 | 확인 | Server push와 merged PR은 각각 저장소 객체의 clone 링크를 읽는다. | f6 고정 raw의 BitbucketPropertyPathNotificationExtractor에서 repo:refs_changed→request.repository, pr:merged→pullRequest.toRef.repository, 공통 addCloneUris→links.clone[].href를 직접 확인. |
| SCC1-04 | 확인 | 링크가 없으면 만료 없이 알림만 보내며 원 이슈 전체 해결/종료를 주장하지 않는다. | PropertyPathEndpoint의 빈 URI 반환은 만료 보조 메서드에서만 이뤄지고 알림 경로는 유지된다. Bitbucket notification의 application.yml 방송 및 빈 URI 테스트, 공개 이슈2249의 open 기록을 대조했다. 기존 코드 예시는 3ba94c12 당시로 분리돼 있다. |

## Spring Cloud Config 2편

대상: `posts/open-source-contribute/spring-cloud-config/02_2편 - 매칭은 느슨하게, lastRefresh는 그대로 둔 이유.html`

| ID | 판정 | 변경 주장 | 직접 확인한 근거 |
|---|---|---|---|
| SCC2-01 | 확인 | 기존 여섯 요청/53b59abc 대응 뒤 세 인라인 요청과 f6 응답이 추가됐다. | fresh pulls/3342/comments에서 리뷰어 10/22 13:24:11·13:27:04·13:29:21Z의 실제 요청 원문, 작성자10/23 00:21:00·02·04Z의 답글을 읽었다. reviews의13:31:05Z CHANGES_REQUESTED도 일치한다. |
| SCC2-02 | 확인 | 별도 helper 클래스를 삭제하고 인터페이스 정적 addCloneUris/addUri로 옮겼다. | raw commit files에 WebhookRepositoryUris removed. f6 PropertyPathNotificationExtractor 고정 원문의 두 static 메서드, Base/Bitbucket/Gitlab 호출 변경을 직접 대조했다. |
| SCC2-03 | 확인 | expireRefreshRate(String)는 boolean 일치 결과를 반환한다. | f6 JGitEnvironmentRepository 원문에서 미일치 false, 일치 시 lastRefresh=0 및 true 반환 확인. 저장 commit patch의 boolean 기대 테스트 수정과 일치한다. |
| SCC2-04 | 확인 | MultipleJGit은 |=로 기본·패턴·생성된 placeholder 결과를 누적한다. | f6 원문에서 super 호출 후 repos.values·placeholders.values 각각 반복과 |=를 확인. boolean OR 대입이므로 앞선 true 때문에 뒤의 정상 호출을 단락시키지 않는다. 예외 발생 뒤에도 모든 자식 실행을 보장한다는 주장은 아니다. |
| SCC2-05 | 확인 | URI 미일치 debug와 실제 예외 warn을 분리한다. | f6 PropertyPathEndpoint의 expired=false/failed=false, try의 expired|=, catch의 failed=true/warn, 최종 !expired&&!failed debug를 직접 확인. 예외가 있으면 미매칭 debug를 추가하지 않는다. |
| SCC2-06 | 확인 | Bitbucket 링크 유무 문서를 정정하고 링크 존재 테스트를 추가했다. | f6 commit patch의 문서 정정, bitbucketServerRepositoryCloneLinks의 HTTP/SSH 두 값 assert, 기존 bitbucketServerSample 및 PR sample의 빈 URI 기대를 확인했다. clone 링크 처리를 f6에서 최초 구현했다고 주장하지 않는다. |
| SCC2-07 | 확인 | 최신 공개 체크는 DCO 하나이며 Signed-off-by 기여 권리 선언 표기를 확인한다. 승인·lastRefresh 합의나 새 head 전체 테스트 통과는 아니다. | fresh check-runs total_count1/nameDCO/success, 추가 commit status context0. 공식 dcoapp/app의 How it works는 작성·제출 권리를 인증하는 DCO와 Signed-off-by 줄 검사를 설명한다. 이는 코드 테스트나 암호학적 서명 검증 결과가 아니다. fresh reviews에는 최신 maintainer CHANGES_REQUESTED와 작성자 COMMENTED만 있고 승인 없음. 1~7절/테스트는53b59abc 당시, 새 f6 직접 실행 기록은 제외한다고 명시한다. |

## Spinnaker 2편

대상: `posts/open-source-contribute/spinnaker/02_2편 - 승인 코멘트의 후속 8항목을 이슈 하나와 PR 둘로 옮긴 과정.html`

| ID | 판정 | 변경 주장 | 직접 확인한 근거 |
|---|---|---|---|
| SPIN-01 | 확인 | 이슈8207·PR8208/8209는 OPEN이며 새 리뷰·코멘트가 없다. | fresh REST 두 PR merged=false/stateopen/comments0/review_comments0, raw GraphQL reviewDecisionREVIEW_REQUIRED. fresh issue8207/comments에는 작성자 두 개만 존재한다. 승인이나 메인테이너 응답을 만들어내지 않는다. |
| SPIN-02 | 확인 | 각 브랜치에 main 병합 두 개가 추가돼 최신 head가 바뀌었다. | 공식 commits API로 각 최신 head부터 first-parent 두 단계를 직접 조회. 각 단계 parents2 및 Merge branch main 메시지/10월22일 시각을 확인했고, 두 번 뒤 정확히 당시 d91a2724c3/92bd5f89b3에 도달했다. 최신 head9e5c3b725519/182ca9d32ac3과 일치한다. |
| SPIN-03 | 확인 | PR 고유 수정 파일은 총5개이며 old/new 원문이 동일하다. | PR8208의4개·8209의1개 고유 경로를 raw API files와 대조. 공식 raw.githubusercontent.com에서 각 old/new 총10개 파일을 새로 받아 SHA256을 재계산해5쌍 모두 동일 및 저장 비교표와 일치함을 확인했다. upstream main의 다른 파일까지 같다는 주장은 아니다. |
| SPIN-04 | 확인 | 각 head의 build2·wrapper는 성공하지만 Mergify update는 권한 문제로 실패했다. | fresh check-runs 각각6개→success4/failure1/neutral1. failure output title은 GitHub refused to update workflow files이고 summary는 Mergify workflows 권한 없이 .github/workflows 파일 갱신을 거절했다는 실제 GitHub 응답이다. Merge Queue neutral/Summary success도 대조했다. 테스트 실패와 앱 권한 실패를 구분하며 전체 통과/머지 가능을 주장하지 않는다. |
| SPIN-05 | 확인 | 본문의 로컬 회귀 실행은 과거 두 SHA 기록이다. | 기준 diff에서 실행 SHA와 테스트 출력은 바꾸지 않고 '당시'를 추가했다. 최신 SHA는 별도 상태 절에만 기록. 병합만으로 새 head 테스트를 직접 실행했다고 하지 않는다. |

## Debezium 2편

대상: `posts/open-source-contribute/debezium/02_2편 - DEFAULT를 데이터베이스 이름으로 읽던 문법.html`

| ID | 판정 | 변경 주장 | 직접 확인한 근거 |
|---|---|---|---|
| DBZ-01 | 확인 | PR8225는 OPEN, head73aa4a2a 유지, 새 코드/승인 없음이다. | fresh REST stateopen/mergedfalse/head73aa4a2a334f56b57c5295299821f2cbfabe1416. reviews는 Naros의 기존 COMMENTED 하나이고 approval없음. raw 상류 PR5039 mergedAt·stateMERGED를 대조했다. |
| DBZ-02 | 확인 | 새 CI 설명은 10/22 09:10:20Z 작성자 댓글이다. | fresh issues/8225/comments에서 해당 public issuecomment의 user.login·시각·본문을 직접 확인. ArcInstanceResolver/ArcServiceProviderContributor의 Quarkus 컴파일 오류와 수정 범위 밖이라는 설명은 작성자의 주장으로 정확히 귀속한다. 메인테이너의 원인 확인/승인으로 확장하지 않는다. |
| DBZ-03 | 확인 | 같은 댓글은 commit prefix 존재를 설명하며 Commit message 체크는 성공이다. | 댓글의 모든 커밋에 debezium/dbz#2842 접두사가 있다는 실제 문장을 읽고, raw check-runs의 Commit message/success를 확인했다. 봇 요청과 통과 체크는 서로 다른 증거로 분리한다. |
| DBZ-04 | 확인 | 최신 head 전체 체크58개는36성공/6실패/16건너뜀이다. | fresh commits/73aa.../check-runs?per_page=100의 실제 배열58개 conclusion을 독립 Counter로 집계했다. |
| DBZ-05 | 확인 | 단일 실행의 jobs55개는33성공/6실패/16건너뜀이다. | fresh actions/runs/39574509122/jobs?per_page=100의 실제 배열55개를 독립 Counter로 집계했다. 전체 head 체크와 단일 workflow jobs의 집계 범위를 구분한다. |
| DBZ-06 | 확인 | 과거30성공/6실패와 최신 집계를 단순 개선·악화로 비교하지 않는다. | diff는 당시 수치를 역사적 범위로 남기고 최신 두 분모를 별도 명시한다. 기존 파서 단위 실험·merge-tree 재현을 최신 head에서 새로 실행한 것으로 바꾸지 않았다. |

최종 소폭 수정도 대조했다. SCC1 도입부의 refresh-rate 문제와 Bitbucket 일반화 정정은 위 근거와 일치하며 설정 키의 `<wbr>`는 표시용 구분이다. Spinnaker의 합계5개 표현은 PR별4개와1개의 원문 비교에 일치한다. SCC2에 추가된 DCO 설명과 공식 링크는 SCC2-07에 포함했다.

## 사용한 원자료와 확인 한계

임시 원본은 `/tmp/opensource-pr-raw.json`, `/tmp/opensource-extra-raw.json`, `/tmp/opensource-ci-raw.json`, `/tmp/opensource-spinnaker-file-comparison.json`이다. 이 파일은 공식 API 응답의 검토용 스냅샷이며 공개 저장소에 넣지 않는다. 현재 상태의 핵심 값은 위 fresh GET으로 대조했다.

공식 공개 출처: [SCC PR](https://github.com/spring-cloud/spring-cloud-config/pull/3342), [DCO 공식 설명](https://github.com/dcoapp/app#how-it-works), [f6 commit](https://github.com/spring-cloud/spring-cloud-config/commit/f6c23d31cfd52a38d2395c4b126b718be1d70a93), [Atlassian 문서](https://confluence.atlassian.com/bitbucketserver076/event-payload-1026535078.html), [고정 플러그인 fixture](https://github.com/jenkinsci/atlassian-bitbucket-server-integration-plugin/blob/41c40fcdcf852fe9f3b3d7897780a281b8d1a590/src/test/resources/webhook/refs_changed_body.json), [Jenkins 공식 플러그인 페이지](https://plugins.jenkins.io/atlassian-bitbucket-server-integration/), [Spinnaker8208](https://github.com/spinnaker/spinnaker/pull/8208), [Spinnaker8209](https://github.com/spinnaker/spinnaker/pull/8209), [Debezium8225](https://github.com/debezium/debezium/pull/8225), [단일 workflow 실행](https://github.com/debezium/debezium/actions/runs/39574509122).

추가 반례로 '링크 없는 샘플=모든 payload', '작성자 대응=승인', 'DCO 하나=전체 테스트 성공', 'main 병합=고유 동작 새 변경', '앱 권한 실패=기여 테스트 실패', '댓글의 원인 설명=입증', '서로 다른 집계 차이=CI 개선', '옛 SHA 실험=새 head 실행'을 찾았으며 수정 본문은 모두 구분한다. 확인한 변경 주장에 추가 사실 수정 요구는 없다. 공개 상태는 조회 이후 바뀔 수 있으며 실제 새 head 전체 실험과 댓글의 컴파일 원인 가설은 이번 감사가 입증하지 않는다.

네 편 중 신뢰도가 가장 낮은 부분이 있는 글은 Debezium 2편이다. 실패 원인이 수정 범위 밖이라는 작성자의 CI 원인 가설 자체는 독립 재현하지 않았으며, 본문이 이를 작성자의 설명으로 정확히 귀속하므로 최신화 주장 판정에는 영향을 주지 않는다.
