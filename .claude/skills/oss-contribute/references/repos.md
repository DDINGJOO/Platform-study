# 저장소별 관례

기여하면서 확인한 것만 적는다. 새로 알게 되면 날짜와 함께 덧붙인다. 확인하지 않은 칸은 비운다.

## open-telemetry/opentelemetry-java-instrumentation

- 서명: EasyCLA(Individual) 최초 1회.
- 생성형 AI 정책: 커밋에 `Assisted-by` 트레일러를 단다. PR 전에 유지 여부를 사람에게 확인한다.
- `AGENTS.md`: PR 본문은 제목·체크리스트 없이 바로 쓴다. 줄을 강제로 개행하지 않는다. Gradle 출력을 파이프로 자르지 않는다. Java 25.
- 새 버전 전용 테스트는 별도 `JvmTestSuite` 로 만들고 `check` 에 연결한다.
- 재현은 main 빌드로 한다. 3.0 개발 중이라 2.x 릴리스와 span 이름·모듈 구성이 다르다.
- 기본 의존성에서 통과하고 최신 의존성(`-PtestLatestDeps=true`)에서만 실패하는 버그가 있다(#20661, Lettuce 5.1 대 최신).
- 리뷰어(laurit)가 직접 커밋을 얹어 구조를 바꾸는 일이 있다. 본인 기여 범위를 기록할 때 구분한다.
- 4건 모두 이틀 안에 머지됐다(2026-10-19 ~ 20).

## keycloak/keycloak

- **이슈 연결이 필수다.** 이슈가 없으면 영역 라벨·담당 팀이 안 붙고, 첫 기여자의 CI 워크플로 승인도 나지 않았다. 커밋 메시지에 `Closes #<이슈>`.
- 이슈는 웹 양식으로 연다. API 로 만들면 템플릿 라벨(`kind/bug`, `status/triage`)이 빠진다. 영역·팀 라벨은 봇이 몇 초 안에 붙인다.
- 이슈 연결 후 3일 만에 머지됐다(#53990).

## debezium/debezium

- 커밋 제목 접두사: `debezium/dbz#<이슈번호>`. 이슈는 `debezium/dbz` 저장소에 있다. 접두사가 없으면 봇이 지적한다.
- MySQL·MariaDB 문법 파일은 ANTLR grammars-v4 에서 가져온 복사본이다. 상류에도 같은 수정을 올리지 않으면 다음 동기화 때 사라진다. 리뷰어도 상류와 맞추기를 요청했다.
- 통합 테스트 CI 잡(MariaDB `ReadOnlyIncrementalSnapshotIT`, MySQL `MysqlDefaultValueIT`, Conductor·Server 컴파일, MongoDB 컨테이너 기동)이 변경과 무관하게 자주 실패한다. 같은 시기 다른 PR 의 같은 잡과 비교해 근거를 댄다. #8220 은 이 상태로 머지됐다.
- 메인테이너가 충돌 해결과 CI 확인을 요청한다. 충돌은 main 을 머지해 해결했다.

## antlr/grammars-v4

- 문법 폴더마다 예제 파일(`examples/`)로 파싱 테스트를 한다. 파싱은 되는데 트리가 틀린 문제는 예제 테스트로 드러나지 않는다. `TestRig -tree` 로 변경 전후 파스 트리를 비교해 PR 에 붙인다.
- deprecated 문법(Positive-Technologies MySQL)은 고치지 않는다.
- 이슈를 먼저 열고 PR 에서 연결했다(#5036 → #5037, #5038 → #5039). 일주일 안에 머지됐다.

## spinnaker/spinnaker

- 모노레포. 커밋 제목은 Conventional Commits(`fix(orca): ...`, `test(orca): ...`).
- SQL 테스트는 Testcontainers MySQL 을 쓴다. Docker 필요.
- 리뷰어(jasonmcintosh)가 승인하면서 후속 항목을 남기고 "이슈로 만들어 고치면 좋겠다" 고 했다. 후속은 이슈 하나(#8207) + PR 둘로 나눴다.
- 후속 PR 은 리뷰 요청이 자동으로 붙지 않았다. 5일 무반응 뒤 이슈에서 이전 리뷰어를 불렀다(2026-10-22).

## spring-cloud/spring-cloud-config

- DCO 서명(`git commit -s`). 포매터 spring-javaformat. JDK 17 로 검증.
- 리뷰어(ryanjbaxter)가 변경 요청을 여러 건 낸다. 항목마다 인라인으로 답하고, 동의하지 않는 항목은 테스트로 근거를 만들어 반박했다.
- 이슈 번호는 `gh-<번호>` 로 부른다. 이슈를 완전히 해결하지 않으면 `Fixes` 대신 `Related to`.

## spring-projects/* (spring-boot, spring-batch, spring-ai, spring-security)

- DCO 서명. 새 PR 에는 `status: waiting-for-triage` 라벨이 붙고 반응이 오기까지 오래 걸린다(10-09 에 올린 셋이 10-22 까지 무반응).
- spring-batch #5582: 이슈 #5580 을 먼저 열고 `Resolves #5580`.

## redis/lettuce

- CI 기본 JDK 8.
- Redis 버전별 통합 테스트 잡(예: RediSearch)이 간헐적으로 실패한다. 다른 Redis 버전 잡이 통과하면 무관하다는 근거가 된다.
- 오탈자·메시지 수정 같은 작은 PR 도 당일 머지됐다.
