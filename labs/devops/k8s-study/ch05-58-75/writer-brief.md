# 58~75편 공통 집필 지시

담당 편과 그 원자료만 작성한다. 공통 파일(.mask-allow, tistory-series.json, README, 다른 담당 편, 기존 글)은 수정하지 않는다. 커밋·푸시·발행은 하지 않는다. 필요한 공통 파일 변경은 보고서에 적는다.

저장소 두 개를 혼동하지 않는다. 파일을 쓸 때는 절대 경로를 쓴다.
- 블로그 저장소(쓰기): `/Users/dding/orca/workspaces/Platform-study/k8s-study` (이하 BLOG)
- 실습 저장소(읽기, 실험 실행): `/Users/dding/orca/workspaces/k8s/tang` (이하 LAB)

## 필수 읽기
- BLOG/.claude/skills/blog-post-pipeline/SKILL.md ("글감은 독자가 검색할 문제에서 출발한다", "📸 실행 화면 캡처")
- BLOG/.claude/skills/tistory-sketch-post/SKILL.md 와 references/svg-sketch-guide.md, references/easy-read-guide.md, assets/template.html
- BLOG/labs/devops/k8s-study/ch05-58-75/plan.md (전체 계획), manifest.json (번호·제목·파일명 고정), series-boxes.html (편마다 시리즈 박스, 그대로 복사)
- 스타일 앵커: BLOG/posts/CS/DevOps/k8s-study/50_50편 - 노드 장애 판단의 50초와 300초는 왜 그 값일까.html
- 담당 묶음 브리프에 적힌 원자료와 관련 기존 글

## 형식
- 템플릿 `<style>` 블록을 수정 없이 그대로 쓴다. 파일 첫머리 주석 블록, `<!-- lead: ... -->`, `<!-- tags: ... -->` 필수(50편과 같은 모양).
- 시리즈 박스는 series-boxes.html 의 해당 편 블록을 그대로 쓴다.
- 도입은 구체적인 장면(실제로 본 출력, 겪은 상황)으로 연다. 개념 정의로 시작하지 않는다.
- h2 4~6개("1. 제목" 번호), 손그림 곡선 SVG 2~4개(svg-sketch-guide 를 따른다, rect·직선 금지), 처음 나오는 자리에 📖 용어 박스 4~8개, 콜아웃 2~5개, 요약 박스로 끝. 다음 편 예고 금지.
- 해요체. 엠대시(— 와 &mdash;) 금지, 비유 금지(fluent-korean). 영어·숫자 뒤 조사는 붙여 쓴다("Pod를", "1.37에서", "SIGTERM을"). 연결어미 뒤 쉼표("~했고,")를 줄인다.
- 분량 제한은 없다. 깊이를 위해 필요한 만큼 쓴다.
- 1차 출처(KEP, 이슈·PR 원문, 커널·kubelet 소스 태그, 공식 문서)는 본문 또는 요약 박스 앞 "출처" 단락에 링크로 넣는다. 원문 URL 은 LAB/shared/why/*/sources/_index.txt 에 있다.
- 다른 편은 본문에서 "43편"처럼 번호로 가리킨다.
- 강의·슬라이드·수업·강사 같은 말을 쓰지 않는다. 옛 버전 설명과 다르면 "예전 버전에는 ~였고 1.NN에서 바뀌었다"처럼 버전 변화로만 쓴다.
- 독자가 물을 질문(각 브리프의 "넣을 질문")을 본문에서 질문으로 세우고 답한다. "강의 중 질문" 같은 표현은 쓰지 않는다.

## 사실과 증거
- 수치·출력은 원자료에서만 가져온다. 기억으로 최신 동작을 단정하지 않는다. 확인 못 한 것은 쓰지 않거나 범위를 한정한다(각 notes.md 의 "9. 확인 못 한 것"을 단정하지 않는다).
- 원자료 `.sh`/`.txt` 중 본문이 인용하는 것을 BLOG/labs/devops/k8s-study/out/ 에 `NN-이름.sh`/`NN-이름.txt` 로 복사한다(NN = 그 내용을 처음 인용하는 편 번호). 내용은 바꾸지 않는다. 본문에는 `labs/devops/k8s-study/out/NN-이름.txt` 처럼 경로를 적는다(50편의 `<code style=...>` 모양).
- 근거가 부족하면 LAB 클러스터에서 더 실험해도 된다: `cd LAB && ./lab kubectl ...`, 노드는 `limactl shell k8s-worker1 -- ...`. 담당 네임스페이스(`blog-NN`)만 쓰고 끝나면 지운다. 클러스터 설정 변경, 구성 요소 정지·재시작, feature gate 변경, VM 재시작 금지. 다른 네임스페이스를 건드리지 않는다. 이미지는 busybox:1.37, nginx:1.27-alpine, nginx:1.28-alpine, curlimages/curl:8.11.1. 새 실험도 `.sh`(첫 주석 줄: 무엇을 확인하나 + "(Mac 에서 실행)") + `.txt` 로 out/ 에 남긴다. 증거 파일 안에 "강의·슬라이드"를 쓰지 않는다.
- 내 스크립트 실수로 다시 돌린 일은 글감으로 쓰지 않는다.

## 캡처
- 편마다 핵심 출력 1~2개를 term-shot 으로 찍는다:
  `/Users/dding/.local/share/tistory-uploader/venv/bin/python3 BLOG/.claude/skills/blog-post-pipeline/assets/term-shot.py --from BLOG/labs/devops/k8s-study/out/NN-x.txt --cmd "<실제 명령>" --source labs/devops/k8s-study/out/NN-x.txt --lines A-B -o BLOG/posts/CS/DevOps/k8s-study/images/NN/01-이름.png`
  (cwd 는 BLOG). 마스킹에 걸리면 찍지 않고 보고한다.
- 이미지는 `https://raw.githubusercontent.com/DDINGJOO/Platform-study/main/posts/CS/DevOps/k8s-study/images/NN/파일.png` 로 건다(50편 `<img>` 모양, alt 에 무엇을 실행한 화면인지와 핵심 숫자).

## 검증 (각 편)
- `python3 BLOG/.claude/skills/blog-post-pipeline/assets/mask-check.py <글.html>` 와 복사한 out/ 파일들. 실습 VM·파드 IP(192.168.104.x, 192.168.64.x, 10.244.x, 10.96~10.111.x), resourceVersion, uid 조각 같은 오탐은 `.mask-allow` 에 넣을 줄(값 + "# 사유")을 보고서에 적는다.
- 태그 짝(svg, div, path), 중복 id, 엠대시 0, 요약 박스가 마지막, 이미지 파일 존재, lead 80~150자.
- 영어·숫자 뒤 띄운 조사 점검: `grep -nE '[A-Za-z0-9)] (은|는|이|가|을|를|에|의|로|으로|와|과|도|만|에서|까지|부터) ' 글.html` 로 찾아 본문 산문은 붙인다(코드 블록·SVG 안은 제외).

## 보고 (짧게)
편마다: 파일 경로, h2·그림·용어 박스·콜아웃 수, 캡처 파일, 새로 돌린 실험, out/ 에 복사한 파일, .mask-allow 에 넣을 줄, 남은 한계. 청소(네임스페이스 삭제) 확인.
