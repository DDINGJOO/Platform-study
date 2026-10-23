# 최종 검증 결과

2026-10-23, 네 편의 검수 완료 및 티스토리 비공개 업로드 기록이다. 아래 표는 초안 검수 때의 결과이며 이어지는 업로드 검증에 후속 상태를 기록했다.

| 검증 | 결과 | 근거 |
|---|---|---|
| 독립 네 관점 퇴고 | 2건 수정, 재검 잔여 0 | [review.md](review.md) |
| 별도 원자료 감사 | 32건 확인, 불일치·확인 불가·과장 0 | [audit.md](audit.md) |
| HTML/SVG·CSS·이미지 | 4편·PNG 9개 통과 | [checks.json](checks.json) |
| Chrome 레이아웃 | 1100px/390px, 총 8개 viewport 통과 | [checks.json](checks.json) |
| 새 checkout의 도구 경로 | untracked skill 링크 없이 정적 검사 통과 | [checkout-paths.json](checkout-paths.json) |
| Python·Compose | 실습 Python 13개 AST, Compose 4개 config 통과 | [code-checks.json](code-checks.json) |
| 일반 마스킹 | 글·README·캡처 원문 등 19개 통과 | [masking.json](masking.json), [실행 출력](masking.txt) |
| 기존 발행 메타데이터 | 기존 251편 변화 0, manifest 원본 유지 | [metadata.json](metadata.json) |
| 실행 자원 정리 | 신규 4개 프로젝트 종료, 기존 week07 유지 | [cleanup.json](cleanup.json) |

일반 마스킹 검사는 공개 글·문서·화면 캡처의 원문 범위다. 회사 자료는 사용하지 않았고 조직 목록 추가 검사는 하지 않았다. 원시 OTLP의 긴 나노초 시각과 합성 ID를 일반 조직 ID 검사로 모두 통과시켰다는 뜻은 아니다. 비밀값·실제 개인정보·회사 인프라 자료가 없는 가상 로컬 실험이다.

실제 요청·저장소 검증은 각 `run.py`의 단언 및 감사자의 새 읽기 전용 조회로 확인했다. Java 서비스는 Docker 빌드로 생성했고 실행된 이미지에서 검증했다. LSP 도구는 제공되지 않았다. 이미지의 시간은 실제 예시 요청 결과이며 성능 비교를 뜻하지 않는다.

감사 후 신규 실습 스택은 `docker compose down`으로 종료했다. `--volumes`는 사용하지 않았으며 파일로 저장한 원자료와 이미지도 유지했다. 다시 실행하려면 [실습 안내](../README.md)를 따른다. 현재 실행 중인 URL이라고 해석하지 않는다.

## 업로드 검증

이후 사용자가 commit/push와 블로그 업로드를 명시적으로 요청했다. 이미지 9개를 먼저 push하고 고정 이미지 커밋의 jsDelivr 주소에서 원본 바이트와 일치함을 확인했다. 글의 이미지 주소만 바꿨으며 그 주소를 원래대로 돌린 HTML 해시는 독립 감사 때와 일치한다. 공개 주소를 적용한 Chrome 8개 viewport에서도 이미지·레이아웃 검사를 통과했다.

새 글은 기존 업로더 규칙에 따라 비공개다. 1~4편은 `/700`~`/703`이며 실제 제목·공개 범위·SVG·태그·본문 길이를 확인했다. 2편은 저장 후 검색 목록에서 번호를 찾지 못해 업로더가 중단됐고, 전체 관리 목록에서 동일 제목 `/701`을 찾고 본문을 검증한 뒤 그 번호를 기록해 중복 생성을 피했다. 최종 업로더 변경 계획은 해당 시리즈 0건이다.

원시 결과를 포함한 공개 전 검사는 조직 외부 목록도 사용했다. 일반 패턴 후보 966개를 별도 감사자가 문맥과 대조했고, 로컬 시각·메트릭 소수부·합성 ID·Go 모듈·Docker 주소 등 정확한 값만 `.mask-allow`에 등록했다. 이후 기존 검사기의 스테이징 검사도 통과했다. [추가 감사](publication-mask-audit.md), [업로드·이미지 증거](publication.json).

Notion 변경은 하지 않았다. 후속 Netflix 도구 및 A/A′/B 배포 시각화는 사용자의 추가 진행 요청에 따라 [후속 로드맵](../../../../posts/CS/DevOps/deployment-experiments/ROADMAP.md)으로 진행한다.
