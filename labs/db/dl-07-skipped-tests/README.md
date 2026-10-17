# dl-07 동시성 테스트가 통과한 게 아니라 실행되지 않았을 때

MySQL 교착 시리즈 7편의 실습. 1편의 "첫 방문 동시 요청 3개" 패턴(INSERT IGNORE → SELECT … FOR UPDATE)을
같은 테스트 하나로 H2, 실제 MySQL 8.4, 그리고 Docker 에 붙지 못한 Testcontainers 위에서 돌려 결과를 비교한다.

| 클래스 | 하는 일 |
|---|---|
| `FirstVisitScenario` | 라운드마다 새 키로 스레드 3개를 `CountDownLatch` 로 동시에 출발시킨다. `buggy` 는 한 트랜잭션에서 INSERT IGNORE → FOR UPDATE → UPDATE, `fixed` 는 INSERT IGNORE 를 자동 커밋으로 먼저 끝낸다 |
| `FirstVisitContract` | 기대: 30 라운드 90 요청이 전부 성공하고 키마다 cnt = 3 |
| `H2MysqlModeTest` | 같은 기대를 H2 `MODE=MySQL` 에서 |
| `H2LockProbeTest` | H2 에서 세 세션으로 1편의 순서를 만든다: A 미커밋 삽입, B·C 함께 대기, 둘 다 INSERT IGNORE 를 끝낸 뒤 둘 다 FOR UPDATE. 시각만 찍는다 |
| `SkippingMysqlTest` | `@Testcontainers(disabledWithoutDocker = true)` + `mysql:8.4` |
| `StrictMysqlTest` | `@Testcontainers` 기본값 + `mysql:8.4` |

## 실행

JDK 25(툴체인), Docker. Gradle 은 wrapper(9.8.1) 가 받는다.

```bash
./scripts/run_all.sh h2       # Docker 없이: H2 에서 고치기 전 코드가 초록인지
./scripts/run_all.sh skip     # DOCKER_HOST 를 틀리게, Testcontainers 1.19.8/1.21.3/1.21.4/2.0.5
./scripts/run_all.sh noskip   # skip 0 검사 태스크, 조건 비활성화
./scripts/run_all.sh mysql    # 실제 MySQL 로 buggy/fixed 세 바퀴씩
```

빌드 속성: `-PtcVersion=1.19.8`(기본 2.0.5), `-Pimpl=fixed`(기본 buggy), `-PnoSkip`(skip 이 있으면 `checkNoSkipped` 가 빌드를 실패시킴),
`-Pdeactivate='org.testcontainers.*'`(JUnit `junit.jupiter.conditions.deactivate`), `-PapiVersion=1.44`(docker-java 의 `api.version`).

## 결과

`results/summary.txt` 에 실행 전체 요약, `results/` 의 나머지는 글의 실행 화면 원자료(로컬 경로를 뺀 발췌)다.
`out/` 은 원출력이라 커밋하지 않는다.

- H2 MODE=MySQL: buggy 도 90/90 성공. 세 세션 탐침에서도 B·C 가 교착 없이 차례로 끝났다(최종 cnt 3)
- MySQL 8.4 (Testcontainers 2.0.5): buggy 는 세 바퀴 모두 30 라운드 중 30 라운드에서 1213, fixed 는 세 바퀴 모두 90/90
- Docker 29.5.3(최소 API 1.40) 에서 Testcontainers 1.19.8, 1.21.3 은 400 으로 Docker 를 못 찾고 SKIPPED + BUILD SUCCESSFUL. 1.21.4, 2.0.5 는 붙는다
- 1.19.8 에 `-PapiVersion=1.44` 를 주면 붙는다
- `assumeTrue(false)` 도 XML 에 skipped 로 남아 `checkNoSkipped` 에 걸린다(`results/assume-noskip.txt`)
- `testLogging` 설정이 없는 Gradle 9.8.1 기본 콘솔은 SKIPPED 줄을 찍지 않는다(`results/gradle-default-console.txt`). 이 실습의 화면에 SKIPPED 가 보이는 건 `testLogging` 에 skipped 를 켰기 때문이다
- `checkNoSkipped` 는 결과 디렉터리가 없거나 tests=0 이면 실패한다. 멀티 모듈이면 통합 테스트가 있는 모듈에만 붙인다
- `DOCKER_HOST` 를 아무도 듣지 않는 주소로 바꿔도 이 머신에서는 skip 되지 않았다. 2.0.5 가 "not listening" 경고 뒤 로컬 유닉스 소켓으로 넘어갔다

버전: Docker Desktop 4.78.0 (Engine 29.5.3), Gradle 9.8.1, Java 25.0.3, JUnit 5.12.2, H2 2.4.240, Connector/J 9.7.0, Apple Silicon.
