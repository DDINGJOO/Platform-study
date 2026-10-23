# Open source 글 최신 상태 조사

확인 시각: 2026-10-23T14:20:03.387899+00:00

공개 upstream 읽기 전용. 블로그·원본 저장소·외부 댓글 수정 없음. GitHub REST/gh 최신 조회 + web 공식 PR 페이지 열람. web 캐시가 옛 커밋 수를 보이면 최신 API head를 우선.

## 핵심 결과

11편 중 4편에 수정 근거가 있고 7편은 변화가 없습니다. 새로 머지된 PR은 없습니다. Spring Cloud Config 두 글의 Bitbucket 설명은 실제 새 리뷰에 따라 정정해야 합니다. Spinnaker는 병합 동기화만 추가됐고, Debezium은 작성자 CI 설명 댓글이 추가됐습니다.

## 글별 비교

### posts/open-source-contribute/lettuce/01_1편 - 검증 코드가 있는데 null이 통과한 이유.html

판정: 변화 없음

- [redis/lettuce #3952](https://github.com/redis/lettuce/pull/3952): MERGED, head `4f3e144a288a`, review `없음`, 댓글 1 / 리뷰 0, 갱신 2026-10-14T14:56:57Z.

수정 권고:
- 관련 PR의 머지·head·마지막 리뷰/코멘트가 기존 2026-10-22 기록 이후 바뀌지 않음. 기술 본문과 과거 재현 로그를 수정할 근거 없음. 확인일 주석/공통 현황표만 갱신 가능.

### posts/open-source-contribute/lettuce/02_2편 - 같은 실수를 저장소 전체에서 찾아보니.html

판정: 변화 없음

- [redis/lettuce #3954](https://github.com/redis/lettuce/pull/3954): MERGED, head `10686c5d6f29`, review `없음`, 댓글 1 / 리뷰 0, 갱신 2026-10-16T08:50:02Z.
- [redis/lettuce #3955](https://github.com/redis/lettuce/pull/3955): MERGED, head `77ddd8a88c42`, review `없음`, 댓글 1 / 리뷰 0, 갱신 2026-10-16T08:50:29Z.

수정 권고:
- 관련 PR의 머지·head·마지막 리뷰/코멘트가 기존 2026-10-22 기록 이후 바뀌지 않음. 기술 본문과 과거 재현 로그를 수정할 근거 없음. 확인일 주석/공통 현황표만 갱신 가능.

### posts/open-source-contribute/opentelemetry/02_2편 - 계측이 애플리케이션의 동작을 바꾼 두 건.html

판정: 변화 없음

- [open-telemetry/opentelemetry-java-instrumentation #20658](https://github.com/open-telemetry/opentelemetry-java-instrumentation/pull/20658): MERGED, head `c017ad757020`, review `APPROVED`, 댓글 4 / 리뷰 4, 갱신 2026-10-19T07:20:45Z.
- [open-telemetry/opentelemetry-java-instrumentation #20659](https://github.com/open-telemetry/opentelemetry-java-instrumentation/pull/20659): MERGED, head `f99b4594eeae`, review `APPROVED`, 댓글 3 / 리뷰 3, 갱신 2026-10-20T07:12:10Z.

수정 권고:
- 관련 PR의 머지·head·마지막 리뷰/코멘트가 기존 2026-10-22 기록 이후 바뀌지 않음. 기술 본문과 과거 재현 로그를 수정할 근거 없음. 확인일 주석/공통 현황표만 갱신 가능.

### posts/open-source-contribute/opentelemetry/01_1편 - 서버 주소가 비고 에러 타입이 BLPOP.이 된 이유.html

판정: 변화 없음

- [open-telemetry/opentelemetry-java-instrumentation #20660](https://github.com/open-telemetry/opentelemetry-java-instrumentation/pull/20660): MERGED, head `b7f5249ae7db`, review `APPROVED`, 댓글 4 / 리뷰 6, 갱신 2026-10-19T14:30:43Z.
- [open-telemetry/opentelemetry-java-instrumentation #20661](https://github.com/open-telemetry/opentelemetry-java-instrumentation/pull/20661): MERGED, head `672c75727122`, review `APPROVED`, 댓글 5 / 리뷰 4, 갱신 2026-10-19T07:01:35Z.

수정 권고:
- 관련 PR의 머지·head·마지막 리뷰/코멘트가 기존 2026-10-22 기록 이후 바뀌지 않음. 기술 본문과 과거 재현 로그를 수정할 근거 없음. 확인일 주석/공통 현황표만 갱신 가능.

### posts/open-source-contribute/spring-cloud-config/01_1편 - 웹훅이 가리킨 저장소만 만료시키기.html

판정: 수정 필요: 새 리뷰·수정 커밋 및 기존 Bitbucket 설명 정정

- [spring-cloud/spring-cloud-config #3342](https://github.com/spring-cloud/spring-cloud-config/pull/3342): OPEN, head `f6c23d31cfd5`, review `CHANGES_REQUESTED`, 댓글 3 / 리뷰 11, 갱신 2026-10-23T00:21:00Z.

기존 문장:
- 35행: 2026-10-22 현재 아직 열려 있고 머지되지 않았습니다.
- 149행: Bitbucket Server 푸시 저장소 URL 없음
- 151행: Bitbucket Server의 기본 푸시 페이로드에는 저장소 URL이 아예 없습니다.
- 157행: 원래 이슈에 들어 있던 Bitbucket Server 사례는 이 PR로 해결되지 않아요.

수정 권고:
- 현재 상태 확인일을 2026-10-23(UTC/KST 구분)로 갱신하되 OPEN·미승인 유지.
- 당시 샘플에는 clone 링크가 없었다고 범위를 한정하고, 10월23일 정정으로 repository.links.clone[].href가 있으면 식별·만료 가능하며 링크가 없으면 알림만 보낸다고 설명. pr:merged는 pullRequest.toRef.repository.links.clone[].href.
- 당시 남긴 공개 코멘트 인용은 역사적 사실로 남길 수 있지만 바로 뒤에 그 문구가 과도한 일반화였음을 명시. 원래 Bitbucket 사례 전체 해결·자동 이슈 종료를 주장하지 말 것.

### posts/open-source-contribute/spring-cloud-config/02_2편 - 매칭은 느슨하게, lastRefresh는 그대로 둔 이유.html

판정: 수정 필요: 새 리뷰·수정 커밋 및 기존 Bitbucket 설명 정정

- [spring-cloud/spring-cloud-config #3342](https://github.com/spring-cloud/spring-cloud-config/pull/3342): OPEN, head `f6c23d31cfd5`, review `CHANGES_REQUESTED`, 댓글 3 / 리뷰 11, 갱신 2026-10-23T00:21:00Z.

기존 문장:
- 36행: 대응은 2026-10-22 커밋 53b59abc 하나에 모았습니다.
- 306행: 마지막 활동은 제가 남긴 이 코멘트이고, 메인테이너는 아직 답하지 않았습니다.

수정 권고:
- 기존 여섯 요청과 53b59abc 대응은 당시 기록으로 보존하고, 10월22일 13:24~13:29Z 새 인라인 요청 세 건 및 10월23일 f6c23d31 대응 절 추가.
- (1) 별도 WebhookRepositoryUris 삭제, 정적 addCloneUris/addUri를 PropertyPathNotificationExtractor로 이동. (2) expireRefreshRate(String)가 boolean을 반환하여 URI가 있으나 어느 저장소도 안 맞으면 debug, 예외 발생 시 warn만 유지. MultipleJGit도 전체 자식 순회하며 OR 누적. (3) Bitbucket Server 링크가 있을 수 있음을 문서·테스트에 반영.
- 2026-10-23 조회 시 OPEN, CHANGES_REQUESTED, 승인 없음. latest maintainer review 10-22 13:31:05Z, author replies 10-23 00:21Z. lastRefresh 배치 관련 새 승인·반박은 없으므로 결론 미정 유지.
- API에 노출되는 최신 head 체크는 DCO 성공 하나뿐. 새 커밋 전체 테스트 통과라고 쓰지 말 것(새 로컬 실행 로그를 별도 확인한 경우에만 추가). PR 본문은 옛 URL 매칭 설명을 아직 포함하므로 최신 코드·커밋·inline 응답을 우선.

### posts/open-source-contribute/spinnaker/02_2편 - 승인 코멘트의 후속 8항목을 이슈 하나와 PR 둘로 옮긴 과정.html

판정: 수정 권고: 최신 head·CI 상태, 본문 동작 변화 없음

- [spinnaker/spinnaker #8208](https://github.com/spinnaker/spinnaker/pull/8208): OPEN, head `9e5c3b725519`, review `REVIEW_REQUIRED`, 댓글 0 / 리뷰 0, 갱신 2026-10-22T16:05:53Z.
- [spinnaker/spinnaker #8209](https://github.com/spinnaker/spinnaker/pull/8209): OPEN, head `182ca9d32ac3`, review `REVIEW_REQUIRED`, 댓글 0 / 리뷰 0, 갱신 2026-10-22T16:05:59Z.

기존 문장:
- 31/81/169/173행: 2026-10-22 현재 상태 설명
- 113행: PR head(d91a2724c3)에서 돌렸어요.
- 153행: PR head(92bd5f89b3)에서 확인했어요.

수정 권고:
- 재현 때 사용한 d91a2724c3/92bd5f89b3은 역사적 실행 기준으로 그대로 보존. 최신 head는 #8208 9e5c3b725519, #8209 182ca9d32ac3으로 따로 기록.
- 각 브랜치에 main 병합 2개(10월22일)가 추가되었고, PR 고유 수정 파일 5개의 old/new 원문 바이트 SHA-256이 전부 동일. 기능·회귀 테스트 변경이나 새 리뷰가 생겼다고 쓰지 말 것.
- 2026-10-23 조회 시 이슈 #8207와 PR 둘 OPEN, 두 PR REVIEW_REQUIRED, review/inline/comment 0, 이슈 댓글은 작성자 둘뿐.
- 각 최신 head에서 build 2개와 wrapper validation 성공. Mergify update rule은 workflows 권한 부족으로 워크플로 파일 갱신을 GitHub가 거절하여 실패했어요. merge queue NEUTRAL, summary 성공이므로 모든 체크 통과/머지 준비 완료라고 쓰지 말 것. 조직 앱 권한 문제이며 기여 코드 테스트 실패와 분리해 설명.

### posts/open-source-contribute/spinnaker/01_1편 - 중복 배달된 StartExecution이 끝난 파이프라인을 RUNNING으로 되돌렸다.html

판정: 변화 없음

- [spinnaker/spinnaker #8174](https://github.com/spinnaker/spinnaker/pull/8174): MERGED, head `91d6dc75241e`, review `APPROVED`, 댓글 4 / 리뷰 2, 갱신 2026-10-15T22:11:44Z.

수정 권고:
- 관련 PR의 머지·head·마지막 리뷰/코멘트가 기존 2026-10-22 기록 이후 바뀌지 않음. 기술 본문과 과거 재현 로그를 수정할 근거 없음. 확인일 주석/공통 현황표만 갱신 가능.

### posts/open-source-contribute/keycloak/01_1편 - 검증 버그를 고쳤는데 리뷰가 오지 않던 이유.html

판정: 변화 없음

- [keycloak/keycloak #53990](https://github.com/keycloak/keycloak/pull/53990): MERGED, head `e3d4fe42e8ee`, review `APPROVED`, 댓글 1 / 리뷰 6, 갱신 2026-10-19T17:06:11Z.

수정 권고:
- 관련 PR의 머지·head·마지막 리뷰/코멘트가 기존 2026-10-22 기록 이후 바뀌지 않음. 기술 본문과 과거 재현 로그를 수정할 근거 없음. 확인일 주석/공통 현황표만 갱신 가능.

### posts/open-source-contribute/debezium/02_2편 - DEFAULT를 데이터베이스 이름으로 읽던 문법.html

판정: 수정 권고: 작성자 CI 설명 댓글 추가, 코드·머지·리뷰 변화 없음

- [debezium/debezium #8225](https://github.com/debezium/debezium/pull/8225): OPEN, head `73aa4a2a334f`, review `없음`, 댓글 8 / 리뷰 1, 갱신 2026-10-22T09:10:20Z.
- [antlr/grammars-v4 #5039](https://github.com/antlr/grammars-v4/pull/5039): MERGED, head `beca5470df89`, review `없음`, 댓글 2 / 리뷰 0, 갱신 2026-10-20T21:35:59Z.

기존 문장:
- 도입·7절: 2026년 10월22일 현재 OPEN, Naros 제안 반영 후 승인 없음.
- 7절: github-actions 봇의 커밋 메시지 접두사 코멘트와 체크 통과.

수정 권고:
- 2026-10-23 재확인으로 날짜만 갱신하고 OPEN·head73aa4a2a·승인 없음 유지.
- 10월22일 09:10:20Z 작성자가 Quarkus engine runtime의 ArcInstanceResolver/ArcServiceProviderContributor 컴파일 실패는 이 PR 수정 범위 밖이며 모든 커밋에 debezium/dbz#2842 접두사가 있다고 설명한 댓글을 추가. 이것은 작성자 설명이며 메인테이너 검증·승인으로 표현하지 말 것.
- 현재 head 체크58개 전체 집계는 success36/failure6/skipped16. 단일 실행39574509122 jobs55개는 success33/failure6/skipped16. 기존 글의 성공30은 집계 범위가 달라 단순 새 실패·개선으로 비교하지 말 것. 필요하면 실행ID와 포함범위를 명시해 최신 집계로 바꿀 것.

### posts/open-source-contribute/debezium/01_1편 - ALTER DATABASE 한 줄에 멈춘 커넥터, 상류 문법까지 고치기.html

판정: 변화 없음

- [debezium/debezium #8220](https://github.com/debezium/debezium/pull/8220): MERGED, head `81981af2bad1`, review `APPROVED`, 댓글 11 / 리뷰 2, 갱신 2026-10-21T07:18:57Z.
- [antlr/grammars-v4 #5037](https://github.com/antlr/grammars-v4/pull/5037): MERGED, head `1145473cabad`, review `없음`, 댓글 1 / 리뷰 0, 갱신 2026-10-20T21:34:15Z.

수정 권고:
- 관련 PR의 머지·head·마지막 리뷰/코멘트가 기존 2026-10-22 기록 이후 바뀌지 않음. 기술 본문과 과거 재현 로그를 수정할 근거 없음. 확인일 주석/공통 현황표만 갱신 가능.

## 신규 Spring 리뷰 원문 링크

- 2026-10-22T13:24:11Z ryanjbaxter: https://github.com/spring-cloud/spring-cloud-config/pull/3342#discussion_r4348858407
- 2026-10-22T13:27:04Z ryanjbaxter: https://github.com/spring-cloud/spring-cloud-config/pull/3342#discussion_r4348888372
- 2026-10-22T13:29:21Z ryanjbaxter: https://github.com/spring-cloud/spring-cloud-config/pull/3342#discussion_r4348914110
- 2026-10-23T00:21:00Z DDINGJOO: https://github.com/spring-cloud/spring-cloud-config/pull/3342#discussion_r4354895624
- 2026-10-23T00:21:02Z DDINGJOO: https://github.com/spring-cloud/spring-cloud-config/pull/3342#discussion_r4354895783
- 2026-10-23T00:21:04Z DDINGJOO: https://github.com/spring-cloud/spring-cloud-config/pull/3342#discussion_r4354895936

커밋 diff: https://github.com/spring-cloud/spring-cloud-config/commit/f6c23d31cfd52a38d2395c4b126b718be1d70a93

## Bitbucket 설명 정정의 별도 원출처

- https://github.com/jenkinsci/atlassian-bitbucket-server-integration-plugin/blob/41c40fcdcf852fe9f3b3d7897780a281b8d1a590/src/test/resources/webhook/refs_changed_body.json#L29-L39
- https://github.com/jenkinsci/atlassian-bitbucket-server-integration-plugin/blob/41c40fcdcf852fe9f3b3d7897780a281b8d1a590/src/main/java/com/atlassian/bitbucket/jenkins/internal/model/BitbucketRepository.java#L118-L124
- https://confluence.atlassian.com/bitbucketserver076/event-payload-1026535078.html

Atlassian 지원 플러그인 fixture에 clone 링크 둘 존재. 모델은 links/clone 생략도 처리. 공식 문서 샘플에 링크가 없다는 사실을 모든 실페이로드에 일반화할 수 없음.

## 이슈 상태

- [spinnaker/spinnaker#8207](https://github.com/spinnaker/spinnaker/issues/8207): open, updated 2026-10-22T02:04:00Z, closed None, comments 2.
- [spinnaker/spinnaker#7921](https://github.com/spinnaker/spinnaker/issues/7921): closed, updated 2026-10-15T22:11:45Z, closed 2026-10-15T22:11:45Z, comments 6.
- [spring-cloud/spring-cloud-config#2249](https://github.com/spring-cloud/spring-cloud-config/issues/2249): open, updated 2026-10-09T12:31:57Z, closed None, comments 4.
- [keycloak/keycloak#54051](https://github.com/keycloak/keycloak/issues/54051): closed, updated 2026-10-19T17:06:24Z, closed 2026-10-19T17:06:12Z, comments 1.
- [debezium/dbz#2829](https://github.com/debezium/dbz/issues/2829): open, updated 2026-10-11T12:52:28Z, closed None, comments 2.
- [debezium/dbz#2842](https://github.com/debezium/dbz/issues/2842): open, updated 2026-10-11T12:36:56Z, closed None, comments 1.
- [antlr/grammars-v4#5036](https://github.com/antlr/grammars-v4/issues/5036): closed, updated 2026-10-20T21:34:17Z, closed 2026-10-20T21:34:17Z, comments 3.
- [antlr/grammars-v4#5038](https://github.com/antlr/grammars-v4/issues/5038): closed, updated 2026-10-20T21:36:00Z, closed 2026-10-20T21:36:00Z, comments 2.

## 검증 범위와 한계

- 최신 새 커밋을 직접 실행한 것은 아님. 코드·추가 테스트 원문과 공개 체크만 확인.
- debezium/dbz#2829와 #2842는 아직 OPEN. 전자는 수정 PR #8220 MERGED와 별개이므로 이슈까지 닫혔다고 쓰지 말 것.
- Spinnaker #8207은 작성자 follow-up 외 메인테이너 답 없음.
- 과거 재현 로그는 당시 고정 SHA의 기록이므로 최신 head 번호로 치환하지 않습니다. 최신 코드 실행·전 버전 테스트·릴리스 포함 여부는 별도 검증하지 않았습니다.
- 외부 쓰기, 인증 전환, 블로그 수정은 하지 않았습니다.
- 현재 상태와 원문 URL은 같은 디렉터리의 `status.json`에 기록했습니다. 조사 중 임시로 받은 전체 API 응답은 저장소에 포함하지 않았습니다.
