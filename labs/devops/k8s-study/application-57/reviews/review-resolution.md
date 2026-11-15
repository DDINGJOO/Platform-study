# 57편 검수 및 수정 기록

## 라운드1

- 사실관계1건과 논리1건은 같은 도입문장이다. 초기 실패는 브라우저 관측이 아닌 NodePort curl이며 직접 Pod 요청과 순차 관측이었다. 실제 근거에 맞춰 수정했다.
- 독자3건: request-client 생성 및 Ready 대기 명령 추가; 환경별 nodeSelector 조정 안내; NodePort 용어박스를 첫 캡처 앞으로 이동; UID 첫 언급에 객체 식별자 설명. (클라이언트 생성/대기는 지적1건이다.)
- 문장 일관성0건.
- 중복을 제거한 수정지적4건 모두 반영했다. 추가로 Downward API 공식 링크와 실제 client 정리 명령도 명시했다.

## 라운드2

네 관점 모두 재검0건. 검토한 본문 SHA는 각보고서에 기록했다.

## 화면 확인 및 라운드3

실제 브라우저에서 그림1의 두 화살표 중 앞쪽에 화살촉이 없는 문제가 보였다. 하나의 SVG path에 두 subpath를 넣어 marker-end가 마지막 끝점에만 붙었기 때문이다. 같은 좌표·스타일을 두 개의 path로 분리했다. 본문과 기술 주장은 변경하지 않았다. 논리 검수자가 독립 재검했고 남은 지적0건이다.

최종 HTML SHA256: 002da5d316cd6fe45b745f6c85377a6fbdcf576c3e7deba7ac3e23930ea6736f

## 자동 검증 및 화면

원본 HTTP 표본 재집계, requestID 대응, Service UID/address 유지, Pod UID 변경, ownerReferences UID 링크, readiness 실패 상태, 최종 DNS/Service/NodePort 응답, CRI/netns/CNI 경로, immutable ConfigMap와 소스 일치를 verify.py로 확인했다.

템플릿 CSS 동일·태그/SVG 파싱·6절/7용어/3SVG/3이미지·엠대시0을 확인했다. 실제 앱과 글 모두 모바일390px에서 가로 넘침이 없었다. PC에서도3이미지 로드와3SVG 라벨의 viewBox 경계를 확인했다.

사실관계 감사는 위 패널과 다른 담당자가 원본에서 별도로 수행하며 audit.md에 기록한다. 커밋·push·발행·Notion write는 수행하지 않았다.
