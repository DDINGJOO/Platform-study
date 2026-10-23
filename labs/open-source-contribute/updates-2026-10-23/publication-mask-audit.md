# 오픈소스 최신화 마스킹 독립 감사

## 판정

**APPROVE — 제공된 고유 후보 5개와 매칭 문맥 9개 전부 확인. 미분류 0개, 실제 비밀 검출 0개.**

`/tmp/opensource-mask-candidates.json`의 각 문맥이 실제 대상 파일에 존재하는지 대조하고, 공개 공식 출처를 직접 조회했다. 연구자의 ID 분류를 그대로 인용하지 않았다. 검사기·허용 목록·원글·원자료는 수정하지 않았으며, 정확한 값과 사유만 `/tmp/opensource-mask-classified.json`에 작성했다.

| 분류 | 고유 후보 수 | 출처 검증 |
|---|---:|---|
| 공식 Atlassian 문서 페이지 ID | 1 | 공개 Bitbucket Server Event payload 문서 URL과 페이지 내용을 직접 조회했다. |
| 동일 공식 공개 문서 URL | 1 | confluence 도메인 패턴 때문에 내부 URL로 잡혔지만 인증 없이 열리는 제품 공식 문서다. |
| 공개 GitHub check-run ID | 2 | Spinnaker PR 두 개의 최신 head check-runs API를 직접 조회해 ID·html_url·Mergify 실패 출력이 일치함을 확인했다. 12자리 AWS 계정 패턴 적중은 같은 두 값의 중복 분류다. |
| 공개 GitHub issue comment ID | 1 | Debezium PR의 issues/comments API를 직접 조회해 작성자·시각·CI 설명 본문·공개 링크를 대조했다. |
| **합계** | **5** | 미분류 0개 |

모든 후보 문맥에 저장소 밖 조직 목록을 적용해 조직 적중 0개를 확인했다. 목록 파일의 존재·비어 있지 않음을 확인하고 기존 load_extra로 읽었으며 내용은 출력하거나 저장하지 않았다.

검토용 raw artifact 4개도 JSON으로 파싱하고 GitHub 토큰·AWS 액세스 키·비밀키 시작 패턴이 없음을 확인했다. raw에는 공개 GitHub의 작성자 프로필·noreply 이메일 등 공개 API 메타데이터가 포함될 수 있으므로 이를 일반 발행 허용으로 확장하지 않는다. raw artifact는 저장소에 포함하지 않는다는 범위를 유지한다.

이 판정은 제공된 후보 스냅샷에 대한 것이다. 최종 루트 재생성에서 새로운 값이 추가되면 해당 값은 추가 원출처 확인 전까지 이 승인 범위에 포함하지 않는다. 보고서에는 실제 후보 값이나 조직 목록 내용을 싣지 않는다.
