# repro: Lettuce sync 타임아웃 span 상태

공통: Lettuce `blpop(2, key)` 를 sync API 로 보내고 클라이언트 쪽 타임아웃을 먼저 일으킨다. 호출자는 항상 `RedisCommandTimeoutException` 을 받는다(두 케이스 모두 단언 통과). Redis 는 Testcontainers(`redis:6.2.3-alpine`). JDK 25, `-Ddev=true`(main 의 -Werror 때문).
- A: `connection.setTimeout(300ms)`  — 전형적인 sync 타임아웃
- B: `TimeoutOptions.enabled(100ms)` — #20661 의 async 테스트와 같은 설정
- 값은 JUnit XML 의 `SPANDUMP[...]` 줄. "의존성" 칸의 기본 = 모듈이 기본으로 거는 Lettuce(라이브러리 5.1.0, javaagent lettuce51Test 5.1.x), 최신 = `-PtestLatestDeps=true`(javaagent 는 `lettuce65Test`).

| 대상 | 의존성 | A (connection timeout) | B (TimeoutOptions) | 로그 |
|---|---|---|---|---|
| main 079a5af0e2 라이브러리 | 기본 | **UNSET**, error.type 없음 | ERROR, `_OTHER` | 04 |
| main 라이브러리 | 최신 | ERROR, `CancellationException` | ERROR, `CancellationException` | 05 |
| main javaagent | 기본(5.1.x) | **UNSET**, error.type 없음 | ERROR, `RedisCommandTimeoutException` | 09 |
| main javaagent | 최신 | **UNSET**, error.type 없음 | **UNSET**, error.type 없음 | 10 |
| v2.32.0 라이브러리 | 기본 | UNSET | UNSET | 07 |
| v2.32.0 라이브러리 | 최신 | ERROR(exception 이벤트) | ERROR(exception 이벤트) | 08 |
| v2.32.0 javaagent(5.1 모듈) | 기본 | UNSET | ERROR(exception 이벤트) | 12 |
| v2.32.0 javaagent(5.1 모듈) | 최신 | ERROR(exception 이벤트) | ERROR(exception 이벤트) | 13 |

- 회귀로 확인된 칸: **main javaagent + 최신 Lettuce + sync 타임아웃(A, B)**. 2.32.0 은 ERROR, main 은 UNSET.
- 같은 UNSET 이 2.x 에도 있던 칸(회귀 아님): 라이브러리 기본(5.1.0)의 A, javaagent 기본(5.1.0)의 A. Lettuce 5.1.0 Tracing SPI 가 예외를 주지 않는 한계.
- 메모의 "2.x 에서 에러" 는 최신 Lettuce 를 쓴 javaagent 에서만 맞다. 메모는 대상을 적지 않았고 이 표로 대상을 확정했다.
- 실행 시간: 로그 끝 `exit=… elapsed=…` 참조. 첫 컴파일이 12분(07)이고 캐시가 있으면 46~124초.
- 되돌림 검증(본 코드만 되돌리면 실패하는지)은 **하지 않았다**. 수정이 없는 이슈 초안 작업이다.
