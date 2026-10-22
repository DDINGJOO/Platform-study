# Spinnaker 재현 기록 (2026-10-22)

- 저장소: spinnaker/spinnaker (모노레포). `--filter=blob:none --no-checkout` 으로 받고 sparse checkout 으로 deck, docs, examples 를 뺐다. 루트 settings.gradle 이 `includeBuild 'deck'` 을 하므로 빈 `deck/settings.gradle` 만 만들어 뒀다(저장소에는 쓰지 않음, 작업 사본 한정).
- JDK: Homebrew OpenJDK 25.0.4 (CI 워크플로 generic-build-publish 가 Java 25 를 쓴다). Gradle 9.6.1 (wrapper).
- Docker: Desktop 실행 중. SQL 테스트는 Testcontainers 로 MySQL 8.0.40 컨테이너를 사용한다.
- 공통 옵션: `./gradlew --no-daemon --max-workers=2 -Dorg.gradle.jvmargs=-Xmx2g`
- 작업 사본은 끝나고 삭제함.

## 1. #8174 (머지 커밋 1f568ed149)

### 기준 상태(머지 커밋)
```
./gradlew --no-daemon --max-workers=2 -Dorg.gradle.jvmargs=-Xmx2g \
  :orca:orca-queue:test --tests '*StartExecutionHandlerTest' \
  :orca:orca-sql:test --tests '*SqlExecutionRepositoryTest'
```
결과: BUILD SUCCESSFUL in 10m 26s (첫 실행이라 Gradle 배포판과 의존성 내려받기·컴파일 포함, 206 tasks).
- StartExecutionHandlerTest: 48 tests, 0 failures
- SqlExecutionRepositoryTest: 21 tests, 0 failures (PR 본문의 "orca-sql 21 tests" 와 일치)
- 이 중 PR 이 추가한 SQL 테스트: "a stale copy cannot move a completed execution back to RUNNING", "updates the execution when the stored status matches"

### 본 코드만 되돌린 상태
- `StartExecutionHandler.kt` 를 1f568ed149^ 버전으로 되돌림(`updateStatus(execution)` 무조건 저장)
- `SqlExecutionRepository.updateStatusIfExpected` 의 비교를 `val statusMatches = true` 로 바꿈(항상 저장)
- 테스트는 그대로 두고 같은 명령을 `--continue` 로 재실행: BUILD FAILED in 1m 4s
- StartExecutionHandlerTest: 48 tests, 11 failures. "given another worker already started the execution from a duplicate message" 의 4개(`it only attempts a conditional status update`, `it does not start the first stage again`, `it does not publish an event`, `it reads the stored status ...`), "execution was deleted" 1개, 그리고 `updateStatus` 를 `updateStatusIfExpected` 로 검증하던 기존 케이스 6개
  - 메시지 예: `Wanted but not invoked: executionRepository.updateStatusIfExpected(..., NOT_STARTED)` / `there were exactly 2 interactions with this mock: retrieve(...), updateStatus(...) at StartExecutionHandler.kt:99`
- SqlExecutionRepositoryTest: 21 tests, 1 failure
  - `a stale copy cannot move a completed execution back to RUNNING`: `Expecting value to be false but was true` (SqlExecutionRepositoryTest.kt:329)

## 2. #8209 (PR head 92bd5f89b3, 열린 PR)
```
./gradlew ... :orca:orca-sql:test --tests '*SqlExecutionRepositoryTest*'
```
- 기준: BUILD SUCCESSFUL in 1m 9s, 22 tests, 0 failures
- `.forUpdate()` 한 줄만 삭제(테스트 유지): 22 tests, 1 failure, 걸린 시간 약 55초
  - 실패한 것은 새 테스트 `waits for a concurrent writer and compares against the status it committed` 하나: `Expecting value to be false but was true` (SqlExecutionRepositoryTest.kt:377)
  - #8174 에서 넣은 직렬 테스트(`a stale copy cannot move ...`)는 `.forUpdate()` 가 없어도 통과한다. 잠금 없이는 통과하는 테스트라는 리뷰 지적(갭 3)과 일치.

## 3. #8208 (PR head d91a2724c3, 열린 PR)
```
./gradlew ... :orca:orca-queue:test --tests '*StartExecutionHandlerTest*' \
  :orca:orca-queue-sql:test --tests '*StartExecutionHandlerSqlTest*'
```
- 기준: BUILD SUCCESSFUL in 1m 9s. StartExecutionHandlerTest 51 tests 0 failures, StartExecutionHandlerSqlTest 1 test 0 failures (MySQL)
- `StartExecutionHandler.kt` 만 1f568ed149 버전(롤백이 무조건 `updateStatus`)으로 되돌림: BUILD FAILED in 53s
  - StartExecutionHandlerTest: 51 tests, 2 failures (`it restores execution status to NOT_STARTED only if it is still RUNNING`, `it does not overwrite the stored execution`; `Never wanted here: updateStatus ... StartExecutionHandler.kt:119`)
  - StartExecutionHandlerSqlTest: 1 test, 1 failure `a cancellation made while StartStage is being pushed survives the failed push()`: `expected: "CANCELED" but was: "RUNNING"` (StartExecutionHandlerSqlTest.kt:116). PR 본문의 실패 메시지와 같다.

## 재현하지 못한 것
- #7921 의 실제 장애(39건, 운영 SQL 지연 65초대)는 재현하지 않았다. 이슈 본문의 로그와 지표를 인용만 한다.
- #8207 의 (1) 재시작 소실, (2) 취소 소실 재현(CompleteExecutionHandler, RestartStageHandler)은 해당 테스트가 열린 PR 에 없고 이슈 본문에만 있어 돌리지 않았다. (3) 은 #8208 의 SQL 테스트로 확인.
- 전체 `orca:build`, 스포트리스 검사는 돌리지 않았다.
