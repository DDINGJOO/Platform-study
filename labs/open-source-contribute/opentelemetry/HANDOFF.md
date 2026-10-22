# 다음 작업 (2026-10-22 저녁 기준)

## 1. Lettuce sync 타임아웃 수정 PR (이슈 #20847)
- 상태: 이슈 제출(웹 양식, 라벨 bug·needs triage), 이슈에 "수정 중" 코멘트 남김. 수정 코드는 아직 없다.
- 남은 것: `lettuce-sync-timeout/wip-fix.patch` 는 재현 테스트(`LettuceSyncClientTest.syncCommandTimeoutIsRecordedAsError`)만 추가한 상태다. origin/main 548cd0242f 기준.
- 설계 방향(이슈 코멘트와 같다): 리액티브 구독 취소와 사용자 직접 cancel 은 지금처럼 에러 아님. Lettuce 의 `awaitOrCancel` 안에서 일어난 취소만, span 을 보류했다가 던져진 `RedisCommandTimeoutException` 으로 끝낸다.
- 먼저 할 것: 지원 범위의 가장 오래된 Lettuce 와 최신 Lettuce 소스로 `awaitOrCancel` 의 클래스 이름과 "cancel → 완료 콜백 → throw" 순서를 확인한다.
- 자체 리뷰 항목: 보류한 span 누수, ThreadLocal 정리, 중첩·재진입, 무한 재귀(advice 가 자기 자신을 부르는지), identity, muzzle(버전별 메서드 부재), sync 호출마다 붙는 비용.

## 2. Reactor PR #20845
- 리뷰 반영 커밋 60be7a98c8 푸시, Copilot 스레드 답글 완료. 메인테이너 리뷰 대기.
- CI 실패 44건은 main 의 -Werror 문제였다. main 이 #20844 로 고쳐졌으니 main 을 병합해 CI 를 다시 돌린다.

## 3. 보류·대기
- Kafka partition/offset -1: 보류(`kafka-unknown-offset/journal.md` 끝의 다시 열 조건).
- Reactor Sinks 를 연산자 없이 바로 구독하는 경우: #20845 반응을 보고 이슈로 물을지 결정.
- WebFlux 2건: #20643 정리 대기.

## 다른 컴퓨터에서 시작할 때
- `git pull` 후 `.claude/skills/oss-contribute/` 스킬을 쓴다.
- 노션 동기화 스크립트는 로컬 설정이 필요하다: `~/.claude/notion-sync/state/oss-tracker.json` 에 `{"db": "<개인 노션 「오픈소스 PR」 DB ID>", "skip_owners": [<업무 GitHub 조직들>]}`. 값은 이 컴퓨터의 같은 파일에서 옮긴다(저장소에 두지 않는다).
- `logs/`, `reports/` 는 로컬 경로가 찍혀 있어 커밋하지 않았다. 이 컴퓨터에만 있다.
