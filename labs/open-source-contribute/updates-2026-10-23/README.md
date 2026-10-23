# 오픈소스 기여 글 최신화 검증

2026-10-23 공개 PR·리뷰·체크를 기존 글 11편과 대조해 네 편을 수정했다. 새로 머지된 PR은 없으며 나머지 일곱 편은 기준 커밋 `4719a09`와 바이트 단위로 동일하다.

- [전체 수정 범위](BRIEF.md), [공식 출처](sources.md), [상태 스냅샷](status.json)
- 독립 퇴고: [사실관계](review-facts.md), [논리](review-logic.md), [독자](review-reader.md), [문장](review-style.md)
- [독립 원자료 감사](audit.md), [마스킹 후보 감사](publication-mask-audit.md)
- [HTML·브라우저 검증](checks.json), [기존 글 업로드 검증](publication.json)

라운드 1의 고유 지적 세 건은 Spinnaker 파일 수를 두 PR 합계로 명시하기, SCC 1편 lead의 기록·정정 구분, SCC 2편 DCO 의미 설명이다. 저자가 반영하고 해당 관점의 검토자가 수정 부분을 다시 검수했다. SCC 1편의 긴 설정 키에는 줄바꿈 기회만 추가해 모바일 가로 넘침도 해소했다. 기존 CSS·SVG·시리즈 박스는 유지했다.

로컬 검증:

```sh
python3 labs/open-source-contribute/updates-2026-10-23/validate.py
# Playwright와 Chrome이 설치된 Python에서는 --browser로 390/1100px 네 글 확인
```

이 검증은 글의 구조·표시·원자료 일치를 확인한다. 최신 upstream head의 전체 테스트를 새로 실행한 결과가 아니며, 과거 재현 SHA와 로그를 최신 결과로 치환하지 않았다. 업로드는 기존 네 글 번호와 실제 공개 범위를 유지한다.
