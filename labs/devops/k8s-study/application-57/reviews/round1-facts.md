# 57편 사실관계 패널 1차

- 판정: 수정 필요 1건. 주요 실험 수치·상태 전환·식별자는 원본과 일치해요.
- 검토한 HTML SHA-256: `156d6aae75fdac9b7ebe95595aa251009961ad1bb9fa9cc1015e2df0f6378545`
- 역할: 독립 사실관계 패널. HTML·실습 소스·클러스터는 수정하지 않았어요.

## F1. 초기 실패의 관찰 도구와 동시성을 원본보다 강하게 표현했어요

- 위치: HTML 34행 도입부.
- 원문: “브라우저는 연결할 수 없다고 나왔어요”, “같은 순간 파드 IP로 직접 보낸 요청”.
- 근거: `evidence/03-early-direct-readyz.json`, `03-early-direct-api-info.json`, `04-early-nodeport.json`과 `run.py`에서 초기 직접 요청과 NodePort 요청은 순차적인 `curl` 실행이에요. 초기 실패의 원자료는 NodePort curl 종료 코드 7이며, 이 시점의 브라우저 실패 기록은 없어요. 본문 마지막의 순차 관찰 제한과도 표현 수준을 맞춰야 해요.
- 수정안: “kubectl apply는 성공했는데 NodePort로 보낸 curl은 연결에 실패했어요. 파드를 조회하니 Running이었어요. 같은 초기화 구간에서 파드 IP로 직접 보낸 요청에는 HTTP 200이 돌아왔고요.”
- 정도: 실험 결과를 바꾸는 오류는 아니지만, 실행한 관측 도구와 시점을 사실대로 써야 하므로 수정해요.

## 대조를 마친 주요 주장

| 주장 | 원본 근거 | 판정 |
|---|---|---|
| Namespace·immutable ConfigMap·Deployment·NodePort Service 구성 | `application-v1.json` | 확인 |
| replicas1, maxSurge1, maxUnavailable0, minReadySeconds 미지정 | 매니페스트 Deployment spec | 확인 |
| 요청25m/32Mi·제한200m/96Mi, readiness1초·liveness5초 | 매니페스트 container spec | 확인 |
| 같은 Python digest·소스에서 APP_VERSION v1→v2 변경 | 매니페스트·`21-release-v2.json`·`06/23/25`의 이미지와 template | 확인 |
| 앱 초기 8초 readyz503, API200, 메모리 카운터와 화면2초 polling | `app.py`, `03-early-direct-*` | 확인 |
| 초기 Pod.93와 Pod→ReplicaSet→Deployment 소유 관계 | `02-running-not-ready.json`, `06-initial-state.json` | 확인 |
| 최종 Pod.85, PID250522/250552, netns4026532488, host4026531840 | `final-runtime.json` | 확인 |
| 최종 eth0 /32·MTU1480·cali01a59808126 경로 | `final-runtime.json`의 nsenter/ip 명령 출력 | 확인 |
| readiness 실패 후 Running·restartCount0 유지, 주소 남고 ready/serving=false | `13-unready-state.json` | 확인 |
| 준비 실패 중 직접 API200, NodePort curl7, 복구 후 Service 응답 | `14-unready-direct.json`, `15-unready-nodeport.json`, `17-ready-again.json` | 확인 |
| DNS10.96.0.10→ClusterIP10.98.233.106, worker2 client.126.50→worker1 app.194.93 | `06/09/10/11/13` 원본 | 확인 |
| internal-first-57가 응답과 앱 로그에 동일 | `10-internal-http.json`, `11-app-logs.json` | 확인 |
| rollout 초기 v1ready/v2notready→v2ready/v1terminating·servingtrue | `timeline.jsonl` 15:07:42.652649Z 및15:07:51.575999Z snapshot | 확인 |
| rollout129건 모두200, v1=42·v2=87 | `rollout-requests.json` 전수 재집계 | 확인 |
| replacement120건 중108HTTP200, rc7=8·28=3·56=1 | `replacement-requests.json` 전수 재집계 및 stderr | 확인 |
| replacement 중 준비된 endpoint가 없는 구간 | `timeline.jsonl` 15:08:17.834240Z~15:08:26.991177Z 전환 표본 | 확인 |
| 삭제 전후 UID 변경·관찰 IP.86→.85·같은 ReplicaSet·Service주소 유지 | `23-after-rollout.json`, `25-after-replacement.json` | 확인 |
| 최종 내부와 NodePort가 모두v2.85 응답 | `26-final-internal-http.json`, `30-final-external-http.json` | 확인 |
| 임시 client 삭제·앱1개Ready·Service endpoint1개readytrue 유지 | `28-client-cleanup.json`, `29-final-resources.json`, `final-runtime.json` | 확인 |
| preStop3초·SIGTERM handler 존재 | 매니페스트·`app.py` | 확인 |
| 순차 조회·표본 관찰이며 정밀 전파 지연/무중단 보장 아님 | `run.py`의 순차 get·요청 반복과 본문 한정 표현 | 확인 |

일반 동작 설명은 [Deployment](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/), [EndpointSlice 조건](https://kubernetes.io/docs/concepts/services-networking/endpoint-slices/#conditions), [probe](https://kubernetes.io/docs/concepts/workloads/pods/probes/) 공식 문서(v1.37 헤더)를 재확인했어요. 특히 terminating/serving/ready의 구분, terminating Pod 때문에 총개수가 일시 초과할 수 있다는 설명, readiness 실패와 재시작의 구분은 맞아요. CNI 호출 관계는 문서 설명이며 모든 호출을 추적했다는 주장을 하지 않아 관찰 범위가 적절해요.

지적 건수: **1건**. 수정 후 해당 도입부만 재확인하면 돼요.
