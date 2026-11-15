# 57편 독립 사실관계 감사

판정: **PASS**. 본문을 쓰거나 4인 패널 퇴고를 수행하지 않은 감사자가 원본을 직접 대조했다.

- 감사한 최종 HTML SHA-256: `002da5d316cd6fe45b745f6c85377a6fbdcf576c3e7deba7ac3e23930ea6736f`
- 대상: `posts/CS/DevOps/k8s-study/57_57편 - 파드 하나를 배포하고 요청받기까지, 애플리케이션으로 확인하는 쿠버네티스.html`
- 분포: **확인 50 / 불일치 0 / 확인 불가 0 / 과장 0**.
- 여기서 확인은 표에 적은 관찰 범위·문서 설명의 범위다. 전체 트래픽·정밀 계층 지연·모든 호출의 직접 추적을 확인했다는 뜻은 아니다.
- 패널 보고서와 verify.py의 통과 결과는 감사 근거로 사용하지 않았다. 직접 JSON을 파싱하여 표본을 재집계하고, 명령 stdout/stderr·소스·명시 설정·객체 UID 관계·타임라인 원문을 읽었다.
- 최종 HTML은 텍스트SHA `da424...` 검토 도중 그림1의 disjoint path를 둘로 나눈 화살촉 렌더링 수정이 있었다. 최종SHA를 다시 읽었고, 이 수정은 주장·좌표·텍스트를 바꾸지 않았다.

| # | 검증한 주장 | 판정 | 직접 대조한 근거 |
|---|---|---|---|
| 1 | Kubernetes v1.37.2·containerd2.4.1·Calico3.33.0, Ready노드4대 | 확인 | 감사 시 read-only get nodes/get ds calico-node 조회: 네 노드 kubeletVersion v1.37.2/containerd://2.4.1/ReadyTrue, image quay.io/calico/node:v3.33.0 |
| 2 | 매니페스트는 Namespace·ConfigMap·Deployment·Service 네 종류 | 확인 | application-v1.json items.kind 직접 확인 |
| 3 | 앱은 Python 표준 라이브러리 서버와4경로를 제공 | 확인 | app.py imports, Handler.do_GET의 /, /api/info, /readyz, /healthz 분기 |
| 4 | 브라우저는2초마다실제API호출 | 확인 | app.py PAGE의 refresh(), setInterval(refresh,2000), fetch(/api/info) |
| 5 | 앱소스는 immutable ConfigMap의 /app/app.py 마운트 | 확인 | application-v1.json ConfigMap immutable=true, data.app.py가 app.py와 byte-equivalent text, Deployment volumes/volumeMounts/command |
| 6 | Python 이미지는 명시 digest로 고정 | 확인 | application-v1.json image=python@sha256:9ef1a599f863231c3d91e941389bfdc4a2d6070557243d54df1a4e57015b960e |
| 7 | 정상 상태 replicas1, 별도 client 생성 후 삭제 | 확인 | application-v1.json Deployment replicas=1;08-client-create.json;28-client-cleanup.json rc0;29-final-resources.json 앱Pod1개 |
| 8 | CPU requests25m/limits200m, memory requests32Mi/limits96Mi | 확인 | application-v1.json containers[0].resources;final-runtime.json pod.containers[0].resources |
| 9 | 초기 Pod 소유자는 ReplicaSet, 그 소유자는 Deployment | 확인 | 06-initial-state.json Pod.ownerReferences.uid→ReplicaSet.metadata.uid→Deployment.metadata.uid 직접대조 true/true |
| 10 | 초기 Pod 이름 deploy-board-7bf857644b-qz5n2 | 확인 | 02-running-not-ready.json metadata.name;06-initial-state.json Pod |
| 11 | 스케줄러 바인딩과 kubelet→CRI→runtime→CNI 역할설명 | 확인 | 공식CRI·NetworkPlugins문서의 호출구조와일치; 본문은57실습에서전호출을직접추적하지않았다고명시 |
| 12 | 최종Pod노드 worker1, IP10.244.194.85 | 확인 | final-runtime.json pod.node/pod.ip;25-after-replacement.json;감사시freshgetpods동일 |
| 13 | 샌드박스PID250522, 앱PID250552 | 확인 | final-runtime.json sandbox.pid/container.pid와명령argv의PID일치 |
| 14 | 앱·샌드박스netns4026532488, 호스트4026531840 | 확인 | final-runtime.json commands[0].stdout readlink3행 |
| 15 | 앱eth0 /32·MTU1480 | 확인 | final-runtime.json commands[1].stdout의 ip -j addr show eth0: prefixlen32/mtu1480 |
| 16 | 최종Pod호스트경로 cali01a59808126 | 확인 | final-runtime.json commands[3].stdout ip -j route get dev |
| 17 | 앱준비상태는초기8초와 /tmp/not-ready 유무로결정 | 확인 | app.py READY_AFTER,ready식;application-v1.json READY_AFTER_SECONDS=8 |
| 18 | 초기readyz503·직접api200·NodePortcurl7 | 확인 | 03-early-direct-readyz.json,03-early-direct-api-info.json,04-early-nodeport.json stdout/returncode |
| 19 | 위요청은같은초기구간의순차관측 | 확인 | 03readyz time15:07:24.958574Z,03api15:07:25.043923Z,04nodeport15:07:25.057478Z;run.py 호출순서 |
| 20 | HTTP000은서버의응답코드가아닌curl미수신표시 | 확인 | 04/15 stdout HTTP000+rc7+connectionfailure, run.py curl -w %{http_code}; 앱코드에000응답없음 |
| 21 | readiness와liveness는각 /readyz,/healthz | 확인 | application-v1.json readinessProbe/livenessProbe와공식Probes문서 |
| 22 | readiness실패만으로재시작되지않음 | 확인 | 13-unready-state.json Running/ReadyFalse/restartCount0, 초기와같은containerID;공식Probes문서와일치 |
| 23 | Endpoint주소남고ready/servingfalse,terminatingfalse | 확인 | 13-unready-state.json EndpointSlice.endpoints[0]와캡처02동일 |
| 24 | not-ready동안직접API200·NodePort실패,제거후복구 | 확인 | 14-unready-direct.json HTTP200;15-unready-nodeport.json rc7;16복구명령rc0;17-ready-again.json v1응답 |
| 25 | 준비주기1초가모든계층의1초이내동시전환보장은아님 | 확인 | manifest periodSeconds1, run.py sequentialobjects()/until()/sleep로관찰;정밀지연계산을하지않는한정이명시됨 |
| 26 | Service selector app=deploy-board,80→namedhttp8080 | 확인 | application-v1.json Service.selector,ports 및Deployment.containerPort/name |
| 27 | ClusterIP10.98.233.106,client는worker2 10.244.126.50 | 확인 | 06/13-initial/unready state Service/Pod, client.json nodeSelector k8s-worker2 |
| 28 | DNS서버10.96.0.10이ServiceClusterIP반환 | 확인 | 09-dns.json stdout nslookup출력 |
| 29 | 내부요청ID internal-first-57가응답과앱로그에서일치 | 확인 | 10-internal-http.json request_id와11-app-logs.json동일;로그peer10.244.126.50 |
| 30 | 내부요청이노드간통신을포함 | 확인 | 13-unready-state.json app k8s-worker1/client k8s-worker2;10요청응답및11로그 연결; 패킷캡처추적이라고과장하지않음 |
| 31 | Pod/노드/IP는DownwardAPI환경변수 | 확인 | application-v1.json env[].valueFrom.fieldRef,app.py os.environ.get; API직접조회코드없음 |
| 32 | Mac접속주소192.168.64.3:30057 NodePort경로 | 확인 | run.py URL/curl명령;Service.nodePort30057;30-final-external-http.json;감사시동일주소fresh200 |
| 33 | port-forward가실습요청경로가아님 | 확인 | run.py 실제호출 argv와browserPNG; script에port-forward호출없음 |
| 34 | v1→v2는같은이미지/소스의환경변수rollout | 확인 | 21-release-v2.json set env;23-after-rollout.json 두RS의이미지digest·codevolume동일, APP_VERSION만변경 |
| 35 | maxSurge1/maxUnavailable0,minReadySeconds미지정 | 확인 | application-v1.json strategy와minReadySeconds키부재;공식Deployment문서 |
| 36 | 업데이트중두앱Pod관측 | 확인 | timeline.jsonl rollout구간의두앱Pod;최대2개 직접집계 |
| 37 | v1readytrue/v2readyfalse 동시endpoint관측 | 확인 | timeline.jsonl42행: .93 ready/servingtrue, .86 ready/servingfalse |
| 38 | v2readytrue뒤v1readyfalse/servingtrue/terminatingtrue관측 | 확인 | timeline.jsonl61행;EndpointSlice공식conditions와일치 |
| 39 | rollout129개전부200,v1=42/v2=87 | 확인 | rollout-requests.json 전행독립재집계: rc0/http200=129, versions42/87, requestID불일치0 |
| 40 | 표본은35초관측, 응답후0.25초대기 | 확인 | run.py sample(...,35), loop의response후time.sleep(.25);정확4RPS라고하지않음 |
| 41 | Pod삭제후같은RS에서새UID파드생성 | 확인 | 24-delete-app-pod.json;23/25상태의ownerReferenceRS UID일치,PodUID7ad94...→7bc091... |
| 42 | 교체IP .86→.85,ServiceUID/IP/port유지 | 확인 | 23/25-after*.json 서비스UID2e000ecf...동일/ClusterIP동일/NodePort동일, 두PodIP변경; IP필수변경으로일반화하지않음 |
| 43 | replacement120중108HTTP200,12통신실패 | 확인 | replacement-requests.json 전행독립재집계 rc0/http200108, failures12 |
| 44 | 실패rc7=8,28=3,56=1과오류의뜻 | 확인 | replacement-requests.json stderr직접확인: connectionfailure8,connecttimeout3,Recv failure: Connection reset by peer1 |
| 45 | 교체중준비된endpoint가없는구간 | 확인 | timeline.jsonl116행 readyfalse/servingtrue/terminatingtrue인기존endpoint만존재, 준비된새endpoint없음 |
| 46 | SIGTERM처리와종료전3초대기설정 | 확인 | app.py signal.signal(SIGTERM,stop), stop내shutdownthread;manifest preStop time.sleep(3) |
| 47 | 카운터·실행시간은메모리기반이며재생성때초기화 | 확인 | app.py module-globalCOUNT=0/START=monotonic(), /api/info만COUNT증가, 파일·DB저장없음 |
| 48 | 최종client삭제와앱1Ready,내부·외부v2응답 | 확인 | 28삭제rc0;29최종자원;26내부/30외부v2 .85;감사fresh조회에서도앱1개Ready/client없음 |
| 49 | 실행이미지3장의값과본문일치 | 확인 | 01PNG v2/최종Pod .85;02PNGreadyz503/direct200/endpointfalse;03PNG129/108/12·rc분포·UID/IP·Service유지: 원본JSON/본문과시각적대조 |
| 50 | 정리명령은전체namespace삭제안내이며실제현재삭제아님 | 확인 | 본문은실습완료후삭제방법을안내;run.py는client만삭제;freshnamespace앱존재 |

## 공식 문서 재확인

검사한 Kubernetes 문서의 현재 선택 버전은 v1.37로 실습 minor와 일치했다. 문서의 일반 동작 설명과 이 앱에서 직접 관찰한 결과를 구분했다.

- [Probes](https://kubernetes.io/docs/concepts/workloads/pods/probes/): readiness 실패의 not-ready 처리와 liveness의 컨테이너 재시작 구분.
- [EndpointSlice conditions](https://kubernetes.io/docs/concepts/services-networking/endpoint-slices/#conditions): serving/terminating/ready 의미, terminating이 프로세스 종료 전부터 설정될 수 있음.
- [Deployments](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/): template 변경 rollout, surge/unavailable, terminating Pod의 자원 사용, minReadySeconds 기본값.
- [Pod lifecycle](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/): 교체 Pod의 새 UID와 컨테이너 재시작의 구분.
- [CRI](https://kubernetes.io/docs/concepts/containers/cri/), [Network plugins](https://kubernetes.io/docs/concepts/extend-kubernetes/compute-storage-net/network-plugins/): kubelet/런타임/CNI 호출 역할 구분.

## 새로 실행한 읽기 검증

실습 kubeconfig를 지정해 `get nodes -o json`, `-n app-capstone get pods -o json`, `-n kube-system get ds calico-node -o json`을 조회했다. 노드4개 모두 Ready, 버전은 본문과 일치했다. namespace에는 최종 앱 Pod `deploy-board-5f6f56c47c-l2r9x` 하나가 Running/Ready였으며 request-client는 없었다. `curl -sS --max-time 3 http://192.168.64.3:30057/api/info`는 v2, 최종Pod, worker1, .85 응답을 반환했다. 이 조회는 앱의 /api/info 요청 수만1증가시키며 배포·설정·파드는 변경하지 않았다.

## 가장 신뢰도가 낮은 설명과 범위

대상은57편 한 편이다. 그중 직접 관찰의 밀도가 가장 낮은 부분은 스케줄러 바인딩부터 CRI/CNI 호출까지의 설명이다. 이 실습의 개별 호출을 모두 추적한 자료가 없으며, 본문도 그 한계를 명시했다. 공식 역할 설명과 실제 API·CRI·netns·주소·호스트경로의 결과를 연결한 수준으로 처리했으므로 과장으로 판정하지 않았다.

129건의 rollout 성공은 장시간·다중 클라이언트·모든 연결에서 무실패를 증명하지 않는다. 12건의 실패에 대해서도 curl이 보고한 종류를 확인했으며 각 패킷의 커널 수준 원인을 모두 역추적한 것은 아니다. 본문은 이 수준을 넘어서는 원인 단정이나 무중단 보장을 하지 않는다. 객체조회는 순차적이므로 모든 표를 동일시점의 원자적 상태로 읽으면 안 된다.

본문·앱·실습 환경 변경, 커밋, 발행, Notion 쓰기는 수행하지 않았다. 생성한 파일은 이 감사 보고서 한 개다.
