PR: https://github.com/open-telemetry/opentelemetry-java-instrumentation/pull/20845 (2026-10-22 제출)

# PR 초안 (푸시·PR 생성 안 함, 승인 대기)

기록 상태: 로컬 브랜치 `reactor-sinks-reset-all-hooks`, 커밋 `972873c6815bff2c319f3241c6583252c474ac3a`. 이슈 없이 PR 만 올리는 구성(이 저장소는 이전 4건 모두 그렇게 머지됨).

## 제목
Re-register Reactor hook after Hooks.resetOnEachOperator()

## 본문 (영문)
After an application calls `Hooks.resetOnEachOperator()`, the agent no longer propagates the context through Reactor operators: a subscriber of an externally driven `Flux.create` publisher no longer sees the context that was current when it subscribed, and nothing brings it back.

`HooksInstrumentation` is meant to prevent that: it re-registers the hook at the end of `Hooks.resetOnEachOperator`. But `ContextPropagationOperator.registerOnEachOperator()` returns early when its static `enabled` flag is set, and the application's own reset doesn't go through the operator, so the flag stays set and the registration is ignored.

This adds a second advice for the no-argument `resetOnEachOperator()` that resets the operator state and registers again. The keyed `resetOnEachOperator(String)` and the type initializers keep the existing advice. There is no API change.

`HooksResetTest` calls `Hooks.resetOnEachOperator()` twice and checks the context after each; it fails without the change (the second assertion, after the first reset), and also checks that resetting an unrelated hook key changes nothing.

## 한국어 번역
앱이 `Hooks.resetOnEachOperator()` 를 부르면 에이전트가 더 이상 Reactor 연산자 사이로 컨텍스트를 전파하지 않습니다. 외부에서 구동하는 `Flux.create` publisher 의 구독자는 subscribe 시점에 있던 컨텍스트를 못 보고, 복구되지도 않습니다.

`HooksInstrumentation` 은 `Hooks.resetOnEachOperator` 끝에서 훅을 다시 등록해 이것을 막으려는 코드입니다. 그런데 `ContextPropagationOperator.registerOnEachOperator()` 는 static `enabled` 가 true 면 바로 반환합니다. 앱이 직접 부른 reset 은 operator 를 거치지 않으므로 `enabled` 가 true 로 남아 재등록이 무시됩니다.

인자 없는 `resetOnEachOperator()` 에 advice 를 하나 더 달아 operator 상태를 초기화한 뒤 다시 등록하게 했습니다. 키 있는 `resetOnEachOperator(String)` 과 type initializer 는 기존 advice 를 그대로 씁니다. API 변경은 없습니다.

`HooksResetTest` 는 `Hooks.resetOnEachOperator()` 를 두 번 부르며 매번 컨텍스트를 확인하고, 변경 전에는 실패합니다. 무관한 키의 reset 이 영향을 주지 않는 것도 확인합니다.

## 사람이 확인할 것
- AGENTS.md 와 repos.md 기준으로 PR 본문은 제목·체크리스트 없이 바로 쓰고 하드랩을 하지 않았다. 위 영문 본문의 줄바꿈은 문단 단위뿐이다.
- 본문의 "second assertion" 은 확인함: 수정 전·되돌림 로그 모두 `HooksResetTest.java:36`(첫 reset 직후 assertion)에서 실패(`logs/05-before-fail.log:671`, `logs/07-revert-fail.log:628`).
- `Assisted-by: Claude Opus 5.5` 트레일러 유지 여부(repos.md: PR 전에 확인).
- H1(Sinks 직접 subscribe)·H3 는 이 PR 범위 밖. 이슈로 올릴지는 별도 결정.
