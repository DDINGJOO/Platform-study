# 54편: NetworkPolicy 연결 상태·방향·DNS 실험

실행일: 2026-11-14 23:34~23:35 KST. 개인 Mac의 Lima 실습 클러스터다. Kubernetes v1.37.2, Calico node v3.33.0. `iptables -V`는 `v1.8.10 (nf_tables)`이며 이 출력만으로 Calico native nftables 데이터플레인을 뜻하지 않는다.

## 범위와 재현

`python3 labs/devops/k8s-study/calico-51-56/54/run.py`로 실행한다. 스크립트의 LAB 경로는 현재 Mac의 실습 저장소 `/Users/dding/orca/workspaces/k8s/tang/lab`다. 다른 환경에서는 이를 조정한다. worker1에 busybox 클라이언트 2개, worker2에 nginx 서버 1개를 고정한다. 이미지 캐시가 필요하며 imagePullPolicy=Never다. 별도 namespace `calico-blog-54`가 이미 있으면 소유권을 추정하지 않고 중단한다.

노드 전체 규칙 변경·전역 정책·BIRD 중지·노드 재시작은 하지 않았다. 표준 networking.k8s.io/v1 NetworkPolicy만 새 namespace 안에 만들었다. 마지막에 namespace를 삭제하고 NotFound를 확인했다. 이후 노드 4대 Ready를 별도로 조회했다. `commands.json`에 결과가 있다.

## 결과

`results.json`의 17개 검사 모두 예상한 성공·차단과 일치했다. 차단을 기대한 wget은 종료 코드 1, 직접 DNS 질의는 2를 반환하므로 전체 명령이 모두 exit 0이라는 뜻은 아니다.

- 정책 없음: A/B 새 HTTP 연결, DNS UDP/TCP 모두 성공.
- server ingress 빈 허용 목록: A/B의 새 연결 timeout.
- allow-a 추가: A 성공/B timeout. allow-b 추가: B도 성공. 기존 빈 허용 목록 정책은 남아 있었다.
- A의 egress 빈 허용 목록: 서버 ingress에서 A가 허용돼도 새 연결 timeout.
- server TCP 80 egress 허용: Pod IP HTTP 성공/DNS UDP·TCP timeout.
- DNS UDP 53 허용: UDP 성공/TCP timeout.
- DNS TCP 53 허용 추가: TCP 성공/Service DNS 이름 HTTP도 성공.

기존 연결 실험은 첫 HTTP 응답을 확인한 다음 ingress deny를 apply했다. Python HTTPConnection 하나를 재사용한 12회 응답은 모두 200이고 4-tuple도 같았다. 이 12회에는 정책 전 첫 요청이 포함된다. 정책 후에 새 wget 연결 A/B의 timeout이 확인되는 동안 기존 연결의 성공이 이어졌다. 마지막 요청까지 클라이언트 내부 경과 시간은 6.612초였다.

클라이언트는 노드의 Python을 client-a 컨테이너 PID의 네트워크 네임스페이스에 nsenter해 실행했다. Pod의 네트워크를 통과하며 노드 기본 netns에서 요청한 실험과 다르다. DNS는 같은 netns에서 kube-dns Service IP 10.96.0.10에 직접 UDP/TCP 질의를 했다. 반환 기록의 rcode=0, answers=1을 확인했다. UDP 응답 잘림에 따른 자동 TCP 재시도 실험은 아니다.

## 파일과 근거

- `run.py`: 실제 실행한 실험·finally namespace 정리 스크립트.
- `commands.json`: 시각·명령·입력 JSON·종료 코드·stdout·stderr. read-pcap의 stdout은 원본 pcap의 base64다.
- `pods.json`, `service.json`, 정책별 JSON: 실제 apply한 객체.
- `keepalive.jsonl`: 같은 연결의 요청별 시간·HTTP 상태·양쪽 소켓 주소/포트.
- `keepalive.pcap`: worker1 any 인터페이스에서 두 실험 Pod IP와 TCP80으로 필터링한 약 12초 캡처. stderr 기준 138패킷 수집, 커널 드롭 0.
- `keepalive-packets.txt`: Mac tcpdump로 pcap을 해석한 출력. Linux SLL2 인터페이스 번호를 Mac에서 완전히 이름으로 해석하지 못해 일부 `?`, `anpi1`로 표시된다. 본문은 이 이름을 Linux 실제 장치명으로 사용하지 않는다. any 캡처에는 같은 패킷의 여러 인터페이스 관측이 포함될 수 있다.
- `worker1-rules.txt`, `worker2-rules.txt`: 실험 마지막 단계의 전체 iptables-save -c. `server-endpoint-chain.txt`는 서버로 가는 endpoint 체인 발췌다. deny 직후 스냅샷이나 개별 요청별 카운터가 아니다.
- `calico-v3.33.0-endpoints.go`: 설치 버전의 공식 소스 원문. appendConntrackRules와 정책보다 앞의 호출 위치를 확인했다. 소스 상단 라이선스를 보존했다.
- `render_results.py`: 원문 JSONL과 결과를 읽어 `connection-summary.txt`, `policy-matrix.txt`를 만든다. 값은 샘플에서 산출하며 주소는 화면에서 생략한다.
- 이미지 `posts/CS/DevOps/k8s-study/images/calico-54/{keepalive,matrix}.png`: 위 두 텍스트를 term-shot --from으로 렌더링했다. 실제 터미널 GUI 촬영이나 실시간 대시보드는 아니다. 화면 바닥글은 대응하는 원자료 경로다.
- `write_post.py`: 템플릿 CSS와 고정 시리즈 목록으로 담당 HTML을 생성한다. 리뷰 후 HTML 직접 수정 시 이 생성기의 본문도 동기화하거나 재실행하지 않도록 주의한다.
- `validation.json`: 담당 글만 검증한 결과. h2 6개, 용어박스 6개, SVG 3개, 이미지 2개, 오류 0.

## 한계와 시각

Mac의 commands.json 시각과 VM Python/tcpdump 시각은 서로 다른 시계다. 논리 실행 순서(첫 응답→apply→새 연결 검사)는 스크립트로 확인하지만 서로 다른 시각의 밀리초 차이를 정책 적용 지연으로 계산하지 않는다. 순차 새 연결 검사 사이의 상태를 원자적 관측처럼 쓰지 않는다. 한 번의 짧은 실행 결과이며 기존 연결의 장기 유지나 다른 CNI·Calico 모드의 동작을 보장하지 않는다. DNS TCP 질의 코드는 실측한 작은 응답을 한 recv로 받았으므로 일반 DNS 클라이언트 구현 예제로 쓰지 않는다.

## 공개 전 검사

회사 데이터·토큰·kubeconfig·Secret 본문은 수집하지 않았다. HTML의 기본 마스킹 검사에서 사설 IP `10.244.126.25`, `10.244.194.81` 두 개가 검출됐다. 둘 다 이 스크립트가 만든 개인 Lima Pod IP이며 기술 설명에 필요한 값이다. 담당 자료의 `mask-allow.txt`에 판단 근거와 해당 값만 적고 재검사해 통과했다. 공통 `.mask-allow`는 수정하지 않았다. 캡처용 두 텍스트는 허용 목록 없이도 검사 통과했다.

## 공식 출처 확인

2026-11-14에 조회했다.

- https://kubernetes.io/docs/concepts/services-networking/network-policies/ : 방향별 격리·합집합·선택자 의미·기존 연결 처리의 구현 의존성.
- https://docs.tigera.io/calico/latest/network-policy/get-started/calico-policy/calico-network-policy : 기존 연결과 새 연결의 정책 적용 설명. 실험은 이 페이지 예제의 Calico 자체 정책 대신 표준 Kubernetes 정책을 썼다.
- https://docs.tigera.io/calico/latest/reference/host-endpoints/conntrack : conntrack 개념을 보조 확인. host-endpoint 문서이므로 Pod 동작의 단독 근거로 쓰지 않았다.
- https://docs.tigera.io/calico/latest/reference/architecture/overview : Felix의 ACL 프로그래밍 역할.
- https://github.com/projectcalico/calico/blob/v3.33.0/felix/rules/endpoints.go : 실제 설치 버전의 conntrack 규칙 생성과 endpoint 체인 순서.
