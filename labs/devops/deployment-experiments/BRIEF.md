# 배포 관측과 A/B 실험 공통 브리핑

사용자 요청으로 실제 실습과 글 3편을 작성·독립 검수하고 GitHub commit/push, 티스토리 업로드까지 진행한다. Git과 업로드는 리더만 담당한다. Notion은 나중에 하기로 했으므로 읽거나 쓰지 않는다. 회사 자료·실제 개인정보·회사 보안 상태를 사용하지 않는다. 소스는 이 신규 실습만 수정하며 기존 자료 저장소는 읽기 전용이다.

| 번호 | 실습 | HTML 파일 |
|---|---|---|
| 1 | canary | 01_1편 - 오래된 A 대신 새 베이스라인 A′와 B를 비교한다.html |
| 2 | sticky-ab | 02_2편 - A·B 테스트 사용자는 새로고침해도 같은 그룹이어야 한다.html |
| 3 | decision | 03_3편 - 전환율이 높아도 표본과 가드레일부터 확인한다.html |

repo root: /Users/dding/orca/Platform-study
lab root: /Users/dding/orca/Platform-study/labs/devops/deployment-experiments
post root: /Users/dding/orca/Platform-study/posts/CS/DevOps/deployment-experiments
image dirs: post root/images/lab-01, lab-02, lab-03

읽을 스킬·가이드 (모두 절대 경로):
- /Users/dding/orca/Platform-study/.codex/skills/blog-post-pipeline/SKILL.md 및 source-skill.md
- /Users/dding/orca/Platform-study/.codex/skills/tistory-sketch-post/SKILL.md 및 source-skill.md
- /Users/dding/orca/Platform-study/.codex/skills/tistory-sketch-post/references/easy-read-guide.md
- /Users/dding/orca/Platform-study/.codex/skills/tistory-sketch-post/references/svg-sketch-guide.md
- /Users/dding/orca/Platform-study/.codex/skills/tistory-sketch-post/assets/template.html
톤 기준: /Users/dding/orca/Platform-study/posts/CS/Observability/tracing-debugging/10_실습-4 - 지연을 주입하고 트레이스로 원인을 찾는다.html

템플릿 style 원문 유지, 해요체, 비유·엠대시 금지, 용어 4~8개, SVG 2개 이상(path 기반, rect/line/circle 없음), 충분한 재현 명령과 오류 풀이. 본문 분량은 내용을 따라가되 4~6개 절을 기본으로 한다. lead 80~150자와 tags 주석 포함.


시리즈 박스 정본. 현재 편 포함 최근 최대 3개 줄만 남기고 자기 편만 b 및 현재 표시를 붙인다. 링크는 붙이지 않는다.
<div class="obsv-series">
  <div class="obsv-st">📚 배포 관측과 A/B 실험 · N편</div>
  1편. 오래된 A 대신 새 베이스라인 A′와 B를 비교한다<br>
  2편. A/B 테스트 사용자는 새로고침해도 같은 그룹이어야 한다<br>
  3편. 전환율이 높아도 표본과 가드레일부터 확인한다<br>
</div>

필수:
- 1편 실제 Netflix Kayenta judge, 실제 Spinnaker Deck report UI, 가능하면 실제 Orca 파이프라인. mock UI·Python Kayenta 포트 대체 금지. 기존 delivery-safety와 차이는 실제 도구와 데이터 연결이다. A=먼저 기동한 기존 v1, A′=새 v1 baseline, B=동시에 뜬 변경본. A′와 B의 이미지·설정 중 변경 변수, 생성 시점, 자원, 워밍업, 부하, 관측 구간을 기록한다. A vs A′로 재배포 영향을 확인하고 주 판정은 A′ vs B로 한다. 도구 실행 범위를 정확히 쓰고 전체 Netflix 운영 재현이라고 쓰지 않는다.
- 2편 가상 사용자 식별자를 해시한 고정 할당, 진입/노출/전환 이벤트와 사용자 단위 dedup/분모를 실제 HTTP 서비스로 검증. 재기동/재시도/반복 요청에 할당 유지. 시드·salt 변경 위험도 명시. 도구와 지표를 정확히 분리. Grafana 실제 수집 값 캡처. synthetic 전환율은 제품 개선 근거 아님.
- 3편 합성 이벤트 세트에 sample 부족, SRM(할당 비율 이상), 오류·지연 가드레일, 정상·효과 있음 사례를 포함. 독립 분석 코드로 observed/expected표본과 고정된 판정 규칙 확인. p값만으로 승자 주장 금지, 효과 크기/구간, 사전 표본 계획·고정 관측 구간 및 반복 들여다보기 문제를 설명. 과소표본에서도 확정 승리 금지. 통계 공식은 공식/원논문 근거 확인 후 구현. 샘플링 trace 수를 사용자 분모로 쓰지 않는다. 실제 화면/출력 캡처.

각 lab 독립 compose 프로젝트 deployment-experiments-01~03, 포트 281xx/282xx/283xx. 기존 week07-control-plane 등은 건드리지 않는다. 공유 Docker8GB, 현재 기존 kind 약2GB. 연구자가 /tmp/deployment-docs.md 에 실제 Spinnaker 버전/설정 근거 준비 중. 필요한 JVM Xmx256~512m·서비스 최소화. 글로벌 prune/down 금지, 자기 stack만 관리. 새 구성 요소는 사용자가 요청한 Netflix도구/실습을 위한 범위로 명시해 고정 버전 사용. 다른 불필요한 패키지 추가 금지.

실제 Docker 실행→assert 포함 run.py/verify.py→out/summary.json+results.txt→README/버전/참고링크→글. 실제 캡처 PNG 2개 이상, 도구 UI+출력 권장. 수치 미리 작성/가짜 그래프 금지. 로그에 원시 계정·토큰 금지. 긴 시각/랜덤 식별자는 원자료로 필요할 때만 남겨 마스킹 오탐을 줄인다. 재실행으로 기존 증거를 조용히 덮지 않도록 자기 lab 안 history 보관 및 gitignore.

Playwright: /Users/dding/.local/share/tistory-uploader/venv/bin/python (설치됨), Chrome설치됨. terminal캡처는 추적된 /Users/dding/orca/Platform-study/.claude/skills/blog-post-pipeline/assets/term-shot.py 사용(신규 checkout에서 untracked 스킬링크 의존 금지). 실제 UI 읽기 준비/데이터 확인 후 capture. img src=images/lab-NN/file.png 로 시작, CDN변환은 리더만. 공통파일(BRIEF/루트README/ROADMAP/tistory-series/.mask-allow)은 리더소유 수정금지.

글 직접 validate_html.py 및 mask-check.py 실행. 독립 퇴고·감사는 별도 에이전트 담당. 각 글 다른 작성자, 한 파일 한 명 편집. leaf agent는 추가 위임 금지. agent_type=executor, ~/.codex/agents/executor.toml 지침. 완료 주장에는 실제 command와 결과를 보고하고 stack URL과 재검 경로를 알려준다. 막히면 대체안을 근거와 함께 리더에게 알리고 다른 에이전트 영역에 침범하지 않는다.

파일명에는 경로 구분자 /를 쓸 수 없어서 2편은 A·B로 저장한다. 본문과 발행 제목은 A/B를 유지하며 리더가 tistory-series titles override로 매핑한다.
