# 57편 논리 모순 패널: 라운드 1

- 판정: 수정 후 재검 필요
- 지적: 1건
- HTML SHA256: `156d6aae75fdac9b7ebe95595aa251009961ad1bb9fa9cc1015e2df0f6378545`
- 범위: 글 내부 주장·관찰 순서·그림·원자료 사이의 논리 정합성. HTML은 수정하지 않았다.

## L1. 도입의 동시 관측 표현이 마지막의 순차 조회 한정과 충돌한다

- 위치: HTML 34행, “같은 순간 파드 IP로 직접 보낸 요청에는 HTTP 200이 돌아왔고요.”
- 문제: 초기 관찰은 `run.py`에서 Pod 상태 조회 → readyz 직접 요청 → api/info 직접 요청 → NodePort 요청으로 순차 실행했다. 3절 125행과 6절 203행은 개별 조회를 원자적인 시점으로 취급하지 않는다고 정확히 한정하지만, 도입은 같은 순간에 두 결과를 확보했다고 단언한다.
- 근거: `03-early-direct-readyz.json` 완료시각은 15:07:24.958574 UTC, `03-early-direct-api-info.json`은 15:07:25.043923, `04-early-nodeport.json`은 15:07:25.057478이다. 이 증거는 같은 초기 준비 구간에서 순차 확인한 결과이지 동시 스냅샷이 아니다.
- 수정안: 도입을 “kubectl apply는 성공했는데 Mac에서 NodePort로 보낸 curl은 연결에 실패했어요. 파드는 Running이었고, 같은 초기 준비 구간에 파드 IP로 직접 보낸 요청에는 HTTP 200이 돌아왔어요.”로 고친다. 이렇게 쓰면 실제 초기에 관측한 클라이언트도 브라우저로 확대하지 않는다.

## 대조 결과: 추가 지적 없음

- Running/Ready/EndpointSlice/HTTP를 별도 확인으로 일관되게 구분한다. readiness 실패가 재시작 또는 직접 Pod 접근 차단을 뜻한다고 쓰지 않았다.
- rollout 표본 129건 중129건200(v1 42/v2 87), replacement 120건 중108건200과12건전송실패(rc7 8/rc28 3/rc56 1)가 원본과 일치하며 실패0표본을 보장으로 일반화하지 않는다.
- timeline은 rollout에서 v1 ready/v2 unready → v2 ready/old terminating+serving → v2만ready 순서를 실제로 보인다. 그림3과 일치한다.
- replacement에서 old terminating과newRunning이 동시 존재해도 글의 “기존파드종료 → 새파드준비”는 새파드 생성 시점과 준비 완료 시점을 혼동하지 않는다. 실제 old 종료 후newReady 사이 구간과12실패가 있다.
- 최종 앱 유지와임시클라이언트삭제가 양립한다. 정리명령은 나중의 사용자가 실행할 선택지로 제시했으며 이미앱삭제를 주장하지 않는다.
- v1→v2는 같은 이미지·소스의 APP_VERSION 구성 변경이라고 일관되게 설명한다. 이미지빌드·CI/CD를 검증했다고 확대하지 않는다.
- 직접 API200/readyz503/NodePort연결실패는 명시적으로 의도한 준비 판정의 분리와 일치한다.
