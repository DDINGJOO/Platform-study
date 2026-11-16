# 2026-11-15 블로그 계획 — 5장 1편(오브젝트와 파드) + 딥다이브 3묶음 (58~75편)

기준: blog-post-pipeline "글감은 독자가 검색할 문제에서 출발한다"(질문형 제목, 읽고 나서 무엇을 바꾸나), tistory-sketch-post(도입 장면, 4~6장, 그림 2~4, 용어 박스 4~8, 콜아웃 2~5, 요약 박스로 끝, 예고 없음).
흐름: 강의 편(58~63)이 남긴 질문을 "왜" 시리즈가 받는다. 63 의 "지우는 데 31초" → PID 1(64~67) → 67 의 종료 규칙 → 사이드카 종료 순서(68~71). 59 의 apiVersion → API 버전(72~75).
기존 편과 겹침: shim·런타임 재시작 26편, pause 43편, CRI 호출 27편, taint 37편, etcd 저장 22편, etcd 백업 40편 → 링크만.

## A. 강의 편 (근거: shared/ch05-pod/)

| 편 | 제목(검색 질문) | 읽고 나서 바꾸는 것 | 근거 |
|---|---|---|---|
| 58 (허브) | 쿠버네티스 오브젝트 관계도는 어떻게 읽을까, 화살표마다 일하는 컨트롤러 | 만들었는데 아무 일도 없으면 그 화살표의 컨트롤러(Ingress 컨트롤러, metrics-server, provisioner)부터 본다 | 05, 06, 10 / 화살표마다 증거 한 줄 + 세부 편 번호 |
| 59 | kubectl apply 전에 YAML 실수를 잡는 법, explain과 dry-run=server | apply 전 dry-run=server, --validate=false 금지, 알파 필드는 에러 없이 버려진다(httpGet.protocol, stopSignal)는 걸 알고 status 로 확인 | 08, 09, 16, 17, why/07 04 |
| 60 | ReplicaSet은 왜 내가 만든 파드를 지울까, 라벨 셀렉터와 Deployment | 라벨을 겹치게 만들지 않는다, 문제 파드는 라벨을 떼서 격리, RS 직접 대신 Deployment | 10, 11 |
| 61 | 한 파드의 컨테이너는 무엇을 공유하고 같은 포트를 쓰면 어떻게 될까 | 같은 파드 컨테이너끼리 포트를 나눠 쓰고, 파일은 볼륨으로 넘긴다 | 13, 15, why/02 01-pod-sandbox |
| 62 | kubectl rollout status가 성공했는데 파드는 왜 죽어 있을까 | CI 에서 rollout status 만 믿지 않는다: minReadySeconds·readiness, progressDeadline 이 Ready 깜빡임에 리셋, 종료 중 파드 안 기다림 | 14, 14b, 18, 19, sources/ |
| 63 | 파드 phase와 conditions는 어떤 순서로 바뀌고 Terminating은 왜 phase가 아닐까 | Terminating 을 phase 로 다루지 않는다(deletionTimestamp), lastTransitionTime 비교 전에 노드 시계 확인 | 02, 02-clock-skew, 03·03b·03c, 20 |

## B. PID 1 과 신호 (근거: shared/why/07-pid1-and-signals/)

| 편 | 제목 | 핵심 | 근거 |
|---|---|---|---|
| 64 | sleep infinity 파드는 왜 지우는 데 30초가 걸릴까, 컨테이너 PID 1과 커널 규칙 | 2.6.30(2009) 부터 컨테이너 init 은 핸들러 없는 신호를 버리고 조상 ns 의 SIGKILL·SIGSTOP 만 받음. kill 은 0 을 돌려줌 | 01, 06, kernel v6.8 signal.c, ch05 04 |
| 65 | sh -c로 감싼 컨테이너는 왜 SIGTERM에 반응하지 않을까, exec와 trap | 9가지 PID 1 모양별 삭제 시간(31초 vs 0.7초), trap 이 전경 명령에 막힘(POSIX 2.12) | 02, ch05 12b |
| 66 | 쿠버네티스에는 왜 docker run --init이 없을까, 좀비와 tini와 pause | 좀비 20개 실험, Docker --init(1.13, tini), pause 신호 전달 PR 미머지, #84210 열림 | 03, moby PR, pr-29747, why/02 |
| 67 | preStop과 terminationGracePeriodSeconds는 어디서부터 세고 1.37의 stopSignal은 왜 안 먹을까 | preStop 시간은 grace 에서 빠지고 최소 2초, 신호 선택 순서(스펙→STOPSIGNAL→SIGTERM), stopSignal 알파 1.33 그대로·조용히 지워짐 | 04, 05, kubelet·containerd 소스 |

## C. 사이드카 (근거: shared/why/06-sidecar-containers/)

| 편 | 제목 | 핵심 | 근거 |
|---|---|---|---|
| 68 | 쿠버네티스 Job에 사이드카를 붙이면 왜 끝나지 않을까 | #25908(2016, +1 422개), quitquitquit·holdApplicationUntilProxyStarts 우회, 옛 방식 1/2 NotReady | 04, ch05 12, issue-k8s-25908 |
| 69 | 사이드카 KEP는 왜 몇 년 멈췄다가 initContainers로 들어왔을까 | 1.15~1.18 네 번 연기, 2020 반대 원문, 2022~23 WG 가 버린 대안들, Always 로 정리 | kep-753 판본들, pr-80744, WG 노트 |
| 70 | 네이티브 사이드카는 어떤 순서로 뜨고 죽을까 | startupProbe·postStart 는 다음 시작을 막고 readiness 는 안 막음, 종료는 앱 뒤 역순 TERM, 유예 바닥나면 동시 TERM 후 2초, exit 137 의 정체 | 01, 02, 03, 03b, kubelet 소스 |
| 71 | 컨테이너마다 restartPolicy를 주면 사이드카가 될까, restartPolicyRules | 보통 컨테이너 Always 는 파드가 안 끝남, KEP-5307(1.34 α, 1.35 β), KEP-4438 열림 | 05, kep-5307, kep-4438 |

## D. API 버전 (근거: shared/why/08-api-versions-deprecation/)

| 편 | 제목 | 핵심 | 근거 |
|---|---|---|---|
| 72 | 같은 HPA를 autoscaling/v1과 v2로 동시에 읽을 수 있는 이유 | 내부 버전 + 변환, etcd 엔 v2 한 벌, v1 로 읽으면 annotation 3개, hpa.v1.autoscaling 함정 | 01, 02, ch05 06 |
| 73 | no matches for kind 에러는 왜 날까, API deprecation policy가 정해진 과정 | 2017 첫 판 → 2018 노드 skew 사고로 3릴리스 → KEP-1635·3136 → GA 제거 금지 | website PR 이력, kep-3136, ch05 06·07 |
| 74 | API 버전을 지워도 etcd의 옛 데이터는 어떻게 될까, storage version과 StorageVersionMigration | CRD 23개가 v1beta1 로 저장, 시험 CRD 마이그레이션 20초, #52185 아직 열림 | 03, 04, issue-52185 |
| 75 | 업그레이드 전에 deprecated API를 누가 쓰는지 찾는 법 | Warning 헤더(KEP-1693), apiserver_requested_deprecated_apis, v1 Endpoints 경고, 호출자는 감사 로그로 | 05, kep-1693 |

## 빠지는 것
- ch05 02 의 41.9초(6회 재측정 모두 31초대, 측정 쪽 이상)
- ch05 19 의 Failed(시험용 컨테이너 구성 탓)
- 스크립트 실수로 다시 돌린 것들
- 각 why notes.md 의 "9. 확인 못 한 것"은 글에 단정하지 않는다(사이드카: 2020 서명자 실명·비공개 논의·노드 종료 시 순서, PID 1: LKML 동기·busybox exec 최적화 소스, API: HPA 저장 버전 전환 릴리스 등)

## 작성 방식 (승인 뒤)
작성 에이전트 병렬(묶음별) → 편별 사실 감사 → 퇴고 → 메인이 교차 참조·시리즈 박스(5줄 창)·README·tistory-series.json → 보여 드리고 승인 뒤 커밋.
