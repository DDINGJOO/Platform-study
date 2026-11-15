# 공통 집필 지시
역할은 설치된 executor이다. ~/.codex/agents/executor.toml의 developer_instructions를 읽어 그 역할로 수행한다. 자식 에이전트를 추가 생성하지 않는다.

사용자 요청: 플랫폼 스터디 기존 수준을 유지해 Calico를 실측으로 해부하는 51~56편을 완성한다. 담당 한 편과 그 실험 자료만 작성한다. 공통 파일·기존 글·다른 담당 파일은 수정하지 않는다. 커밋·푸시·발행·Notion 쓰기는 하지 않는다.

## 필수 읽기
- /Users/dding/orca/Platform-study/.claude/skills/blog-post-pipeline/SKILL.md
- /Users/dding/orca/Platform-study/.claude/skills/tistory-sketch-post/SKILL.md
- 같은 tistory 스킬의 references/svg-sketch-guide.md, references/easy-read-guide.md, assets/template.html
- 이 작업 트리 labs/devops/k8s-study/calico-follow-up-outline.md
- 이 디렉터리 manifest.json과 series.html (6편의 제목·파일명 고정)
- 스타일 앵커 posts/CS/DevOps/k8s-study/50_50편 - 노드 장애 판단의 50초와 300초는 왜 그 값일까.html
- 관련 기존 글 6/28/29/30/31/34/43/47 중 필요한 것

## 내용·형식
실제로 먼저 실험한다. 예정·문서·예상과 관측을 구분한다. 무리한 실험 대신 가능한 격리 실험으로 범위를 조정하고 근거 없는 과거형은 쓰지 않는다. 재현 명령·시각·종료 코드·stdout/stderr·매니페스트·pcap을 보관한다. 공식 문서와 필요한 설치 버전 소스를 웹으로 확인하고 HTML 본문에 직접 출처 링크를 넣는다. 기억만으로 최신 동작을 단정하지 않는다.

템플릿 style 블록은 그대로 사용. 4~6 h2, 2~4개 손그림 곡선 SVG, 처음 나오는 위치에 용어 박스 4~8개, 실제 문제로 시작, 해요체, 엠대시·비유 금지. 본문 깊이를 위해 필요한 길이는 허용한다. series.html을 복사해 {number}를 자기 번호로 바꾸고 해당 줄만 b+지금 이 글로 표시한다. 요약 박스로 끝낸다. 관련 출처는 끝 요약 이전에 넣는다. tags/lead 주석 필수.

## 실험 격리
클러스터 도구 /Users/dding/orca/workspaces/k8s/tang/lab. 명령 예: ./lab kubectl ..., ./lab ssh worker1 -- sudo ... . mac host kubectl보다 이 래퍼를 사용한다. 현재 4노드 Ready, Calico3.33 IPIP Always. 일반 클러스터 변경·BIRD 정지·기존 경로 삭제·전역 정책·노드 iptables 변경·VM 재시작은 금지. 담당 namespace calico-blog-NN, 호스트 netns cbNN-* 등 고유 이름만 쓴다. 공유 노드에서 read-only 캡처는 고유 포트·시간·Pod IP 필터와 timeout을 쓴다. 설치된 VM 캐시 이미지 pause3.10.2, nginx1.25.1-alpine, busybox1.36.1/1.37, curlimages/curl8.11.1을 우선 확인하고 사용한다. 자원 제한을 작게 하고 3~4Pod 이하, 테스트 후 자신이 생성한 자원만 제거하며 finally로 복구한다. 다른 실험 namespace를 지우지 않는다.

각자 자료는 labs/devops/k8s-study/calico-51-56/NN/ 아래 스크립트·원문·검증 README로 보관한다. 파일 쓸 때 절대 경로를 사용해 두 저장소를 혼동하지 않는다. 환경 파일·토큰·Secret·kubeconfig는 원문에 남기지 않는다. 개인 Lima 실습 노드/Pod IP는 기술 설명에 사용해도 되지만 회사 값과 구분하고 마스킹 검사 결과를 보고한다.

## 캡처·검증
핵심 출력 1~2개를 term-shot.py로 이미지화한다. /Users/dding/orca/Platform-study/.claude/skills/blog-post-pipeline/assets/term-shot.py 도움말 확인 후 --from을 쓰고 원문 경로를 표시한다. 이미지 파일은 posts/CS/DevOps/k8s-study/images/calico-NN/ 안에 보관하고 raw.githubusercontent.com/DDINGJOO/Platform-study/main/ 경로로 링크한다. 캡처는 저장된 원문을 렌더링한 것으로 표현한다. 텍스트 마스킹 검사를 먼저 수행하고 사설IP가 개인 실습 값인 경우 그 판단을 README에 기록한다. .mask-allow 등 공통 파일은 수정하지 않는다. 도구가 없거나 실패하면 정확히 보고한다.
HTML 태그·SVG XML·중복 id·엠대시·요약 위치·이미지 파일 존재 등을 실제 검사한다. 확인 불가한 주장은 삭제하거나 범위를 한정한다. 마지막에 실험 성공·실패와 청소 확인, 작성 파일, 검증 결과, 남은 한계를 보고한다. 지적이 틀리면 무조건 고치지 말고 근거로 반박한다.
