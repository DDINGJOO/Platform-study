# OTel 운영 실습 4편 공통 브리핑

목표: 간단한 실제 서비스 + OTel Collector + Grafana/Tempo (필요하면 Loki/Prometheus), 실행한 실험 수치·로그·브라우저 스크린샷이 포함된 한국어 실습 글 네 편. 초기 범위는 작성·검수였고 이후 사용자가 commit/push/블로그 업로드를 명시적으로 추가 요청했다. 실제 발행 작업은 리더가 담당한다. Notion write는 하지 않는다.

| 번호 | lab 디렉터리 | HTML 파일 |
|---|---|---|
| 1 | collector-loss | 01_1편 - Collector가 받았다고 한 스팬은 정말 저장됐을까.html |
| 2 | tail-sampling | 02_2편 - 에러 트레이스만 남기면 장애를 놓치지 않을까.html |
| 3 | dual-instrumentation | 03_3편 - Java agent와 Micrometer Tracing을 같이 켜면 어떻게 될까.html |
| 4 | sensitive-data | 04_4편 - Collector에서 지운 개인정보는 어디까지 사라졌을까.html |

lab root: /Users/dding/orca/Platform-study/labs/observability/otel-practice
post root: /Users/dding/orca/Platform-study/posts/CS/Observability/otel-practice
image dirs: post root/images/lab-01, lab-02, lab-03, lab-04

읽을 스킬·가이드 (모두 절대 경로):
- /Users/dding/orca/Platform-study/.codex/skills/blog-post-pipeline/SKILL.md 및 source-skill.md
- /Users/dding/orca/Platform-study/.codex/skills/tistory-sketch-post/SKILL.md 및 source-skill.md
- /Users/dding/orca/Platform-study/.codex/skills/tistory-sketch-post/references/easy-read-guide.md
- /Users/dding/orca/Platform-study/.codex/skills/tistory-sketch-post/references/svg-sketch-guide.md
- /Users/dding/orca/Platform-study/.codex/skills/tistory-sketch-post/assets/template.html
톤 기준: /Users/dding/orca/Platform-study/posts/CS/Observability/tracing-debugging/10_실습-4 - 지연을 주입하고 트레이스로 원인을 찾는다.html

템플릿 style 원문 유지, 해요체, 비유·엠대시 금지, 용어 4~8개, SVG 2개 이상(path 기반, rect/line/circle 없음), 충분한 재현 명령과 오류 풀이. 본문 분량은 내용을 따라가되 4~6개 절을 기본으로 한다. lead 80~150자와 tags 주석 포함.

시리즈 박스 정본은 아래를 복사. 전체 목차 대신 현재 편 포함 최근 최대 3개 줄만 남기고 자기 편만 b 및 현재 표시를 붙인다. 링크는 붙이지 않는다.
<div class="obsv-series">
  <div class="obsv-st">📚 OpenTelemetry 운영 실습 · N편</div>
  1편. Collector가 받았다고 한 스팬은 정말 저장됐을까<br>
  2편. 에러 트레이스만 남기면 장애를 놓치지 않을까<br>
  3편. Java agent와 Micrometer Tracing을 같이 켜면 어떻게 될까<br>
  4편. Collector에서 지운 개인정보는 어디까지 사라졌을까<br>
</div>

각 lab는 독립 compose 프로젝트명 otel-practice-01~04 및 호스트 포트 271xx/272xx/273xx/274xx를 쓴다. 기존 실행 중인 week07-control-plane 등 다른 프로젝트는 건드리지 않는다. Docker Desktop 자원은 공유하므로 JVM Xmx 256m, 서비스 최소화. 가능하면 캐시된 이미지 버전(Collector contrib 0.162.0, Tempo 2.10.8, Grafana 13.2.3, Prometheus v3.15.0, Loki 3.7.8, Java21, Spring Boot4.1.1, agent2.32.0)을 재사용. 기존 관측 stack은 읽고 재사용 가능하나 기존 파일 수정 금지. 글로벌 docker prune/down 금지. 자기 compose만 실행/정리한다.

Docker 실제 실행 → 결과 검증 자동화(run.py 또는 verify.py) → out/summary.json 및 사람이 읽는 out/results.txt → README(버전, 명령, 관찰 범위) → 글 작성. 출력에는 실행 시각·버전·실제 측정 수치·한계를 남긴다. 불안정한 sleep만으로 판정하지 말고 readiness/polling과 trace/span ID 집합으로 확인한다. 핵심 기대값을 assert한다. 실험 결과를 미리 쓰거나 성능 배수·완전 보장 추측 금지. 재실행 시 이전 증거를 조용히 섞지 않는다.

도구: /Users/dding/.local/share/tistory-uploader/venv/bin/python 에 Playwright 있음. 시스템 Chrome 있음. /Users/dding/orca/Platform-study/labs/observability/scripts/capture.py 를 참고해 실제 Grafana 페이지를 찍는다. screenshot과 실제 출력 각각 한 장 이상 권장. 공통 term-shot.py는 기존 스킬 assets에 있다. 출력은 이미지 전에 mask-check. 실제 로컬 Grafana에 연결한 스크린샷으로, 가짜 대시보드 데이터나 수치 이미지 생성 금지. 캡처할 때 Grafana 콘텐츠가 보이도록 기다리고 no data/errors가 없는지 확인한다. 캡처한 stack은 리더가 재검할 수 있도록 실행 상태와 URL을 보고한다. 부담 크면 종료 전에 리더에게 연락.

새 글의 img src는 images/lab-NN/name.png 로 상대경로 사용해서 로컬에서 바로 열린다. 미공개 CDN URL 생성 금지. 발행 경로 치환·이미지 푸시는 후속 별도 권한 범위다.

공식 문서/고정 소스만 기술 근거로 사용하고 references.md 또는 README에 링크·확인 범위를 남긴다.회사 저장소·실제 개인정보·운영 보안 이슈 사용 금지. 전부 가상의 로컬 테스트 데이터다. 자료 저장소는 읽기 전용이다. 이 신규 실습과 자기 글만 수정한다. 공통 BRIEF/README/ROADMAP/tistory-series는 리더 소유라 편집 금지.

자기 글 validate_html.py 와 mask-check.py 실제 실행하고 결과 보고. 독립 검수는 리더가 별도 수행. 작성자는 자기 글 독립 승인 금지. 네이티브 leaf agent는 추가 subagent 생성 금지. agent_type=executor, installed role prompt ~/.codex/agents/executor.toml 의 실행 지침을 따른다.
