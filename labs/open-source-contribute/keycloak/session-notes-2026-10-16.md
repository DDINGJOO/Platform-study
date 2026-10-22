# Keycloak #53990 리뷰가 오지 않던 원인과 조치 (2026-10-16)

## 증상
- 10-14 PR 생성, 이틀 동안 사람 반응 0, 라벨 0, 리뷰 요청 0.
- CI 워크플로 6개 전부 `action_required`(첫 기여자 워크플로 실행 승인 대기).

## 원인
- `CONTRIBUTING.md` 16행: "Each PR, no matter how small, should have a GitHub issue associated with it." 커밋 메시지 마지막 줄은 `Closes #이슈번호`.
- 14행의 "작은 변경은 바로 보내도 된다" 는 디스커션 생략 허용이지 이슈 생략이 아니었다.
- Keycloak 은 이슈의 영역 라벨로 담당 팀에 넘긴다. 이슈가 없으면 라벨·팀 배정이 없고, 아무도 안 보니 워크플로 승인도 안 난다.
- 대비: Lettuce 도 템플릿에 이슈 요구가 있지만 실제로는 이슈 없는 PR 을 머지해 왔다(#3952 포함). 규칙이 분류 절차에 물려 있는지가 차이.

## 조치
1. API 로 버그 이슈 #54050 생성 → 연결. 그러나 API 생성은 이슈 양식을 거치지 않아 `kind/bug`, `status/triage` 자동 라벨이 붙지 않았다(외부 기여자는 라벨 권한 없음).
2. 웹 양식(Bug Report)으로 #54051 재생성 → `kind/bug`, `status/triage`, `area/oidc`, `team/core-protocols` 자동 부착. Area 를 `oidc` 로 고른 근거: `AccessTokenContext` 가 `org.keycloak.protocol.oidc.encode` 패키지.
3. 커밋 메시지에 `Closes #54051` 을 `Signed-off-by` 앞에 넣어 force push(코드 변경 없음), PR 본문도 수정. #54050 은 중복으로 닫음.
4. 재현 코드의 열거형 상수(`SessionType.ONLINE`, `TokenType.REGULAR`)와 생성자 시그니처를 실제 소스와 대조. 버그가 최신 릴리스 26.8.1 과 main 양쪽에 있음을 확인.

## 결과
- 10-19 mposolda 승인, 같은 날 머지(웹 양식 재생성 사흘 뒤).
- 중간에 Spotless(테스트 import 순서)로 CI 가 한 번 실패해서 고쳤다는 본인 코멘트가 PR 에 있다(10-19).
