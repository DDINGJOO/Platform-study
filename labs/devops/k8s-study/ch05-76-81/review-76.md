# 76편 감사 기록 (2026-11-21)

대조한 것: 본문 수치·출력 ↔ out/76-pod-lifecycle-ledger.txt(.sh), 인용한 다른 편 원자료(out/77-mysql-pod, 78-label-service-ip, 79-same-node-ping-counters, 79-cross-node-ipip, 80-delete-race, 80-rollout-drop-kinds, 80-rollout-drop-repeat, 80-e28-trace, 81-status-subresource), 77~81편 본문(읽기만), LAB shared/ch05-pod/lecture-notes.md "2편", 편 번호 ↔ posts 파일명과 해당 편 본문(2, 22, 24, 25, 27, 28, 30, 34, 41, 43, 50, 51, 52, 57~67편). 6절 명령은 실습 클러스터에서 읽기 전용으로 출력 모양만 확인했다(kube-system 의 endpointslice get).

## 지적 목록

| # | 편 | 위치 | 문제 | 근거 | 조치 |
|---|---|---|---|---|---|
| 1 | 76 | 4절 restartCount 용어 박스 | "기다리는 동안 STATUS 칸에 CrashLoopBackOff가 보여요"는 81편의 핵심 관찰과 어긋난다 | 81편 3절·요약: v1.37.2 컨테이너 하나짜리 파드는 백오프 내내 STATUS 가 Error, CrashLoopBackOff 는 재시작 직전 0.1초(81-crashloop-watch) | 반영: 대기 사유로 적힌다고 고치고 81편의 Error/0.1초 관찰을 덧붙임 |
| 2 | 76 | 5절 지우기 해석 | "+1.0초에는 SIGTERM을 받은 nginx가 끝나" 는 틀렸다. 삭제 때 kubelet·containerd 가 보내는 정지 신호는 이미지의 STOPSIGNAL 이다 | 65편: nginx:1.27-alpine 이미지 StopSignal=SIGQUIT, 80편 1절 "nginx 이미지의 정지 신호는 SIGQUIT" | 반영: "정지 신호(nginx 이미지는 SIGTERM이 아니라 SIGQUIT, 65편)" |
| 3 | 76 | 5절 롤링 업데이트 단락 | 종류 실험 한 번만 옮겨 "preStop과 readinessProbe를 함께 둔 경우만 … 0" 이라 했다. 80편은 반복 실험까지 네 번을 묶어 결론을 냈고 preStop 만 둔 경우도 두 번 0이었다. "약 14만 5천" 은 145,715 의 버림 | 80-rollout-drop-repeat.txt 범위 줄((a) 30~45, (b) 0~11, (c) 0 / 419,582, (d) 32~38) + kinds((a) 64, (b) 62, (c) 0 / 145,715, (d) 38) → 80편 표 (a) 30~64, (b) 0~62, (c) 0 / 565,297, (d) 32~38 | 반영: 145,715 정확히, 네 번 범위와 (c) 네 번 모두 0(56만 5,297건) 추가 |
| 4 | 76 | 5절, 지우기 콜아웃 | "지우기" 단계가 객체·엔드포인트·규칙·IP 정리로 끝난다고만 읽힌다. 80편이 밝힌 롤아웃 뒤 타임아웃(e28)의 원인, 곧 죽은 파드로 DNAT 된 conntrack SYN_SENT 항목과 출발 포트 재사용이 빠졌다 | 80편 5절: tcpdump 기록 중 e28 81건 모두 옛 파드 IP DNAT, 61건은 실패한 출발 포트 재사용, SYN_SENT 120초. 추적 세 회차 한정 | 반영: 한 단락(세 회차 한정 명시)과 콜아웃 첫 줄에 "conntrack 항목은 그 뒤에도 남을 수 있다(80편)" |
| 5 | 76 | 4절 nodeName patch 해석 | "바꿀 수 있는 칸은 이미지, activeDeadlineSeconds, toleration 추가 같은 몇 개" 의 toleration 은 원자료에 없다. 스크립트가 메시지를 200자에서 잘라 `spec.t` 에서 끊겼다 | 76-pod-lifecycle-ledger.txt 2절, .sh 의 `cut -c1-200` | 반영: 보이는 항목(컨테이너·init 컨테이너 이미지, activeDeadlineSeconds)과 잘린 사실, diff 의 NodeName 줄만으로 서술 |
| 6 | 76 | 4절 81편 status 단락 | "status 본체에 phase=Failed를 패치" 는 경로를 거꾸로 읽게 한다(81편은 "본 리소스"). "status는 kubelet이 쓰는 칸" 은 81편 6절(스케줄러·노드 컨트롤러·DisruptionTarget)과 이 글 2절(PodScheduled 는 API 서버)과 어긋나는 일반화 | 81-status-subresource.txt "본 리소스로 status.phase 를 Failed 로 패치", 81편 6절 마지막 단락 | 반영: "본 리소스 경로로 status.phase를", "파드가 노드에 올라간 뒤 phase와 kubelet 소유 condition은 kubelet이 기준" |
| 7 | 76 | 3절 Calico 단락 | "위 출력의 둘째 줄" 이 가리키는 라우팅 줄은 코드 블록의 셋째 줄이다(둘째 줄은 "노드 상태:") | 본문 코드 블록 | 반영: 셋째 줄 |
| 8 | 76 | 3절 Calico 단락 | "같은 노드의 파드끼리는 cali 장치 사이를 바로 오가고" 는 79편 결론(브리지 0개, 노드 커널의 /32 경로로 한 번 라우팅, TTL 64→63)과 달리 L2 로 바로 붙은 것처럼 읽힌다 | 79편 1·2절, 79-calico-tunl0-not-bridge | 반영: "노드에는 브리지가 없어요. 노드 커널이 /32 경로로 상대 cali를 골라 주고 tunl0는 지나지 않아요" |
| 9 | 76 | 6절 명령 ②⑤ | ② `kubectl get endpointslice -o wide` 는 ENDPOINTS 칸에 주소만 찍고 ready 조건을 보여 주지 않는다. ⑤ 주석은 "엔드포인트의 terminating" 을 약속하는데 해당 명령이 없다 | 클러스터 출력 열: NAME ADDRESSTYPE PORTS ENDPOINTS AGE. jsonpath 명령은 kube-dns 에서 `ready=true serving=true terminating=false` 로 동작 확인 | 반영: ② 를 conditions jsonpath 로, ⑤ 주석에 "②의 명령에서 terminating=true인 줄" |
| 10 | 76 | 도입 셋째 단락 | "세 구간 모두 2초 안팎" 인데 만들기 0.9초, 재시작 1.0초, 삭제 2.0초 | 76-pod-lifecycle-ledger.txt 1·3·4절 | 반영: "2초 안에 끝났고" |
| 11 | 76 | 도입 첫 단락 | "같은 순간 EndpointSlice에도" 는 파드와 EndpointSlice 를 차례로 읽은 한 번의 관측이다 | .sh snap() | 반영: "같은 관측에서 … 들어가 있었어요" |
| 12 | 76 | 4절 kill 1 단락 | "핸들러가 있어서 정상 종료" 는 SIGTERM 을 우아한 종료로 오해하게 한다. nginx 는 SIGTERM 을 빠른 종료, SIGQUIT 을 우아한 종료로 다룬다 | 65편 4절, ledger lastState Completed exitCode=0 | 반영: "SIGTERM에 핸들러가 있어서 바로 끝났고 종료 코드는 0" + 65편 |
| 13 | 76 | 4절 81편 단락 | 다시 띄우기 단계의 81편 근거가 질문 목록뿐이고 81편의 수치(간격 1→13→27→48→88초, UID·IP 불변, 지터)가 없다 | 81-crashloop-restart.txt, 81편 1~3절 | 반영: 한 문장 추가(첫 재시작은 바로, 이후 10·20·40·80초 + 몇 초, 81편은 지터로 설명), 출처에 81-crashloop-restart.txt |
| 14 | 76 | 3절 IP 종류 단락 | externalIPs 를 "할당도 인터페이스도 없다" 로만 적어 78편의 결론(규칙이 모든 노드에 생겨 아무 주소나 가로챔)이 빠졌다 | 78편 4절·요약, 78-externalip-anyaddr | 반영: "규칙만 모든 노드에 생겨 … 같은 포트로 가는 요청을 가로챘어요" |
| 15 | 76 | 2절 만들기 단락 | Secret 참조를 말하면서 77편의 핵심(값은 kubelet 이 채움, secrets 권한 없이 파드만 만들 수 있는 계정이 로그로 비밀번호를 읽음)이 빠졌다 | 77편 3·4절, 77-secret-visibility | 반영: 두 문장 추가 |
| 16 | 76 | 그림 1 회색 편 번호와 표 "자세히" 열 | 표에만 있는 번호가 있다(만들기 34, 통신 61, 다시 띄우기 77) | 그림은 요약, 표는 상세. 61편(컨테이너의 네트워크 네임스페이스 공유)은 통신 단계와 관련이 약하지만 틀린 연결은 아니다 | 반박(유지) |

## 확인했고 문제없던 것
- 76 자체 실험: +0.2s node=worker3 ip=- Pending, +0.9s ip=10.244.100.249 Running ready=True와 EndpointSlice r=true, 이벤트(default-scheduler Scheduled, kubelet Pulled·Created·Started), managedFields(kube-controller-manager / , calico / status, kubelet / status), managed-by endpointslice-controller.k8s.io, worker3 경로 `dev cali99f27912842 scope link`, 마스터 iptables 3줄과 DNAT 줄, patch 거절과 patch 뒤 k8s-worker3, kill 1 뒤 +1.0s restarts=1·uid 735ebc4d 그대로·lastState Completed exitCode=0, 삭제 +0.2s r=false,s=true,t=true와 새 파드 nxskf Pending, +1.0s Succeeded·새 IP 10.244.100.211, +2.0s 옛 파드 사라짐, 옛 IP 경로 빈 줄·iptables 0줄. 그림 4(SVG)의 UID·IP·노드도 같다.
- 이미지 2장: 01-nodename-forbidden.png(2절 출력), 02-who-writes.png(이벤트·managedFields·관리자 라벨) 내용과 alt 일치.
- 인용 수치: 78 라벨 app=other → endpoints null, ClusterIP 0ms 거부, 파드 IP 응답 / 79 tunl0 rx=1528 tx=599 그대로, worker3 tunl0 rx 1528→1531 / 80 delete-race 75ms·0.35초·224번 모두 200, preStop sleep 5 약 5초(5.1초) serving=true / 81 patched (no change), 12초 뒤 다섯 condition 복귀 / 77 mysql:8.4 +2s Error, restarts 2·3·4 를 본 시점 +13·+42·+90초.
- 편 번호: 2(apply→파드), 25·50(Unknown, 300초 toleration, 축출 뒤 대체 파드), 27(RunPodSandbox 등 CRI), 28(노드마다 kube-proxy 규칙), 30(경로는 Felix proto 80, BIRD 는 BGP 로 블록을 알리고 커널에는 넣지 않음), 34(CNI DEL 과 노드 장애 때 남는 IP), 41(nodeName·PodScheduled 를 API 서버가 바인딩 때 함께 저장, managedFields 에 스케줄러 없음), 51(CNI 는 연결, Felix 는 유지), 52(IPIP), 57(readiness·EndpointSlice), 58(calico 가 status 하위 리소스로 주석을 씀), 59(client dry-run 뼈대), 60(ReplicaSet 컨트롤러), 63(Terminating 은 phase 아님), 64(30초 뒤 SIGKILL), 65(sh -c 와 신호, nginx SIGQUIT), 67(grace 는 preStop 시작부터) 모두 그 편 제목·내용과 맞다.
- 형식: style 블록 템플릿과 동일, lead 135자, 시리즈 박스 series-boxes.html 과 동일, h2 6, SVG 2, 용어 박스 6, 콜아웃 3, 요약 박스로 끝, 엠대시 0, 강의·슬라이드·수업·강사 0, 띄운 조사는 코드 블록 안에만, 태그 짝·중복 id 이상 없음, mask-check 깨끗함(수정 뒤 다시 확인).

## 남은 위험
- 80·81편은 다른 감사자가 고치는 중이다. 76편에 옮긴 80편 수치(30~64, 0~62, 32~38, 145,715, 565,297, e28 81건 중 61건)와 81편 수치(1·13·27·48·88초, STATUS 0.1초)는 지금 본문과 out/80-rollout-drop-repeat.txt·80-rollout-drop-kinds.txt 로 맞췄다. e28 의 81건·61건은 80편 본문 값을 따랐고 80-e28-trace.txt 를 전부 다시 세지는 않았다. 그 편 숫자가 바뀌면 76편도 따라 고쳐야 한다.
- 76 실험은 한 번 실행이고 시각은 0.2초 잠들기 + kubectl 두 번을 도는 관측 시각이라 실제 바뀐 시각보다 늦을 수 있다(본문은 "보였어요·있었어요"로 적음).
- nodeName 거절 메시지 전문(바꿀 수 있는 칸의 전체 목록)은 out/ 에 없다. 필요하면 스크립트의 `cut -c1-200` 을 늘려 다시 받아야 한다(out/ 수정 금지라 보고만).

지적 16건 → 반영 15건
