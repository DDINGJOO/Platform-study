# OpenTelemetry Java Instrumentation 기여 아카이브

회고할 때 이 파일부터 연다. 작업마다 폴더 하나, 폴더 구성은 같다.

| 파일 | 내용 |
|---|---|
| `journal.md` | 시간순 작업 일지. 의심한 것, 실행한 명령, 나온 결과, 틀린 판단까지 지우지 않는다 |
| `repro.md` | 재현 명령과 결과. 수정 전 실패 · 수정 후 통과 · 본 코드만 되돌리면 실패 |
| `analysis.md` | 원인 코드 위치(파일:줄, 커밋), 라이브러리 동작 근거, 시맨틱 컨벤션 근거 |
| `pr-draft.md` | PR 제목·본문 초안. 올린 뒤에는 PR 링크를 맨 위에 적는다 |
| `patch.diff` | 최종 diff |
| `logs/` | 원본 증거. Gradle 출력, JUnit XML 보고서 |

## 작업 목록

| 작업 | 폴더 | 상태 | PR / 이슈 |
|---|---|---|---|
| Spring Kafka async acks process span 중복 | (회고 글 2편) | 머지 10-19 | #20658 |
| @WithSpan Flux 가 소스에 32개 요청 | (회고 글 2편) | 머지 10-20 | #20659 |
| MySQL/MariaDB address= URL server.address 누락 | (회고 글 1편) | 머지 10-19 | #20660 |
| Lettuce 타임아웃 error.type="BLPOP." | (회고 글 1편) | 머지 10-19 | #20661 |
| Kafka 실패 span 의 partition/offset -1 | `kafka-unknown-offset/` | 보류 (10-22). -1 은 Kafka 의 의도된 "알 수 없음" 표시라 버그로 보기 약하다 | 미제출 |
| Reactor 앱의 `Hooks.resetOnEachOperator()` 뒤 훅 재등록 실패 | `reactor-sinks/` | 리뷰 대기 (10-22 제출) | #20845 |
| Reactor Sinks 를 연산자 없이 바로 구독하면 컨텍스트 미전파 | `reactor-sinks/` | 설계 한계로 판단, 이슈 여부 미정 | — |
| Lettuce sync 타임아웃이 성공으로 기록(javaagent + 최신 Lettuce 회귀) | `lettuce-sync-timeout/` | 이슈 제출, 수정 PR 준비 중 (10-22) | 이슈 #20847 |
| WebFlux 2건(WebClient 지표 이중 기록, SSE 끊김 시 200 소실) | — | #20643 정리 대기 | — |

머지된 4건의 재현 기록은 `repro.md`(이 폴더), 회고 글은 `posts/open-source-contribute/opentelemetry/`.

## 규칙

- 근거 없는 문장을 쓰지 않는다. 확인하지 않은 것은 "확인 안 함" 으로 적는다.
- 푸시·PR·코멘트는 사람이 승인한 뒤에만 한다.
