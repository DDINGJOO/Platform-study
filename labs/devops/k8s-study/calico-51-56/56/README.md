# 56편: Calico 장애 진단의 대조 실험

2026-11-14 KST. Kubernetes v1.37.2, Calico v3.33.0, IPIP Always. 명령 실행 23:35분대, 종료 및 청소 조회는 commands.json에 개별 시각을 기록했다.

## 재현

Mac에서 Lima 4노드 실습 클러스터가 켜진 상태로 `python3 run.py`를 실행한다. 스크립트의 LAB 경로는 이 개인 실습 저장소의 lab 래퍼 절대경로다. 자신의 환경에서는 이 경로와 노드 이름을 바꾼다. worker1·worker2에 nginx:1.25.1-alpine, worker1에 curlimages/curl:8.11.1 이미지 캐시가 필요하다(imagePullPolicy=Never). 실행은 약 2분 이내였으며 namespace 종료 중 컨테이너의 기본 종료 유예를 기다렸다. kubectl 권한과 worker2의 iproute2가 필요하다.

`run.py`는 기존 calico-blog-56 namespace가 있으면 시작을 거부한다. 생성한 3개 Pod, Service 1개, 임시 NetworkPolicy만 이 namespace에 넣는다. 전역 정책, 노드 경로·iptables, VM 상태는 바꾸지 않는다. cleanup은 자신이 생성한 namespace만 finally에서 삭제한다. 재실행하면 이 디렉터리의 수집 파일을 덮어쓰므로 다른 출력 디렉터리에 스크립트를 복사해 실행한다.

## 결과

- 66개 명령 기록, 새 curl 프로세스로 보낸 요청 24회.
- 정상: 같은 노드 Pod / 다른 노드 Pod / ClusterIP / DNS 이름 모두 HTTP 200.
- Service targetPort=8081: 실제 nginx listen은 80. EndpointSlice 대상 1개, ready=true, port=8081. Pod 직접 요청은 200, Service 요청은 curl 7.
- selector 불일치: Pod와 Service는 존재하나 EndpointSlice endpoints=null. Pod 직접 요청은 200, Service 요청은 curl 7.
- 대상 Pod ingress deny: 같은 노드의 별도 대조 서버는 200, 다른 노드 대상 Pod/Service/이름 요청은 curl 28(약 2초 연결 제한). 정책 제거 후 모두 200.
- 잘못된 이름: curl 6. 이름을 고친 뒤 200. DNS 서버 장애를 재현한 것이 아니다.
- 목적지 worker2의 blackhole 10.244.126.0/26과 Pod 10.244.126.28의 /32 경로를 함께 확인. route get .28은 cali 장치를 선택, 별도 호스트 경로가 없던 .62는 exit 2, EINVAL. .62의 IPAM 할당 여부는 판정하지 않았다.
- namespace 삭제 명령 exit 0, 후속 조회 stdout 비어 있음. 종료 시 노드 네 대 Ready.

curl 6/7/28과 blackhole route get exit 2는 의도한 비교 결과이므로 모든 명령 exit 0을 성공 기준으로 삼지 않는다. commands.json에서 preflight부터 cleanup까지 원문을 대조할 수 있다. 요청별 시각이 다르고 조건을 바꾼 뒤 2초를 기다렸으며 반영 지연의 상한을 측정한 실험은 아니다. 요청 성공과 객체 스냅샷이 각각 관측 근거다. 기존 keep-alive 연결·TLS·경로 삭제·터널 장애·복합 장애는 이번 검증 범위가 아니다.

## 파일

- run.py: 재현 스크립트. resources.json과 deny-web.json은 실제 적용한 매니페스트.
- commands.json / commands.txt: 명령·시각·종료 코드·stdout/stderr. stdin 매니페스트는 위 파일에 별도 보관.
- matrix.json: 실제 curl 요청 24회, facts.json: 실제 주소와 경로 조회 대상.
- matrix-capture.txt: matrix.json에서 주요 단계의 종료 코드·HTTP 코드만 추려 만든 이미지용 파생 표. 원문 출력 그대로의 화면이라고 부르지 않는다.
- decision-capture.txt: 관련 원문에서 목적지 포트·대상 수·청소 결과를 추린 보조 자료.
- write_post.py: 템플릿 스타일을 유지해 담당 HTML만 만드는 생성기.
- validation.json: 태그·SVG XML·고유 ID·스타일 일치·실측 수·청소 검증 결과.
- mask-allow.json: 이 개인 실습에서 생성된 주소와 사람이 허용한 이유. 공통 .mask-allow는 수정하지 않았다.
- 저장소의 posts/CS/DevOps/k8s-study/images/calico-56/matrix.png: term-shot.py --from으로 생성한 파생 표 이미지. 원문은 matrix.json이며 생성 후 육안 확인했다.

## 마스킹 판단

본문의 mask-check.py 결과는 개인 Lima 실습 IP 7종만 일반 패턴으로 탐지했다. 이 값은 mask-allow.json에 목적과 출처를 기록했다. 조직 목록 적중·토큰·계정·이메일·내부 URL 적중은 없었다. 이미지용 matrix-capture.txt에는 IP와 자격정보가 없으며 term-shot.py 사전 검사도 통과했다. 공유 허용 목록은 변경하지 않았다. kubeconfig·토큰·Secret은 수집하지 않았다.

## 공식 출처 (2026-11-14 확인)

- https://kubernetes.io/docs/tasks/debug/debug-application/debug-service/ : 포트·selector·EndpointSlice·Pod 직접 요청을 대조하는 Service 진단.
- https://kubernetes.io/docs/concepts/services-networking/network-policies/ : 방향별 격리, 대상 선택과 허용 규칙.
- https://man7.org/linux/man-pages/man8/ip-route.8.html : blackhole의 로컬 EINVAL 및 경로 조회 도구.
- https://curl.se/libcurl/c/libcurl-errors.html : 종료 코드 6·7·28의 범위. 7을 RST의 직접 증거로 쓰지 않는다.

기존 28·29·30·47편의 설명을 연결하되 교과서 내용을 반복하기보다 이번 대조 실험의 판별 근거에 집중했다. 신규 HTML과 그림·실험 파일만 작성했다. 커밋·푸시·업로드는 하지 않았다.
