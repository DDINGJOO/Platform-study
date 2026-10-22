# journal: Reactor Sinks 첫 연산자 · resetOnEachOperator 후속

작업 시각은 KST 2026-10-22. 확인하지 않은 것은 "확인 안 함" 으로 표시한다. 틀린 판단도 지우지 않는다.
클론: scratchpad `otel-reactor/`, main `079a5af0e2` (2026-10-22 "Restore AWS Lambda baseline dependency coverage (#20823)"). JAVA_HOME 은 25.0.4, 모든 Gradle 에 `-Ddev=true`(Kafka 작업의 -Werror 함정 때문, 이번에는 로컬 빌드가 그 오류 없이 통과했지만 같은 옵션을 유지).

## 16:5x 읽기: 규칙, Kafka 기록, #20659
- `SKILL.md`, `references/repos.md`, Kafka 작업 journal/repro 를 읽음. 서명(Assisted-by), AGENTS.md 규칙(Gradle 출력 파이프 금지, 파일로 리다이렉트) 동일.
- #20659(머지, "Pass downstream demand through runWithContext for Flux"): 본문과 리뷰를 읽음. 리뷰는 trask 승인("Thanks!"), laurit 승인, Copilot 요약뿐이고 후속 단서가 되는 논의는 없다. PR 본문에 "열린 #20643 은 새 3-인자 runWithContext 오버로드를 추가하지만 2-인자 경로는 바꾸지 않는다" 는 문장이 있다(내 PR 이었음). 후속으로 Sinks·reset 을 언급한 곳은 못 찾음. 인라인 리뷰 코멘트는 `gh api .../pulls/20659/comments` 로 요청했지만 비어 있었다(출력 없음).
- 처음 `echo ===...` 를 쓴 명령이 zsh 에서 `=` 확장 오류(`===== not found`)로 실패해 첫 Kafka journal 출력이 중간에 끊김. 이후 구분선 echo 를 쓰지 않음.

## 17:00 중복 검색
- 첫 시도: `gh search ... --state all` → `invalid argument "all"`(gh search 는 open|closed 만 허용). 로그 `logs/00a-duplicate-search-failed-state-all.log`(헤더와 오류줄만 남김).
- 재시도: `--state` 없이(기본이 전 상태) 12개 질의 x 이슈/PR. `logs/00-duplicate-search.log`.
  - `reactor sinks`, `Sinks.many`, `Sinks.one`, `reactor Sinks context`, `reactor context first operator`, `reactor emitNext context` 등 Sinks 계열: 이슈·PR 모두 0건.
  - 관련 후보(제목만 봄, 본문은 안 읽음 = 확인 안 함): PR #18258 "Reactor 3.1: reset schedulers hook in resetOnEachOperator()"(머지), 이슈 #18932 "Hooks.onEachOperator + Operators.lift ... allocation amplification"(닫힘), PR #20643(열림), #20659(머지).
- H2 를 찾은 뒤 2차 검색: `Hooks.resetOnEachOperator`, `HooksInstrumentation`, `reactor registerOnEachOperator`, `reactor hook removed` 등 8개. 같은 증상의 이슈·PR 없음. 이슈 #2777 "Reactor javaagent instrumentation tests pass even with advice code commented out"(2022, 닫힘)은 제목만 봄(확인 안 함).
- 판단: 중복 없음. `gh search` 는 모든 단어가 일치해야 해서 놓쳤을 가능성은 남는다.

## 17:02 코드 읽기와 가설
읽은 파일(모두 `instrumentation/reactor/reactor-3.1/`): `library/.../ContextPropagationOperator.java`, `TracingSubscriber.java`, `HooksTest.java`, `javaagent/.../HooksInstrumentation.java`, `testing/.../AbstractReactorCoreTest.java`.

- H1. `Sinks.many()`/`Sinks.one()` 으로 만든 Flux/Mono 에서 컨텍스트가 안 붙는다. 근거 없이 세운 가설. 단서: 기존 테스트에 `Flux.create` 로 외부 구동 publisher 를 만든 `propagatesContextValuesFromExternallyDrivenPublisher` 가 있는데 Sinks 용은 없다. `grep Sinks` 로 reactor 모듈에 사용처 0건.
- H2. 에이전트 환경에서 앱이 `Hooks.resetOnEachOperator()` 를 부르면 훅이 사라지고 복구되지 않는다. 단서: `HooksInstrumentation` 이 `resetOnEachOperator` 메서드 끝에서 `registerOnEachOperator()` 를 다시 호출하는데(= 재설치 의도), `registerOnEachOperator()` 는 `if (enabled) return;` 으로 시작한다. 앱이 직접 reset-all 하면 `enabled` 는 여전히 true 라서 재설치가 무시될 것으로 예상.
- H3. `ContextPropagationOperator` 인스턴스가 여러 개일 때 `enabled`·훅 키는 static 인데 strategy 는 인스턴스별이라, 등록하지 않은 인스턴스의 reset 이 다른 인스턴스의 `AsyncOperationEndStrategy` 를 남긴다. 코드 읽기에서 의심.

## 17:07 H1 실험 (javaagent version34Test, Reactor 3.4.0)
- Sinks 는 3.4 부터라 라이브러리 `test`(3.1.0)에서는 컴파일되지 않는다. 에이전트가 붙는 `javaagent` 모듈의 `version34Test` 소스셋에 임시 탐색 테스트를 둠. 소스 `logs/01-SinksExploreTest.java.txt`.
- 방법: 컨텍스트 키를 가진 컨텍스트에서 subscribe, 다른 span("producer") 안에서 emit, 구독 콜백이 본 키를 기록.
- 명령: `./gradlew ... :instrumentation:reactor:reactor-3.1:javaagent:version34Test --tests '*SinksExploreTest' -i > logs/01-explore-sinks-v34.log 2>&1` → `exit=0 elapsed=51s`.
- 결과(로그의 `SINKS-RESULT`):
  - `Sinks.many().unicast().asFlux().subscribe(l)` → `null` (컨텍스트 안 붙음)
  - `...asFlux().map(...).subscribe(l)` → `subscribe-time` (붙음)
  - `...asFlux().doOnNext(...).subscribe(l)` → `subscribe-time`
  - `Sinks.one().asMono().subscribe(l)` → `null`, `.map(...)` 붙이면 `subscribe-time`
  - 대조군 `Flux.create(...).subscribe(l)` → `subscribe-time`
- 해석: 연산자가 하나라도 붙으면 정상이고, 연산자 없이 Sinks 의 Flux/Mono 를 직접 subscribe 하면 컨텍스트가 안 붙는다. "첫 연산자" 메모와 맞는 증상일 수 있다(메모의 정확한 의미는 확인 안 함).
- 원인 추정(코드 읽기, 실험으로 분리 확인은 안 함): 계측은 `Hooks.onEachOperator` 의 lift 로 `onAssembly` 를 거친 연산자 출력에만 `TracingSubscriber` 를 붙인다. `Flux.create` 는 `onAssembly` 를 거치지만 Sinks 의 `asFlux()`/`asMono()` 는 거치지 않는 것으로 보인다(Reactor 소스를 직접 열어 확인하지는 않음 = 확인 안 함). 즉 Sinks 가 나쁜 게 아니라 "연산자 없는 직접 subscribe" 가 훅 대상이 아니다.
- 판단: 이 저장소 안에서 고칠 버그로 보지 않는다. 고치려면 `Hooks.onLastOperator` 로 subscribe 지점을 추가로 가로채는 설계 변경이 필요하고(시도 안 함), 그건 매 체인의 마지막에 래핑이 하나 더 붙는 비용·변경 범위가 있어 메인테이너 합의가 먼저다. 이슈 보고만 하는 것도 가능하지만 이번 범위(재현→수정)에서는 기록하고 멈춘다.

## 17:10 H2 실험 (javaagent test, Reactor 3.1.0)
- 첫 시도의 탐침이 틀렸다. 지연 Mono(`delayElement`)로 span 이 보이는지 검사했더니 reset 후에도 `parent-visible`. 이유: 에이전트의 executor 계측이 Reactor 훅과 무관하게 스레드를 넘어 컨텍스트를 전달하기 때문에 훅이 없어도 통과한다. 즉 이 탐침은 훅 유무를 구분하지 못한다. 로그 `logs/02a-explore-hooks-reset-flawed-probe.log`.
- 바꾼 탐침: H1 과 같은 "외부 구동 publisher + subscribe 시점 컨텍스트" 방식(`Flux.create`). 훅이 없으면 콜백에서 키가 `null`. 소스 `logs/02-HooksExploreTest.java.txt`.
- 명령: `... :javaagent:test --tests '*HooksExploreTest' -i > logs/02-explore-hooks-reset.log 2>&1` → `exit=0 elapsed=9s`(테스트는 관찰만 하고 단정하지 않음).
- 결과: baseline `subscribe-time`, `Hooks.resetOnEachOperator("some-other-key")` 후 `subscribe-time`, `Hooks.resetOnEachOperator()` 후 `null`. **H2 재현.**
- 확인한 것: `Hooks.resetOnEachOperator()` 호출이 끝나면 훅이 사라지고, 에이전트의 재등록 advice 는 돌았을 텐데도 복구되지 않는다. 실제로 advice 가 호출되었는지는 로그로 직접 확인하지 않았다(확인 안 함). `enabled` 가 true 라서 early return 한다는 것은 코드 읽기에서 나온 설명이고, 수정 후 통과로 간접 확인했다.

## 17:12 H3 실험 (library test)
- 임시 테스트 `logs/03-MultiInstanceExploreTest.java.txt`: A.register → B(미등록).reset → A.reset, 각 단계에서 `AsyncOperationEndStrategies.instance().resolveStrategy(Mono.class) != null`.
- 명령: `... :library:test --tests '*MultiInstanceExploreTest' -i > logs/03-explore-multi-instance.log 2>&1` → `exit=0 elapsed=25s`.
- 결과: 세 단계 모두 `true`. 즉 A 가 등록한 strategy 가 B.reset 뒤에도, A.reset 이후에도 레지스트리에 남는다(훅은 B.reset 에서 이미 제거됨). 기계적으로는 맞다.
- 판단: 등록하지 않은 인스턴스에서 reset 을 부르는 오용이 필요해서 실사용 영향은 작아 보인다. 이번에는 고치지 않고 기록만(분석 참조).

## 17:14 #20643 확인 (읽기만)
- `gh pr view 20643`, `gh pr diff 20643 > logs/04-pr20643.diff`(2427줄). 열림, 작성자 copilot-swe-agent, 7커밋, 리뷰는 Copilot 코멘트 1건, mergeable `UNKNOWN`.
- 변경 파일 15개. `HooksInstrumentation.java` 없음. `registerOnEachOperator`/`resetOnEachOperator` 본문 변경 없음(테스트에서 호출만). `enabled` 는 컨텍스트 줄로만 나옴. `Sinks` 문자열 없음.
- 겹치는 파일: 같은 모듈의 `ContextPropagationOperator.java`, `TracingSubscriber.java`, 에이전트 `ContextPropagationOperatorInstrumentation.java`. 내 수정은 `HooksInstrumentation.java` 와 새 테스트 파일뿐이라 충돌 없음(git 으로 병합을 시도해 보지는 않았다 = 확인 안 함).
- 그 PR 이 H2 를 해결하는가: 아니다(위 이유). H1 을 해결하는가: 아니다(Sinks·onLastOperator 없음).

## 17:15 수정과 되돌림 검증
- 브랜치 `reactor-sinks-reset-all-hooks`(로컬).
- 테스트 `HooksResetTest`(javaagent test 소스셋): (1) reset-all 을 두 번 호출해도 컨텍스트가 계속 전파됨, (2) 무관한 키의 reset 은 영향 없음. 수정 전 로그 `logs/05-before-fail.log`, XML `logs/05-before-fail-TEST-HooksResetTest.xml`: `exit=1 elapsed=29s`, `2 tests completed, 1 failed`.
- 첫 수정: 재등록용 operator 생성 코드를 `HooksInstrumentation` 의 private static 메서드로 빼서 두 advice 가 공유. **틀렸다.** 결과 `logs/06a-after-attempt1-linkageerror.log`: `LinkageError: loader constraint violation in interface itable initialization for class ...HooksInstrumentation`, `3 Advice failures`, 3개 모두 실패. `inline = false` advice 에서 바깥 클래스를 참조하면 클래스로더가 달라 터진다. advice 는 바깥 클래스에 기대지 않고 자체 완결이어야 한다. 이 시도의 XML 은 `logs/06a-after-attempt1-TEST-HooksResetTest.xml`(`tests="3" failures="3"`, 두 번째 실행이 덮기 전 사본이 아니라 같은 실행의 결과; 3개째는 클래스 종료 시 advice 실패 집계 오류).
- 두 번째 수정(최종): 헬퍼를 없애고 각 advice 에 builder 표현식을 그대로 둠. reset-all(인자 0개)에는 새 advice 를 달고, 그 안에서 `operator.resetOnEachOperator()` 로 operator 의 `enabled` 를 내린 뒤 `registerOnEachOperator()` 로 다시 등록. 기존 advice 는 type initializer 와 키 있는 `resetOnEachOperator(String)` 에만 남김.
- 수정 후 통과: `logs/06-after-pass.log`, XML `logs/06-after-pass-TEST-HooksResetTest.xml`: `exit=0 elapsed=10s`, `tests="2" failures="0"`. `compileJava`, `test` 가 실제로 실행된 것을 로그로 확인.
- 본 코드만 되돌림(`git checkout -- HooksInstrumentation.java`, 테스트 유지): `logs/07-revert-fail.log`, XML `logs/07-revert-fail-TEST-HooksResetTest.xml`: `exit=1 elapsed=8s`, `2 tests, 1 failed`(reset-all 테스트). 복원 후 `git status` 확인.

## 17:17 모듈 테스트, 포맷
- 첫 시도 `logs/08a-module-tests-zsh-modifier-error.log`: `$R:library:test` 에서 zsh 가 `:l` 을 소문자 변환 수정자로 해석해 `reactor-3.1ibrary` 가 됨. 변수 뒤에 `:` 를 붙일 때는 `${R}:library` 로 쓴다(새 함정).
- 재실행: `spotlessApply` + `javaagent:{test,testInitialization,version34Test}` + `library:test --continue` → `exit=0 elapsed=38s`, `logs/08-module-tests.log`. XML 합계(`logs/08-junit-xml/`): javaagent test 59, testInitialization 1, version34Test 3, library test 60(skipped 1), 실패 0. 새 테스트 2개는 javaagent test 59 에 포함.
- spotlessApply 는 이 실행에 포함되어 포매팅이 적용됐다(advice 의 builder 체인 줄바꿈이 바뀐 것을 `git diff` 로 확인).
- `-PtestLatestDeps=true` 로 `HooksResetTest` + `testInitialization`: `logs/09-latestdeps.log` `exit=0 elapsed=74s`, 통과. 단 로그에서 실제로 해석된 reactor-core 버전을 확인하지 못했다(확인 안 함).
- 확인 안 함: 전체 `check`, 다른 모듈(webflux, spring-ai, lettuce, r2dbc 등)의 테스트, muzzle, 실제 에이전트를 붙인 Spring 앱에서의 동작.

## 17:20 커밋
- 브랜치 `reactor-sinks-reset-all-hooks`, 커밋 `972873c6815bff2c319f3241c6583252c474ac3a`. 작성자·커밋터 `DDINGJOO <173995233+DDINGJOO@users.noreply.github.com>`, 트레일러 `Assisted-by: Claude Opus 5.5`. Co-Authored-By 없음. 푸시·PR 없음.
- 최종 diff `patch.diff`(`git diff main`).
- 임시 탐색 테스트 3개는 클론에서 지우고 소스를 `logs/` 에 보관.

## 2026-10-22 PR 제출과 증거 이미지

- PR #20845 제출(DDINGJOO, `Assisted-by` 유지).
- `screenshots/01-before-fail.png`, `02-after-pass.png`, `03-revert-fail.png`: 실제 터미널 캡처가 아니라 `logs/` 의 Gradle 출력과 JUnit XML 에서 핵심 줄을 그대로 옮겨 렌더한 이미지다. 줄 번호와 출처 파일을 이미지 안에 적었다. 원본은 같은 폴더의 `.html`.

## 2026-10-22 17:29 Gradle 테스트 보고서 캡처

- 수정 전: `HooksInstrumentation.java` 만 origin/main 으로 되돌리고 `HooksResetTest` 실행 → BUILD FAILED, 2개 중 1개 실패. 보고서 생성 17:29:37. 보고서 원본 `reports/before/`, 로그 `reports/before.log`.
- 수정 후: 처음 실행은 입력이 같아 Gradle 이 테스트를 건너뛰고 17:15 보고서를 그대로 남겼다. `--rerun` 으로 다시 돌려 17:30:35 보고서를 얻었다. 원본 `reports/after/`, 로그 `reports/after.log`.
- 캡처: `screenshots/11-report-before-class.png`(클래스 요약, 50%), `12-report-before-failure.png`(실패 상세 `Expecting value to be true but was false`), `21-report-after-class.png`(클래스 요약, 100%). 헤드리스 Chrome 으로 보고서 HTML 을 그대로 연 화면이다.
- 교훈: 같은 코드로 다시 돌린 Gradle 테스트는 UP-TO-DATE 로 건너뛰어 예전 보고서가 남는다. 증거용으로 다시 돌릴 때는 `--rerun` 을 붙이고 보고서의 생성 시각을 확인한다.

## 2026-10-22 17:3x 리뷰 대응: Copilot 인라인 지적 (discussion_r4346161890)

- 지적: reset 마다 `ContextPropagationOperator` 를 새로 만들어 reset/register 한다. operator 마다 `ReactorAsyncOperationEndStrategy` 가 따로 있고 레지스트리는 identity 로 unregister 하므로, 새 operator 의 reset 은 아무것도 지우지 못하고 전략만 하나씩 더 쌓인다.
- 판단: 맞다. 첫 수정은 "훅이 다시 붙는다" 만 보고 레지스트리 쪽 부작용을 보지 않았다. 원래 코드(type initializer 마다 새 operator)도 같은 성질이 있었지만 그때는 `enabled` 때문에 두 번째부터 등록이 막혀 쌓이지 않았다. 내 수정이 그 막힘을 풀면서 누적을 만들었다.
- 수정: javaagent 에 `ReactorSingletons` 를 두고 operator 하나를 끝까지 재사용한다. type initializer · 키 있는 reset 은 `registerOnEachOperator()`, 인자 없는 reset 은 `reregisterOnEachOperator()`(같은 operator 로 reset → register).
- 헛짚음: 처음엔 키 있는 reset 에도 재등록을 걸었다. operator 의 `resetOnEachOperator()` 가 내부에서 `Hooks.resetOnEachOperator(key)` 를 부르므로 advice 가 다시 불려 무한 재귀 → 테스트 15분 타임아웃(`logs/10-review-fix-module-tests.log`, `ReactorSingletons.java:30` 반복 스택). 인자 없는 reset 에만 재등록을 걸도록 되돌렸다.
- CI 실패 44건: 이 PR 과 무관. main 의 `InstrumenterBuilder.java:53` 미사용 logger 가 `-Werror` 로 `:instrumentation-api:compileJava` 를 깨뜨림. 같은 시각 main 빌드(079a5af0e2, 4c54b89cba)도 실패.
- 17:5x 커밋 60be7a98c8 푸시, Copilot 스레드에 답글(discussion_r4346387255).
