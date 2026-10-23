# 배포 관측과 A/B 실험

2026-10-23 실제 실행·글 3편·화면 8장을 작성했다. 기존 배포 안전성 글의 Kayenta 분류기 Python 이식 실습에서 확장해 실제 Netflix 계열 도구와 관측 데이터를 연결했다. 네 관점 퇴고와 별도 원자료 감사·업로드 검증은 실습의 `validation/`에 기록한다.

| 편 | 제목 | 실습 |
|---|---|---|
| 1 | [오래된 A 대신 새 베이스라인 A′와 B를 비교한다](01_1%ED%8E%B8%20-%20%EC%98%A4%EB%9E%98%EB%90%9C%20A%20%EB%8C%80%EC%8B%A0%20%EC%83%88%20%EB%B2%A0%EC%9D%B4%EC%8A%A4%EB%9D%BC%EC%9D%B8%20A%E2%80%B2%EC%99%80%20B%EB%A5%BC%20%EB%B9%84%EA%B5%90%ED%95%9C%EB%8B%A4.html) | `canary` |
| 2 | [A/B 테스트 사용자는 새로고침해도 같은 그룹이어야 한다](02_2%ED%8E%B8%20-%20A%C2%B7B%20%ED%85%8C%EC%8A%A4%ED%8A%B8%20%EC%82%AC%EC%9A%A9%EC%9E%90%EB%8A%94%20%EC%83%88%EB%A1%9C%EA%B3%A0%EC%B9%A8%ED%95%B4%EB%8F%84%20%EA%B0%99%EC%9D%80%20%EA%B7%B8%EB%A3%B9%EC%9D%B4%EC%96%B4%EC%95%BC%20%ED%95%9C%EB%8B%A4.html) | `sticky-ab` |
| 3 | [전환율이 높아도 표본과 가드레일부터 확인한다](03_3%ED%8E%B8%20-%20%EC%A0%84%ED%99%98%EC%9C%A8%EC%9D%B4%20%EB%86%92%EC%95%84%EB%8F%84%20%ED%91%9C%EB%B3%B8%EA%B3%BC%20%EA%B0%80%EB%93%9C%EB%A0%88%EC%9D%BC%EB%B6%80%ED%84%B0%20%ED%99%95%EC%9D%B8%ED%95%9C%EB%8B%A4.html) | `decision` |

[실행 안내](../../../../labs/devops/deployment-experiments/README.md)

A(먼저 기동해 캐시를 채운 기존 버전), A′(같은 버전을 새로 띄운 베이스라인), B(같은 시점에 띄운 변경본)를 그래프에 모두 표시했다. A는 로컬 모델이며 장기 운영 서버를 측정한 것이 아니다. A′와 B의 생성 시점·자원·워밍업·부하·관측 구간을 맞췄다. A와 A′는 재배포 영향 진단이며 주 판정은 A′ 대 B다.

실제 Kayenta 판정과 Spinnaker 보고서, 사용자 할당 유지와 사용자 단위 노출·전환, 표본 부족·SRM·가드레일을 다룬다. 합성 데이터의 전환율 차이는 제품 개선의 근거로 해석하지 않는다. 회사 Notion 반영은 별도 요청 때 진행한다.

티스토리 업로드: [1편](https://dding-shark.tistory.com/704), [2편](https://dding-shark.tistory.com/705), [3편](https://dding-shark.tistory.com/706). 실제 공개 범위·이미지 로드·원자료 감사 결과는 [발행 기록](../../../../labs/devops/deployment-experiments/validation/publication.json)에 보존한다. 스크린샷 8개는 고정 커밋의 이미지 주소를 사용한다.
