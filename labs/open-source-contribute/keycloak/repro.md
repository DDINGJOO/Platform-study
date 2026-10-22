# Keycloak 재현 기록 (2026-10-22)

대상: keycloak/keycloak #53990 (gh 로 2026-10-22 재확인: MERGED, 2026-10-19T17:06:11Z, mposolda, 머지 커밋 082ead23).

## 환경

- 저장소: `git init` 후 `git fetch --depth=2 --filter=blob:none origin 082ead23...` (1초 미만) → scratchpad/repro/keycloak. 끝나고 삭제.
- CI JDK: `.github/actions/java-setup/action.yml` 의 기본값 `25`(temurin). 로컬 Homebrew OpenJDK 25.0.4 로 실행(배포판만 다름).
- Maven: `./mvnw` 3.9.16, `MAVEN_OPTS=-Xmx2g`, 병렬 옵션 없음. 의존 모듈은 `-am` 으로 같은 리액터에서 컴파일(install 불필요, 이미 로컬 저장소에 의존성이 있어 내려받기 없음).
- Docker·DB 사용 안 함. 단위 테스트만.

공통 명령:

```
export JAVA_HOME=/opt/homebrew/Cellar/openjdk@25/25.0.4/libexec/openjdk.jdk/Contents/Home MAVEN_OPTS=-Xmx2g
./mvnw -B -pl services -am test -Dtest='<클래스들>' -Dsurefire.failIfNoSpecifiedTests=false -Dcheckstyle.skip -Dlicense.skip
```

## (1) 머지 커밋 082ead23, 테스트 `AccessTokenContextTest,*TokenContext*`

- AccessTokenContextTest: Tests run: 4, Failures: 0
- DefaultTokenContextEncoderProviderTest: Tests run: 6, Failures: 0
- 합계 Tests run: 10, Failures: 0, BUILD SUCCESS (Total time 35.275 s, 첫 컴파일 포함, 벽시계 37.9 s)
- PR 본문의 `Tests run: 10, Failures: 0` 과 같다.

## (2) 본 코드만 되돌림 (`git checkout HEAD^ -- .../AccessTokenContext.java`, 테스트 유지)

테스트 `AccessTokenContextTest,ProbeNullRawTokenIdTest`:

```
[ERROR] Tests run: 4, Failures: 1, ... in AccessTokenContextTest
[ERROR] AccessTokenContextTest.shouldRejectNullRawTokenId -- FAILURE!
java.lang.AssertionError: expected java.lang.NullPointerException to be thrown, but nothing was thrown
	at org.keycloak.protocol.oidc.encode.AccessTokenContextTest.shouldRejectNullRawTokenId(AccessTokenContextTest.java:49)
[ERROR] Tests run: 5, Failures: 1 (프로브 1개 포함)   BUILD FAILURE  (11.865 s)
```

PR 본문의 `before: Tests run: 4, Failures: 1` 과 같다. 나머지 3개 null 검증 테스트는 통과.

## (3) 임시 프로브 (`ProbeNullRawTokenIdTest.java.txt`, 사본에서만 실행하고 삭제)

되돌린 상태:

```
PROBE constructor: accepted, getRawTokenId()=null
PROBE encodeTokenId=onrtro:null
PROBE json: accepted, encodeTokenId=onrtro:null
```

머지 커밋 상태(Tests run: 5, Failures: 0, BUILD SUCCESS, 12.544 s):

```
PROBE constructor: java.lang.NullPointerException: Null rawTokenId not allowed
PROBE json: ValueInstantiationException root=java.lang.NullPointerException: Null rawTokenId not allowed
```

## 이슈·PR 상태 (gh 읽기 전용)

- #54050: 2026-10-16T03:39Z 생성, 라벨 없음, 03:42Z 중복으로 닫음(duplicate of #54051).
- #54051: 2026-10-16T03:45:19Z 생성. 이벤트: DDINGJOO 가 `kind/bug`, `status/triage`(템플릿), keycloak-github-bot 이 `area/oidc` → `team/core-protocols`(1~4초 안). 03:45:37 에 PR 에서 참조. 10-19 13:42 mposolda 가 priority 처리, 17:06 PR 머지와 함께 닫힘, `release/27.0.0` 라벨.
- PR: 10-14T22:39Z 생성(UTC), 10-16T03:39Z 와 03:45Z 에 force push(Closes 추가), 10-18T08:56Z force push, 10-19T13:41Z mposolda 지정, 14:01Z Spotless 수정 force push, 17:06Z 승인과 머지.

## 재현하지 못한 것

- 최초 코드가 언제 들어왔는지(blame): 얕은 클론이라 이력이 없고, 이번 글의 근거에도 넣지 않음.
- 첫 기여자 워크플로 승인 대기(action_required)는 세션 기록(10-16)에만 있고 현재 API 로는 재확인할 수 없음.
- Spotless 실패 로그 원문: 확인하지 않음(PR 코멘트의 본인 설명만 사용).
