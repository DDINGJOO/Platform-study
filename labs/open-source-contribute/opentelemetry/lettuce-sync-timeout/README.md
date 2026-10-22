# lettuce-sync-timeout

Lettuce sync API 타임아웃이 성공 span 으로 기록되는지 조사한 기록. 결론은 analysis.md, 결과 표는 repro.md, 초안은 issue-draft.md(미제출). `logs/` 는 로컬 경로가 찍힌 빌드 로그를 포함하므로 공개 저장소에 커밋하지 않는다(JUnit XML 은 `SPANDUMP` 줄만 근거로 쓴다). `run.sh` 는 환경변수 `OTEL_CLONE`, `LOGDIR` 필요.
