# Lettuce #3954, #3955 작업 기록 (2026-10-16)

## 탐색
- 이전 기여 #3952(같은 값을 두 번 검증해서 다른 인자의 null 검사가 빠진 버그)와 같은 실수를 찾으려고 저장소 전체를 스크립트로 훑었다.
- 1차 탐색: `LettuceAssert` 호출이 연속된 블록에서 같은 식별자를 두 번 검증하는 곳 → 58블록. 대부분 `notNull → notEmpty → noNullElements` 라는 의도된 단계적 검증이라 버그가 아니었다(오탐).
- 2차 탐색: 단언 메시지의 주어와 검증 대상 변수가 어긋나는 곳 → 77건. 대부분 메시지가 개념을 가리키는 정상 표현(`type` → "Class")이었고, 실제 결함 두 건을 찾았다.
  - `ClientOptions.Builder#reauthenticateBehavior`: `"ReuthenticatBehavior must not be null"` (공개 빌더, 사용자에게 노출)
  - `CompressionCodec#copy`: `to` 를 검증하면서 메시지가 `"From must not be null"` (private 메서드)
- 오탈자 사전 검사: `lenght` 12곳(6파일, 스트림 XACK·XLEN 자바독, 공개 API), `overriden` 8곳, `occured` 1곳. 같은 파일 안에 `length of the stream` 이 올바르게 쓰인 곳이 있어 내부 불일치였다.
- `.agents/docs/architecture.md`: API 인터페이스는 코드 생성물이 아니라 손으로 쓰는 파일 → 여섯 갈래를 모두 고쳐야 함.
- 남은 후보(`SslOptions` 메시지 차이, 소문자 주어 2곳)는 결함이 아니거나 너무 사소해서 제외.

## 확인
- 메시지 문자열에 의존하는 테스트 검색: `RedisCommandBuilderUnitTests` 가 `"From must not be null"` 을 단언하지만 그건 `geodist` 의 올바른 검증용이라 무관. 깨지는 테스트 없음.
- 포매터 줄 길이 한도 128, 바뀐 줄 중 최대 126.
- `./mvnw formatter:validate` 두 브랜치 모두 통과.

## 분리 판단
- 머지 이력: 1파일 1~3줄 오탈자 PR 을 꾸준히 받고(#2213, #1826, #1632, #1497), "various typos" 묶음도 받는다(#3423).
- 자바독 오탈자(A)와 런타임 단언 메시지(B)는 리뷰어가 할 판단이 달라서 두 PR 로 나눔. B 는 "이 문자열에 기대는 코드가 없나" 라는 질문이 붙는다.
- 두 메시지 수정은 같은 성격이라 다시 쪼개지 않음.

## 결과
- #3954 (10파일 +21/-21), #3955 (2파일 +2/-2) 모두 2026-10-16 머지.
- #3955 CI 에서 `RediSearchIntegrationTests.testFtAlterAddingNewFields` 1건 실패(4,784개 중). 바꾼 파일과 무관하고, 같은 기준 커밋의 #3954 는 통과 → 간헐 실패로 판단. 재실행은 관리자 권한이 필요해 못 함.
