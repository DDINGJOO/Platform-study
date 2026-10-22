# journal: Lettuce sync API 타임아웃이 성공 span 으로 기록된다? (3.0 회귀 주장)

작업 시각은 KST(로컬) 2026-10-22. 확인하지 않은 것은 "확인 안 함" 으로 적는다.
출발점은 2026-10-17 에 적어 둔 메모 한 줄("Lettuce sync 타임아웃 성공 기록(3.0 회귀)은 설계 문제라 이슈로 먼저")이고, 상세 기록이 없다. 그래서 메모를 사실로 받지 않고 재현부터 한다.

## 사전 읽기
- SKILL.md, references/repos.md, kafka-unknown-offset/journal.md 를 읽었다. 그 건의 함정(main 의 -Werror 때문에 `-Ddev=true`, zsh 단어 분리, BSD sed)을 이번에도 적용한다. 실행 스크립트는 `run.sh`(로그 이름을 첫 인자로 받고 종료 코드·소요 시간을 로그 끝에 적는다).
- #20661(머지, async 타임아웃에서 `error.type` 가 Redis 오류 타입으로 잘못 나오던 것을 고침)의 코멘트를 읽었다. 리뷰어 trask 가 `OpenTelemetryTracing.finishFromOutput` 쪽을 리팩터링했다. 그 PR 의 테스트(`testCommandTimeoutDoesNotReportRedisErrorType`)는 **async** API 로만 타임아웃을 검증하고, 상태가 에러(`StatusData.error()`)임을 이미 단언한다. sync 경로는 비교 대상이 없다.

## 클론, 중복 검색
- `git clone --filter=blob:none` → scratchpad/otel-lettuce. HEAD = `079a5af0e2f5 2026-10-22 Restore AWS Lambda baseline dependency coverage (#20823)`. 최신 2.x 태그 = v2.32.0 (v2.31.0, v2.31.1 도 있음).
- 중복 검색(읽기만). 처음에 `--state all` 을 줬는데 `gh search` 는 `open|closed` 만 받아서 첫 시도(`logs/02-duplicate-search.log`)는 전부 오류/빈 결과였다. 틀린 것을 지우지 않고 로그에 남겼다. `--state` 를 빼고 다시 했다(`logs/02b-duplicate-search-broad.log`): `lettuce` 한 단어로 이슈 100건·PR 100건을 받아 제목을 훑었다.
- 후보와 읽은 것(`logs/03-related-items.log`):
  - 이슈 #19814 "[Lettuce] Redis timeouts in OpenTelemetry 2.30.0+"(open): 댓글만 읽었다. 제목은 "타임아웃이 난다" 는 보고이고 span 상태가 성공이라는 보고가 아니다(원문 본문은 `gh issue view` 기본 출력에서 확인 못 함 → 본문 확인 안 함).
  - PR #20784 "Classify Lettuce 5.1 message-only failures"(merged): "Older Lettuce tracing drops the Throwable on command timeouts, leaving failed spans and duration metrics without error.type" — `error.type` 문제이고 상태 문제가 아니다.
  - PR #20793, #20778(open): Redis 오류 접두사 분류. 상태 문제 아님.
  - PR #19075(merged): [5.1.0, 6.0.0) 에서 Redis 명령 오류의 span status 를 설정. 2.x 에서 "에러 span 상태" 를 고친 이력이다. 이번 건과 같은 주제가 아니다.
  - #20457 "Improve error.type classification", #20681 "Track repository-wide error.type coverage", #20679: 추적용 이슈, 본문 읽지 않음(확인 안 함).
- 판단: sync 타임아웃이 성공으로 기록된다는 이슈·PR 은 제목 기준으로 못 찾았다. 본문 검색(`--match body`)은 안 했다(확인 안 함).

## 코드 읽기: 어디서 span 이 끝나는가
- 라이브러리 계측: `instrumentation/lettuce/lettuce-5.1/library/.../OpenTelemetryTracing.java`. `OpenTelemetrySpan.finish()` 는 `taggedErrorMessage` 와 `error` 로 `finishFromOutput`, Lettuce 6+ 에서는 `start(RedisCommand)` 에서 `CompleteableCommand.onComplete((o, throwable) -> ...)` 로 span 을 끝낸다.
- 에이전트: 5.1 javaagent 모듈은 #20533 에서 제거됐다. `lettuce-5.0/javaagent` 가 `lettuce51Test`/`lettuce60Test`/`lettuce65Test` 스위트로 5.1+ 도 시험한다(`build.gradle.kts`). 따라서 javaagent 쪽 테스트는 `lettuce-5.0/javaagent/src/test/.../LettuceSyncClientTest.java`.
- 첫 가설(아직 검증 전): sync 프록시가 타임아웃 때 `cmd.cancel(true)` 로 취소하면 `onComplete` 의 throwable 이 CancellationException 이거나 null 이라서 span 이 어떻게 끝나는지가 달라질 수 있다. 실험으로 확인한다.

## 테스트 작성
- 파일: `lettuce-5.1/testing/.../AbstractLettuceSyncClientTest.java`(라이브러리 `LettuceSyncClientTest` 가 상속)에 테스트 2개와 span 을 stdout 으로 찍는 `dumpSpans` 를 추가.
  - A `testSyncCommandTimeoutViaConnectionTimeout`: `connection.setTimeout(300ms)` 후 `sync().blpop(2, key)`. 전형적인 sync 타임아웃(동기 프록시가 기다리다 취소).
  - B `testSyncCommandTimeoutViaTimeoutOptions`: #20661 의 async 테스트와 같은 `TimeoutOptions.enabled(100ms)` 인데 sync API 로 호출.
  - 두 테스트 모두 `RedisCommandTimeoutException` 이 던져지는지 먼저 단언하고, span 이 `StatusData.error()` 인지 단언한다. 메모가 맞다면 이 단언이 실패해야 한다. 스팬 내용은 stdout 에 `SPANDUMP[...]` 로 찍는다.

## 17:0x 첫 실행: main 라이브러리(기본 의존성 = Lettuce 5.1.0)
- 명령: `run.sh 04-main-lib-default :instrumentation:lettuce:lettuce-5.1:library:test --tests '*LettuceSyncClientTest.testSyncCommandTimeout*'` (JDK 25, `-Ddev=true`, `--no-daemon --max-workers=2 -Xmx2g`). 로그 `logs/04-main-lib-default.log`, XML `logs/04-main-lib-default-TEST.xml`. `exit=1 elapsed=62s`.
- 결과: A(connection timeout) = status **UNSET**, `error.type` 없음. B(TimeoutOptions) = status ERROR, `error.type=_OTHER`.
- 해석: A 는 메모의 주장과 같은 모양이다. 그러나 이 경로는 Lettuce 5.1.0 의 Tracing SPI 가 예외를 주지 않는 한계이고(#20784 가 같은 이유로 B 를 `_OTHER` 로 분류), 2.x 에서도 같은지 봐야 회귀인지 알 수 있다.

## 최신 의존성(라이브러리)
- `-PtestLatestDeps=true`, 로그 `05-main-lib-latest.log` (`exit=0 elapsed=48s`, 단언이 통과했다는 뜻).
- 결과: A, B 모두 **ERROR**, `error.type=java.util.concurrent.CancellationException`, `exception` 이벤트 있음.
- 새로 안 점(예상과 다름): sync 프록시는 타임아웃 때 명령을 `cancel(true)` 하고 `RedisCommandTimeoutException` 을 **호출자에게만** 던진다. 명령 쪽에 보이는 예외는 CancellationException 이다. B(TimeoutOptions) 도 sync 대기 시간이 같은 100ms 라서 sync 쪽 cancel 이 먼저 일어난다(Lettuce `Futures.awaitOrCancel`, `FutureSyncInvocationHandler.getTimeoutNs`: scratchpad/lettuce-src/ 의 main 소스에서 읽음, 어떤 릴리스인지는 확인 안 함). 그래서 `error.type` 이 `RedisCommandTimeoutException` 이 아니라 `CancellationException` 이다. 메모에는 없던 부수 문제.

## 2.32.0 라이브러리 비교
- 수정 전 코드 보관: `git diff > logs/06-main-test.patch` 후 `git stash`, `git checkout v2.32.0`, `git apply --3way`(깨끗하게 적용됨).
- `07-v2.32.0-lib-default.log`: `exit=1 elapsed=757s`(컴파일·내려받기 포함 12분). A, B 모두 **UNSET**. 즉 main 보다 나쁘다(B 가 main 에서 #20784 로 ERROR 가 됨). 라이브러리 기본 의존성에서의 UNSET 은 3.0 회귀가 아니다.
- `08-v2.32.0-lib-latest.log`: A, B 모두 ERROR + `exception` 이벤트 (`error.type` 속성은 2.x 에서 없고 old semconv).
- 결론(라이브러리): main 과 2.32.0 이 같은 방향이다. 회귀 없음.

## 틀린 판단: 메모는 "라이브러리" 를 가리키지 않았다
- 여기까지 라이브러리에서는 회귀가 안 나왔다. 메모의 "2.x 에서는 에러, main 에서 바뀜" 이 어느 쪽인지 몰라서 javaagent 를 본다. 지시에서 둘 다 확인하라고 했다.
- `#20533 Remove Lettuce 5.1 javaagent module`(2026-10-13)을 보고 의심: 5.1+ 에이전트가 `lettuce-5.0` 모듈의 AsyncCommand 기반 경로로 바뀌었다. 그 경로의 `EndCommandAsyncBiFunction.end` 는 `CancellationException` 이면 에러가 아니라고 보고 `throwable = null` 로 만든다(파일:줄은 analysis.md).

## javaagent 테스트
- `lettuce-5.0/javaagent/src/test/.../LettuceSyncClientTest.java` 에 같은 A, B 테스트를 추가(`dumpSpans` 포함). `git diff > logs/11-main-test-v2.patch`.
- `09-main-agent-lettuce51.log` (`lettuce51Test`, Lettuce 5.1.x 기본): A **UNSET**, B ERROR(`error.type=RedisCommandTimeoutException`, exception 이벤트). (`exit=1` 은 내 단언이 A 에서 실패한 것)
- `10-main-agent-lettuce65-latest.log` (`lettuce65Test -PtestLatestDeps=true`): A, B **모두 UNSET**, `error.type` 없음, 이벤트 없음. 호출자는 `RedisCommandTimeoutException` 을 받는다.
- v2.32.0 에서 `lettuce-5.1:javaagent`(`12`, `13` 로그): 기본(5.1.0) A UNSET / B ERROR, 최신 A, B 모두 **ERROR** + exception 이벤트.
  - 같은 테스트를 `git apply --3way` 로 v2.32.0 에 적용(5.1 javaagent 는 라이브러리 `AbstractLettuceSyncClientTest` 를 상속하므로 라이브러리 쪽 테스트가 그대로 돈다).
- 회귀 확인: 최신 Lettuce + javaagent + sync 타임아웃은 2.32.0 ERROR → main UNSET.

## 의도 여부 조사
- `EndCommandAsyncBiFunction` 의 취소 예외 면제는 2021-05-31 `7d46c336b0 (#3125 Update lettuce-5.0 to Instrumenter API)` 에서 들어왔고(blame), 리액티브 구독 취소를 에러로 안 치려는 의도로 보인다. 테스트 `LettuceReactiveClientTest.testCommandCancelOnMonoPublisher`, `testCommandCancelAfter2OnFluxPublisher`(실험적 속성 `lettuce.command.cancelled`)가 그 동작을 고정한다. 의도 자체는 확인했으나 "sync 타임아웃" 을 염두에 둔 것인지는 근거 없음(확인 안 함).
- #20533 본문·CHANGELOG(123-128줄)는 계측 범위 이름, 인코딩 이벤트, 설정 키 변경만 "breaking" 으로 적었다. 에러 상태가 달라진다는 언급은 없다. sync 타임아웃 테스트도 에이전트 쪽에는 없다.
- 2.32.0 에서도 v3-preview 를 켜면 `lettuce-5.0` 모듈이 5.1+ 를 맡는 구조였다(`LettuceInstrumentationModule` 의 `isV3Preview()`). 이 모드로 2.32.0 을 돌려 보지는 않았다(확인 안 함). 3.0 이 그 모드를 기본으로 만든 것이므로 2.x 기본 모드와의 차이가 3.0 회귀로 보인다.

## 2026-10-22 이슈 제출
- API 로 #20846 을 먼저 만들었더니 양식 라벨(bug, needs triage)이 빠졌다(Keycloak 때와 같은 일). 사용자가 웹 양식으로 #20847 을 다시 열었고 라벨이 붙었다. #20846 은 닫힘.
- #20847 에 "수정 중, 곧 PR. 리액티브 구독 취소는 그대로 두고 sync 자체 타임아웃의 취소만 RedisCommandTimeoutException 으로 끝내는 방향" 코멘트.
- 교훈: 이슈 양식이 있는 저장소는 처음부터 웹 양식으로 연다. repos.md 의 Keycloak 항목에만 있던 규칙을 SKILL.md 공통 규칙으로 올린다.
