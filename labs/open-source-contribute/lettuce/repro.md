# Lettuce 재현 기록 (2026-10-22)

대상: redis/lettuce #3952, #3954, #3955. 모두 머지됨(gh 로 2026-10-22 재확인).

| PR | 머지 시각(UTC) | 머지한 사람 | 머지 커밋 | 사람 리뷰 |
|---|---|---|---|---|
| #3952 | 2026-10-14 14:56:57 | a-TODO-rov | 26d42549 | 없음(봇 코멘트만) |
| #3954 | 2026-10-16 08:50:01 | a-TODO-rov | abcc00ef | 없음 |
| #3955 | 2026-10-16 08:50:28 | a-TODO-rov | 3da7a61f | 없음 |

## 환경

- 저장소: `git clone --filter=blob:none https://github.com/redis/lettuce.git` (3.8초) → scratchpad/repro/lettuce/repo
- CI JDK: `.github/workflows/run-tests.yml` 의 `java_version` 기본값 `'8'`(temurin). 실패 로그 스택에도 `Method.java:498`(JDK 8) 이 찍혀 있음.
  `doctests.yml` 은 JDK 11(temurin).
- 로컬에는 JDK 8 이 없음(설치본 11, 17, 21, 25, 26). **CI 워크플로 중 하나(doctests)가 쓰는 JDK 11 로 실행**했다.
  JDK 11.0.16 (JetBrains build). 테스트 대상이 생성자 인자 검증이라 JDK 버전 차이의 영향은 없다고 판단.
- Maven: `./mvnw` (Maven 3.9.16), `MAVEN_OPTS=-Xmx2g`, `-Djacoco.skip=true`.
- 단위 테스트만 실행. Redis·Docker 사용 안 함.
- 로그 중 `.git/gc.log already closed` (jgit, git-commit-id 계열 플러그인) 경고는 테스트와 무관.

## #3952

공통 명령:

```
export JAVA_HOME=$(/usr/libexec/java_home -v 11) MAVEN_OPTS=-Xmx2g
./mvnw -B test -Dtest=<클래스> -Dsurefire.failIfNoSpecifiedTests=false -Djacoco.skip=true
```

### (1) 머지 커밋 26d42549 에서 PR 이 추가한 테스트 → 통과

```
-Dtest=DefaultEndpointUnitTests
[INFO] Tests run: 25, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
Total time: 01:10 min (첫 실행, 의존성·컴파일 포함, 벽시계 72초)
```

### (2) 본 코드만 되돌림(테스트 유지) → 실패

```
git checkout 26d4254^ -- src/main/java/io/lettuce/core/protocol/DefaultEndpoint.java
# 142행: LettuceAssert.notNull(clientOptions, "ClientResources must not be null");

[ERROR] Tests run: 25, Failures: 1, Errors: 0, Skipped: 0
[ERROR] io.lettuce.core.protocol.DefaultEndpointUnitTests.shouldRejectNullClientResources <<< FAILURE!
java.lang.AssertionError:
Expecting code to raise a throwable.
	at ...DefaultEndpointUnitTests.shouldRejectNullClientResources(DefaultEndpointUnitTests.java:573)
[INFO] BUILD FAILURE
Total time: 35.698 s
```

PR 본문의 기록(before: Tests run 25, Failures 1 / after: Failures 0)과 같다.
`shouldRejectNullClientOptions` 는 두 상태 모두 통과(첫 번째 검증은 원래 맞았음).

### (3) 추가 확인: null 이 실제로 어디서 터지나 (임시 테스트, 저장소 사본에서만)

`NullResourcesProbeTests`: `new DefaultEndpoint(ClientOptions.create(), null)` 후
`new StatefulRedisConnectionImpl<>(endpoint, endpoint, StringCodec.UTF8, Duration.ofSeconds(1))`.

수정 전 코드:
```
PROBE constructed endpoint, getClientResources()=null
java.lang.NullPointerException
	at io.lettuce.core.RedisChannelHandler.<init>(RedisChannelHandler.java:81)
	at io.lettuce.core.StatefulRedisConnectionImpl.<init>(StatefulRedisConnectionImpl.java:100)
	at io.lettuce.core.StatefulRedisConnectionImpl.<init>(StatefulRedisConnectionImpl.java:85)
Total time: 32.492 s
```
(RedisChannelHandler.java:81 = `this.tracingEnabled = clientResources.tracing().isEnabled();`, 메시지 없는 NPE)

수정 후 코드:
```
java.lang.IllegalArgumentException: ClientResources must not be null
	at io.lettuce.core.internal.LettuceAssert.notNull(LettuceAssert.java:56)
	at io.lettuce.core.protocol.DefaultEndpoint.<init>(DefaultEndpoint.java:142)
Total time: 37.364 s
```

### (4) 버그가 들어온 시점 (git log -L)

```
git log -L141,142:src/main/java/io/lettuce/core/protocol/DefaultEndpoint.java
30bbbbdf 2016-08-10 Decouple CommandHandler #317          → ClientOptions 검증 한 줄로 파일 생성
b53dc554 2018-06-09 Add tracing support using Brave #782   → notNull(clientOptions, "ClientResources ...") 추가
26d42549 2026-10-14 (#3952)                                → clientResources 로 수정
```

## #3955 메시지 확인 (리플렉션 임시 테스트)

`CompressionCodec#copy` 는 private static 이고, 공개 경로(compress/decompress)에서는 내부에서 만든 스트림만 넘기므로 null 이 들어갈 수 없다. 메시지만 확인하려고 리플렉션으로 호출했다. 같은 테스트에서 `ClientOptions.builder().reauthenticateBehavior(null)` 도 호출.
트리는 26d42549 이고 두 파일만 각 시점 버전으로 바꿨다.

수정 전(abcc00e 버전의 CompressionCodec.java, ClientOptions.java):
```
PROBE copy(from, null) -> java.lang.IllegalArgumentException: From must not be null
PROBE reauthenticateBehavior(null) -> java.lang.IllegalArgumentException: ReuthenticatBehavior must not be null
Total time: 30.921 s
```
수정 후(3da7a61 버전):
```
PROBE copy(from, null) -> java.lang.IllegalArgumentException: To must not be null
PROBE reauthenticateBehavior(null) -> java.lang.IllegalArgumentException: ReauthenticateBehavior must not be null
Total time: 35.614 s
```

## 탐색 스크립트 재실행 (#3954·#3955 의 탐색 규칙)

세션 당시 스크립트는 남아 있지 않다. 세션 기록의 규칙을 그대로 다시 짜서 돌렸다.
스크립트: `scan-dup-assert.py`, `scan-msg-subject.py` (이 폴더). `src/main/java` 만 대상.

### 1차: 연속된 LettuceAssert 블록에서 같은 식별자를 두 번 검증

```
python3 -I scan-dup-assert.py <repo> <rev>
rev       블록수  같은 메서드(notNull 등)가 같은 식별자에 두 번
be963b39  59      1  (DefaultEndpoint.java clientOptions 141,142 → #3952 의 버그)
a761616a  58      0  (#3954·#3955 의 기준 커밋)
3da7a61   58      0
```
세션 기록의 58블록과 같다. 나머지 58블록은 전부 `notNull → notEmpty → noNullElements` 처럼 메서드가 서로 다른 단계적 검증이었다.
예) RedisCommandBuilder.java 819-821: `notNull(commands, ...)`, `notEmpty(commands, ...)`, `noNullElements(commands, ...)`.

### 2차: 메시지 첫 단어와 검증 변수명 불일치

```
python3 -I scan-msg-subject.py <repo> a761616a
규칙 A: 대소문자 무시 완전 일치가 아니면 후보 → 380건
규칙 B: 한쪽이 다른 쪽을 포함하면 제외(codec ↔ RedisCodec) → 145건
상위 패턴(B): type→"Command" 9, name→"Parameter" 7, value→"Parameter" 6, seconds→"Timeout" 4, script→"Lua" 4
두 규칙 모두에서 실제 결함 2건이 잡힘:
  ClientOptions.java:329  reauthenticateBehavior → "ReuthenticatBehavior"
  CompressionCodec.java:156  to → "From"
```
세션 당시 77건과는 숫자가 다르다(당시 규칙의 세부 필터가 기록에 없음). 글에는 77건(세션 기록)을 쓰고, 재실행은 "느슨한 규칙일수록 개념명 메시지가 더 많이 걸린다"는 확인으로만 쓴다.

## 그 밖에 확인한 것

- 메시지 문자열에 기대는 테스트: `RedisCommandBuilderUnitTests` 1290-1298 의 `geodistShouldRejectNullTo/From` 이 "To/From must not be null" 을 단언. `RedisCommandBuilder#geodist`(1331-1334) 의 올바른 검증용.
- #3954·#3955 head 커밋(10686c5d, 0c6eebe1)의 부모는 둘 다 a761616a (같은 기준 커밋).
- #3955 첫 CI(run 38845403888, head 0c6eebe1): Redis 8.10 잡만 실패.
  `RediSearchIntegrationTests.testFtAlterAddingNewFields:695 expected: 2L but was: 1L`, 전체 `Tests run: 4784, Failures: 1, Skipped: 88`. 나머지 Redis 7.2/7.4/8.2/8.8/8.12 성공.
- #3954 CI(run 38845399837, head 10686c5d): 여섯 버전 모두 성공.
- #3955 는 머지 직전 유지보수자(Aleksandar Todorov)가 main 을 브랜치에 병합(77ddd8a8, 08:50:10)했고 18초 뒤 머지. 77ddd8a8 에서 돈 CI 는 여섯 버전 모두 성공.
- 과거 오탈자 PR(gh): #2213 1파일 +2/-2, #1826 1파일 +1/-1, #1632 1파일 +3/-3, #1497 1파일 +2/-2, #3423 "docs: Fix various typos in documentation" 2파일 +14/-13. 모두 MERGED.
- 남은 오탈자: 현재 main 에도 스트림 API 6파일 `Get the length of a steam.` 이 남아 있음(`steam` 은 사전 단어라 오탈자 사전 검사에 안 걸림). `lenght`/`overriden`/`occured` 는 main 의 src 에서 0건.

## 정리

- 받은 저장소(scratchpad/repro/lettuce) 삭제 완료.
- 대상 저장소에 쓰기 작업 없음.
