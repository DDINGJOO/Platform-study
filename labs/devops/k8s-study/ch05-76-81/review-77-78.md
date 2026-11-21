# 77·78편 감사 기록 (2026-11-21)

대조한 것: 본문의 수치·출력 인용 ↔ out/77-*, out/78-* (LAB shared/ch05-pod 21~24 원본과 diff 동일, 77-mysql-pod.txt 만 A 절 삭제본), 소스 발췌 ↔ v1.37.2 원문, 인용문 ↔ 원 URL(kubernetes/website 소스, gh api 로 이슈·PR·KEP 원문), 편 번호 ↔ posts 파일명.

## 지적 목록

| # | 편 | 위치 | 문제 | 근거 | 조치 |
|---|---|---|---|---|---|
| 1 | 77 | 1절 CrashLoopBackOff 용어 박스 | "재시작 횟수가 2에서 3, 4로 오를 때 간격이 13초, 42초, 90초 지점" 은 시점 3개를 전이 2개에 붙여 13초가 2→3 시점처럼 읽힌다 | 77-mysql-pod.txt B 절: restarts=2 at +13s, 3 at +42s, 4 at +90s | 반영: "재시작 횟수가 2, 3, 4가 된 것을 본 시점이 13초, 42초, 90초로 점점 벌어진" |
| 2 | 77 | 3절 볼륨 설명 | "password는 ..data 디렉터리를 가리키는 심볼릭 링크" | 77-secret-visibility.txt 3절: `password -> ..data/password` | 반영: "..data/password를 가리키는 심볼릭 링크" |
| 3 | 77 | 5절 Secret base64 단락 | "etcd에는 base64도 아닌 원래 글자로 저장되고" 를 조건 없이 단정 | 22편은 저장 암호화가 꺼진 상태에서 평문을 확인했고 암호화를 켜면 암호문이 됨을 보였다 | 반영: "저장 암호화를 켜지 않은 etcd에는 … 원래 글자로 저장된다는 것과 암호화를 켜는 방법은 22편에서" |
| 4 | 77 | 5절 s-apply 해석 | "(실험 출력에서 주석 원문은 {…stringData…})" 가 77-secret-apply-annotation 의 s-apply 출력처럼 읽힌다. 그 실험은 횟수만 셌고 주석 원문을 찍지 않았다 | 원문은 77-secret-visibility.txt 4절의 db-cred-applied 주석 | 반영: "77-secret-visibility.txt 4절에서 같은 방식으로 만든 db-cred-applied의 주석 원문은" |
| 5 | 77 | 1절 "같은 이름의 .sh" | out/77-mysql-pod.sh 에 A 절(mysql:5.7)과 머리 주석 "mysql:5.7 은 arm64 노드에서 뜨나"가 그대로 있다. .txt 는 A 절을 뺐으므로 .sh 와 .txt 가 어긋나고, 본문이 가리키는 .sh 에 mysql:5.7 이야기가 남는다 | out/77-mysql-pod.sh 2·17~20행 | 보고(out/ 수정 금지). 본문에는 mysql:5.7 낱말 0. .sh 에서 A 절을 빼거나 그대로 둘지 결정 필요 |
| 6 | 78 | 1절 "이 사슬이 처음 이어지는 데는" 단락 | "파드가 Ready인 것을 확인한 뒤 Service를 만들고 … 0.4초 뒤부터 응답. Service, EndpointSlice, 노드 규칙이 차례로 생기는 틈" 은 순서가 틀렸다. 스크립트는 Pod 와 Service 를 한 번에 apply 하고 kubectl wait 로 Ready 를 본 뒤부터 쟀다. Service 는 이미 있었다 | 78-label-service-ip.sh 8~24·31~34행, txt "실패 1 번 뒤 응답, 대기 0.4초 (파드 Ready 확인 뒤부터)" | 반영: 한 번에 apply → Ready 확인 직후부터 측정으로 고치고, 틈은 "파드 Ready가 EndpointSlice ready=true로 옮겨 적히고 마스터 kube-proxy가 규칙을 고치기까지의 틈으로 보여요"(추론 표시) |
| 7 | 78 | 4절 203.0.113.10 해석, 그림 2 alt, 그림 3 SVG | (a) "80번은 여전히/그대로 타임아웃": 80번은 Service 생성 뒤 client 파드에서만 쟀고 생성 전에는 재지 않았다. (b) "규칙이 1줄씩 생겼고": 생성 전 줄 수는 재지 않았다. (c) "규칙에 네임스페이스를 가리는 조건이 없어요" 만 있고 client 파드가 Service 와 같은 blog-78 에 있었다는 점이 빠져 다른 네임스페이스 파드도 실험한 것처럼 읽힐 수 있다 | 78-externalip-anyaddr.sh/.txt 1·2절, 규칙 `-A KUBE-SERVICES -d 203.0.113.10/32 -p tcp … --dport 8001` | 반영: "같은 주소라도 80번은 Service를 만든 뒤에도 타임아웃", "1줄씩 있었고", client 가 같은 네임스페이스였고 다른 네임스페이스 영향은 규칙을 읽은 판단이라고 명시. alt "client 파드의 80번 요청은 타임아웃", SVG "80번은 타임아웃" |
| 8 | 78 | 5절 KEP-5707 단계 표와 해석, 마지막 콜아웃 | KEP-5707 의 Phase 4("After 3 releases since phase 3, remove the AllowServiceExternalIPs feature gate and DenyServiceExternalIPs admission controller")가 빠졌다. 그래서 "그만두는 쪽은 kube-proxy의 구현"이 불완전하고, 콜아웃이 DenyServiceExternalIPs 를 켜라고 권하면서 그 플러그인도 지울 계획이라는 점을 말하지 않는다 | KEP-5707 README(gh api, 139~141행), Summary 3번 "remove the "DenyServiceExternalIPs" admission controller" | 반영: 단계 표에 Phase 4 원문 추가, 해석을 "3단계까지는 kube-apiserver 코드를 지우지 말고 4단계에서 게이트와 어드미션을 지운다"로, 콜아웃에 "4단계에서 지울 계획이니 kube-proxy 구현이 꺼지기 전까지 쓰는 방어" 추가. "API 필드를 지우는 단계는 없다"는 원문과 맞아 유지 |
| 9 | 78 | 5절 CVE 단락 | "externalIPs 사용을 막는 어드미션 웹훅" | 이슈 #97076 원문 "To restrict the use of external IPs we are providing an admission webhook" | 반영: "제한하는" |
| 10 | 78 | 근거 파일 | out/78-externalips-background-excerpts.txt 의 KEP-5707 발췌에 Phase 4 가 없다(지적 8 의 원인) | KEP-5707 README 139~141행 | 보고(out/ 수정 금지). 본문은 KEP 원문 링크로 받친다 |

## 확인했고 문제없던 것
- 77: B·C 절 수치(+2s Error, +90s restarts=4, 8.4.13), env-plain/env-secret 출력, describe.go·kubelet_pods.go 발췌(skipAnnotations, `%d bytes`, secretManager.GetSecret), secret-visibility 1~6절, secret-apply-annotation 표(0/1/0, managedFields, Annotations <none>), run --env dry-run. 이미지 2장 내용·alt 일치.
- 77 pod-maker 해석: 권한은 pods create·get·list + pods/log get, secrets 없음. 본문과 그림 4가 둘 다 적고 "Secret을 읽은 것은 kubelet"은 kubelet_pods.go 발췌로 받친다. exec 줄은 관리자 권한으로만 봤다고 본문이 밝힌다.
- 인용문 원문 일치: Secret 문서("anyone who is authorized to create a Pod …", 볼륨 캐시·갱신), declarative-config("The annotation contains the contents …"), Service 문서("Kubernetes does not manage allocation of externalIPs …"), Admission 문서(DenyServiceExternalIPs, "disabled by default"), 이슈 #97076 인용 3줄·Medium·externalip-webhook·OPA Gatekeeper, PR #97395 release-note, KEP-5707 Summary·Motivation·Phase 1~3·조회 명령(Monitoring 절)·Migration Guidance.
- 날짜·번호: #97076 created 2020-12-04, #97395 merged 2021-01-28 milestone v1.21, #137293 merged 2026-03-17T23:49Z milestone v1.36, 커밋 80c6507cce author 2026-02-14, v1.36.0 포함·v1.35.0 미포함(compare), 보안 공지 Google Groups 표시 Dec 8, 2020.
- 78: label-service-ip(EndpointSlice, 0ms 거부, curl 7 port 80, Mac 응답/거부, nft·iptables 1줄), imperative-run-expose(run: myweb2, 네 노드 응답), externalip-anyaddr 3~5절(IPAddress 기록/NotFound, ServiceCIDR, IPPool blockSize 26, NodeRestriction 만, NodePort 30720 네 노드, route en0/bridge100), iptables-backend(nf_tables), proxier 발췌. IP 표의 대역·할당 주체는 lab.conf(192.168.104.0/24·192.168.64.0/24, POD 10.244.0.0/16, SERVICE 10.96.0.0/12)와 맞다.
- 편 번호: 22(Secret 평문·주의 문구), 24(LB pending), 28(ClusterIP 인터페이스 0), 32(인가), 33(기본 플러그인 25개), 34(IPAM), 42(IPAddress), 51(eth0), 56(curl 7), 59(client dry-run 뼈대, create deployment 라벨), 60(셀렉터), 61(containerPort), 75(Endpoints deprecation) 모두 해당 편 내용과 맞다.
- 형식: style 블록 템플릿 동일, lead 147·149자, 시리즈 박스 series-boxes.html 동일, h2 5/5, SVG 2/2, 용어 6/6, 콜아웃 4/4, 요약 박스로 끝, 엠대시 0, 강의·슬라이드·수업 0, mysql:5.7 0, 띄운 조사 0, 태그 짝·중복 id 이상 없음.

## 남은 위험
- mask-check(78): 10.96.220.47, 10.101.41.30, 10.96.193.82 가 [일반] 사설 IP 로 걸린다. mask-allow-pending.txt 에 이미 있으니 .mask-allow 반영 전에는 발행 점검에서 다시 걸린다.
- 보안 공지 날짜 "12월 8일"은 Google Groups 표시값(시간대 미표시)이다. 미국 시각으로는 12월 7일일 수 있다.
- 78 의 0.4초 틈이 EndpointSlice 갱신과 kube-proxy 동기화 중 어디서 생겼는지는 출력으로 가리지 못했다(본문도 그렇게 적음).

지적 10건 → 반영 8건
