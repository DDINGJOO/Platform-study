# 58~75편 감사 지시

담당 편을 원자료와 대조해 사실·논리·형식을 감사하고, 확실한 문제는 그 글에서 직접 고친다. 다른 편·공통 파일(.mask-allow, README, tistory-series.json)·out/ 원자료 내용은 고치지 않는다(필요하면 보고). 커밋·푸시 금지.

- 블로그 저장소: `/Users/dding/orca/workspaces/Platform-study/k8s-study` (BLOG)
- 실습 저장소: `/Users/dding/orca/workspaces/k8s/tang` (LAB, 원자료 shared/ch05-pod, shared/why/0N-*)
- 규칙 원본: BLOG/labs/devops/k8s-study/ch05-58-75/writer-brief.md, plan.md, BLOG/.claude/skills/tistory-sketch-post/SKILL.md, references/easy-read-guide.md

## 1. 사실 (가장 중요)
- 본문의 모든 숫자·시각·버전·출력 인용·인용문을 out/ 파일(본문이 가리키는 경로)이나 LAB 원자료, sources 발췌와 한 줄씩 대조한다. 원자료에 없는 수치는 고치거나 지운다.
- 버전 이력(알파·베타·GA 릴리스, PR·이슈 번호, 날짜)은 LAB/shared/why/*/sources 원문이나 notes.md 연대표와 맞는지 본다. notes.md "9. 확인 못 한 것"에 있는 내용을 단정하면 범위를 한정하거나 지운다.
- 인과 주장("~때문에")이 실험·소스로 받쳐지는지 본다. 추론이면 추론이라고 쓰게 고친다.
- 링크한 URL 이 sources/_index.txt 의 원문 URL 과 맞는지(오타·다른 PR 번호) 본다.
- 이미지 파일이 실제로 있고 alt 의 숫자가 이미지 원자료와 맞는지 본다.

## 2. 논리와 독자
- 1~2년차 개발자가 읽고 따라갈 수 있는가. 용어 박스가 처음 나오는 자리에 있는가. 질문형 제목에 본문이 실제로 답하는가.
- 같은 묶음의 앞뒤 편과 모순이 없는가(번호로 가리키는 편의 내용과 맞는가).

## 3. 형식
- 템플릿 style 블록 변경 없음, lead(80~150자)·tags 주석, 시리즈 박스가 series-boxes.html 과 같음, h2 4~6, SVG 2~4, 용어 박스 4~8, 콜아웃 2~5, 요약 박스로 끝, 예고 없음.
- 엠대시(—, &mdash;) 0, 비유 없음, "강의·슬라이드·수업" 0.
- 영어·숫자 뒤 띄운 조사(산문만): `grep -nE '[A-Za-z0-9)] (은|는|이|가|을|를|에|의|로|으로|와|과|도|만|에서|까지|부터) '`.
- 태그 짝(svg·div·path·text·p), 중복 id, mask-check: `python3 BLOG/.claude/skills/blog-post-pipeline/assets/mask-check.py <글.html>`.

## 기록
- `BLOG/labs/devops/k8s-study/ch05-58-75/review-NN-MM.md` 에 지적 목록(편, 위치, 문제, 근거, 조치: 반영/반박)을 남긴다. 지적이 틀렸다고 판단하면 고치지 말고 근거를 적는다.
- 마지막 줄: "지적 M건 → 반영 K건".

## 보고 (짧게)
편별 지적 수·반영 수, 중요한 사실 오류 목록(무엇이 틀렸고 원자료는 무엇이었나), 남은 위험.
