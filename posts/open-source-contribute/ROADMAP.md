# 오픈소스 기여 회고

분류 이름은 `open-source-contribute`다. 여섯 프로젝트의 회고 글 11편을 작성해 티스토리에 업로드했다. 2026-10-23에 공개 PR·이슈 상태를 다시 확인했고, 변경 근거가 있는 네 편을 최신화했다.

PR 개수만큼 글을 만들지는 않는다. 하나의 문제가 여러 저장소·PR·후속 테스트에 걸쳐 해결됐다면 한 회고에서 과정을 연결한다.

## 쓸 때 모을 근거

- 공개 이슈와 PR의 문제 설명, 변경 전후 diff
- 실제 로컬 재현과 테스트 명령·로그
- 리뷰에서 바뀐 판단과 유지보수자의 후속 수정
- 내 수정, 다른 기여자의 수정, 아직 남은 한계

기억만으로 당시의 의도·감정·테스트 결과를 만들지 않는다. PR 상태와 테스트 통과 여부는 집필 시 다시 확인한다. 미공개 보안 제보·비공개 포크의 내용은 포함하지 않는다.

OpenTelemetry의 일반 구조·설계 공부는 [별도 OTel 시리즈](../CS/Observability/otel/ROADMAP.md)에 쓴다. 회고에는 실제 문제를 어떻게 좁히고 수정·검증했는지를 중심으로 담는다.

글은 `posts/open-source-contribute/<프로젝트>/`에서 관리하고 `tistory-series.json`에 등록했다. 기존 티스토리 글 번호와 실제 공개 범위를 유지해 수정한다.

## 2026-10-23 상태 대조

| 프로젝트 | 글 수 | 최신 확인 |
|---|---:|---|
| Lettuce | 2 | 관련 세 PR은 기존과 같이 MERGED, 추가 변경 없음 |
| Keycloak | 1 | 기존과 같이 MERGED, 추가 변경 없음 |
| OpenTelemetry | 2 | 관련 네 PR은 기존과 같이 MERGED, 추가 변경 없음 |
| Spring Cloud Config | 2 | PR은 OPEN·CHANGES_REQUESTED. 새 리뷰 세 건과 후속 수정, Bitbucket 설명 정정 반영 |
| Spinnaker | 2 | 1편 PR은 MERGED. 2편 두 PR은 OPEN, main 동기화와 최신 CI 상태 반영 |
| Debezium | 2 | 1편 PR은 MERGED, 2편 PR은 OPEN. 새 작성자 CI 설명을 승인과 구분해 반영 |

이번 조회에서 새로 머지된 PR은 없다. 기술 변경이 없는 일곱 글은 유지하고, 과거 재현 SHA·테스트 결과를 최신 head 실행 결과로 바꾸지 않는다. 원문 URL·확인 시각·수정 범위는 [조사 기록](../../labs/open-source-contribute/updates-2026-10-23/sources.md)에 보존한다. 신규 커밋을 직접 실행하거나 upstream에 댓글·수정을 남기지는 않았다.
