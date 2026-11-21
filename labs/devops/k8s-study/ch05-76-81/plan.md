# 5장 2편 블로그 계획 초안 (2026-11-21) — 파드 생명주기 순서

방침(사용자): 글 목록은 파드 생명주기 순서(만들기 → 연결 → 통신 → 지우기). mysql:5.7 arch 문제는 뺀다. 58~75편·51~57편과 겹치는 건 링크.
기준: blog-post-pipeline(질문형 제목, 읽고 나서 무엇을 바꾸나), tistory-sketch-post.

| 편 | 제목(검색 질문) | 읽고 나서 바꾸는 것 | 근거 | 겹침·링크 |
|---|---|---|---|---|
| 76 (허브) | 파드 하나가 만들어지고 지워지기까지 무엇이 바뀔까, 생명주기 지도 | 장애를 볼 때 지금 어느 단계(만들기·연결·통신·지우기·재시작)인지부터 가른다 | 21~31 전체, 단계마다 증거 한 줄 + 편 번호 | 58(관계도 허브), 63, 64~67 |
| 77 | env로 넣은 비밀번호는 왜 kubectl describe에 보일까, Secret과 secretKeyRef | 비밀번호를 env value 대신 secretKeyRef 로, pods·secrets 권한을 나눈다 | 24 (+22 명령형 run/expose 의 라벨) | 22편(etcd 암호화) |
| 78 | Service는 파드를 어떻게 찾고 파드 IP·ClusterIP·externalIP는 어디서 닿을까 | 라벨·셀렉터를 먼저 확인, externalIPs 대신 NodePort/LB(1.36 deprecated) | 21, 22, sources/externalips-warning | 28(ClusterIP ping), 24(LB pending), 60(라벨) |
| 79 | Calico 노드에는 브리지가 없다, 같은 노드와 다른 노드의 파드 통신은 어디를 지나갈까 | 통신 장애를 볼 때 같은 노드/다른 노드부터 가르고 tunl0·cali 카운터와 경로를 본다 | 25, 25b, 26, 27 | 51(veth), 52(IPIP), 30(Felix), 56(구간별 진단) |
| 80 | 롤링 업데이트 중에 요청이 왜 끊길까, preStop과 readiness는 각각 무엇을 막나 | 배포 중 끊김을 "누가 늦게 아느냐"로 보고 preStop(지우는 쪽)·readiness(뜨는 쪽)를 둘 다 넣는다. headless 는 DNS 캐시까지 | 28, 32, 32b, 32c (preStop+readiness 0/14.5만, 나머지 38~64건, headless 캐시 33/74) | 62(terminatingReplicas), 67(grace), 57(readiness) |
| 81 | CrashLoopBackOff는 파드를 다시 만드는 걸까, 재시작 백오프와 status의 주인 | 재시작 횟수·간격을 읽고, status 는 edit 로 못 고친다는 걸 안다 | 29, 30, 31, sources/crashloop-gates | 63(phase·Terminating), 60(컨트롤러) |

## 쓰기 전에 확인할 것
- 80: 실패 재현 완료(32c). 남은 것: 롤아웃과 무관한 시각의 e28 타임아웃 원인(conntrack 5-tuple 재사용 후보) 확인, 반복 횟수 늘려 (c) 0건이 우연이 아닌지
- 79: cali 이름이 네임스페이스·파드 이름에서 만들어진다는 관찰(재생성 때 같은 이름)은 Calico 소스로 확인하거나 뺀다
- 78: externalIPs deprecated 배경(CVE-2020-8554, DenyServiceExternalIPs, KEP-5707) 원문 확인. 딥다이브 한 편으로 뺄지 결정
- 81: 백오프 간격의 "+몇 초"(1→13→27→48→88)가 어디서 오는지 kubelet 소스로 확인

## 빠지는 것
- mysql:5.7 arm64 실패(사용자 결정)
- 슬라이드 오타류(myweb2-pod NotFound, 노드 IP 중복 표) — 글감 아님
- 내 스크립트 실수로 다시 돌린 것(28 Mac 시각 표기, 21 첫 실행의 대기 없음)
