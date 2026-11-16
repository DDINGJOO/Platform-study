# 72~75편 감사 기록 (2026-11-15)

대조한 원자료: out/72-*, 73-*, 74-*, 75-*, 58-kind-apiversion.txt, 59-alpha-beta-served.txt, LAB shared/why/08-api-versions-deprecation/(notes.md, sources/ 전부와 _index.txt), 교차 참조한 22·33·36·38편 본문과 out/33-admission.txt. out/ 복사본 5쌍(72-discovery=01, 72-hpa=02, 74-etcd=03, 74-crd=04, 75-endpoints=05)의 .sh·.txt 는 LAB 원본과 cmp 로 같음.

형식 점검(네 편, 수정 뒤): style 블록이 템플릿과 같음, 시리즈 박스가 series-boxes.html 과 같음, lead 141·145·145·128자, tags 있음, h2 5·4·5·5, SVG 2·2·2·2, 용어 박스 7·5·5·4, 콜아웃 4·3·2·3, 요약 박스로 끝, 예고 없음, 엠대시 0, "강의·슬라이드·수업·강사" 0, 띄운 조사는 코드 블록 안에만, svg·div·p·text·path·g 짝 맞음, 중복 id 0, rect·line·L 직선 0(75편 수정 뒤), mask-check 네 편 모두 깨끗함. 이미지 7개 모두 있고 alt 숫자가 화면과 맞음. 본문 링크는 감사 문서(36편에서 인용) 하나를 빼고 모두 sources 안의 URL 과 글자까지 같음.

확인만 하고 문제없던 것
- Rule #4a 숫자·날짜(73편 표와 본문): 2017-01 #1856(생성 2016-12-05, 머지 2017-01-03) GA 1년/2릴리스·Beta 3개월/1릴리스·Alpha 0, 2017-09 #5338 Beta 6개월/2릴리스와 Rule #4b, 2018-05 #8666(머지 05-29) 12개월/3릴리스·9개월/3릴리스와 "maximum supported version skew of 2 releases", #8825 이틀 뒤(05-31), 2022-01 #31389(liggitt, 01-18 생성) "must not be removed within a major version", 2022-09 #36663 지금 문구. 첫 판 Rule #4 인용 블록과 "approximately 3 months (4 per year)", 지금 판 "approximately 4 months (3 per year)" 모두 원문과 같음. #8666 본문 인용, bgrant0607 두 인용, lavalamp 의 "latter half / odd-numbered" 제안, Hockin·sftim·liggitt·smarterclayton(#31389) 인용 모두 website-prs-deprecation-policy-history.md 와 같음.
- KEP: 1635 deads2k 2019-10-01 작성, stable 1.19, Motivation 인용·"nine months and removed in 18 months"·1.16→1.19→1.22 예시·영향 목록 / 3136 2022-01-13 작성, 1.24, Motivation·"practical"·Risk 인용, `--runtime-config=group/version/resource=true` / 1333 인용과 kube-scheduler 1.16 사례 / 1693 liggitt 2020-04-16, beta 1.19·GA 1.22, Motivation·Goal 인용, 코드 299·warn-agent `-`, kube-apiserver·kube-controller-manager 경고 무시 / 2342 "misusing" / 2330 2018 / 4192 alpha 1.30·beta 1.35·stable 1.37 / 2339 Summary. 모두 kep.yaml·README 와 같음.
- 큰 제거 버전: 1.16(apps/v1beta1·v1beta2, extensions/v1beta1 Deployment·DaemonSet·ReplicaSet·NetworkPolicy·PSP, `--runtime-config` 임시 재활성, 1.18 #85903), 1.22(Ingress 두 그룹, CRD·webhook·APIService·CSR·Lease·RBAC v1beta1), 1.25(PSP 제거, CronJob·v2beta1·PDB·events·EndpointSlice·RuntimeClass), 1.26(v2beta2, flowcontrol v1beta1), 이행 가이드 마지막 1.32 flowcontrol v1beta3. CHANGELOG 발췌·이행 가이드와 같음. PR #70672 2018-11-05→2019-06-22 약 7.5개월.
- HPA(72편): 같은 uid 7b4c5407…·resourceVersion 1000251400 = mod_revision, etcd apiVersion=autoscaling/v2, 778→1184바이트, annotation 3개(behavior·conditions·metrics, metrics 에는 memory 70 만), v2 annotation 0, GET→PUT 보존(순서 cpu,memory→memory,cpu), annotation 없는 v1 PUT 은 cpu=50 만·behavior 빈 값, `hpa.v1.autoscaling`→/apis/autoscaling/v2, 전체 이름→v1. 해시 qwQve8ut294=·oQlkt7f5j/A=·r2yiGXH7wu8=·x51sC10/5OA=, install.go·annotations.go(6개 키)·conversion.go·storageversionhash.go 발췌, 1.14 CHANGELOG 인용, api_changes.md "star" 인용, Rule #2 문장(2017 첫 판과 지금 판 모두 있음), api-group.md·protobuf.md 인용 모두 원자료와 같음. HPA 저장 버전이 언제 v2 로 바뀌었는지(notes 9절)는 본문에 없음.
- CRD 23개(74편): 키 893(protobuf 821, JSON 72), apiextensions v1beta1 23 + certificates v1beta1 1, 저장 apiVersion 14종, events 404 모두 v1 Event, Calico 25, apiextensions.go 주석 인용, #82292(DirectXMan12 2019-09-03, 700k·1M, 지금도 open), jfWCUB31mvA=. "more compact" 이유는 확인 못 했다고 적음(notes 9절과 같음). 예외 목록과 n-1 자동 선택이 겹치는지 확인 못 했다고 적음(같음).
- SVM 실험(74편): 21:13:59 생성 → 2초 간격 확인 → 21:14:20 Succeeded, "약 20초"와 "객체 두 개짜리라 일반화 못 함" 단서, w1 mod_revision 1000252150→1000252517, w2 1000252156 그대로(코드로 확인 안 했다고 적음, notes 9절과 같음), storedVersions ["v1","v2"]→["v2"], v1 삭제 거부 메시지, SVM 객체는 v1beta1 저장. #52185 본문·Hockin·smarterclayton·lavalamp·timothysc·liggitt(2018-01-17)·enj(2024-04)·michaelasp(2026-08-10) 인용과 날짜 모두 issue-52185 와 같음. StorageVersion API 와 HA 관계는 확인 못 했다고 적음(같음).
- Endpoints(73·75편): "v1 Endpoints is deprecated in v1.33+; use discovery.k8s.io/v1 EndpointSlice", 1.33 CHANGELOG 인용 "The API will not be removed", gauge 두 줄 모두 removed_release="", GET 470·PUT 34·WATCH 11, --warnings-as-errors 종료 코드 1, process_start 19:58:25, --audit-policy-file 0. 호출자는 확인 못 했다고 적음(kube-controller-manager 추정은 쓰지 않음).
- notes 9절 항목은 네 편 어디에서도 단정하지 않음(Ingress 1.20→1.22 경위는 73편 콜아웃에서 "확인하지 못했어요", KEP-4330 단계·"beta 건너뛰기" 규범은 언급 없음). 아래 75-1 의 gauge 지속 표현만 고침.
- 73편 out 파일(73-old-manifests-dry-run-scan.txt): 첫 줄 "# 75 …"와 네임스페이스 blog-75 는 원자료라 그대로 둠. 본문의 매니페스트 6개·통과 3(경고 1)·막힘 3·종료 코드 1·discovery NotFound 3개 인용은 파일 1·2절과 같고, 75편이 인용한 3절(dry-run 경고·--warnings-as-errors)·4절(gauge·process_start·audit 0)도 파일과 같음.
- 교차 참조: 22편(k8s\x00 뒤 apiVersion·kind, resourceVersion=mod_revision), 38편(리비전·컴팩션), 59편(strict decoding), 21편(컨트롤 플레인 3대), 36편(감사 문서 "If the flag is omitted, no events are logged", hostPath) 모두 해당 편 본문과 맞음.

| # | 편 | 위치 | 문제 | 근거 | 조치 |
|---|---|---|---|---|---|
| 72-1 | 72 | 5절 마지막 문단 | extensions/v1beta1 Deployment 를 "1.37 서버에 보내면 … 거절돼요"라고 씀. 실제로는 kubectl 이 discovery 에서 매핑을 못 찾아 요청을 보내기 전에 멈춘 것이고 73편 1절도 그렇게 설명함 | 58-kind-apiversion.txt "error: resource mapping not found … no matches for kind"(Error from server 없음), 73편 1절 | 반영: "1.37 서버를 상대로 … kubectl apply 하면 … 메시지로 막혀요" |
| 72-2 | 72 | 1절 두 번째 코드 블록 | `$ kubectl get --raw /apis/autoscaling` 아래에 JSON 이 아니라 스크립트가 뽑은 두 필드를 그대로 출력처럼 붙임 | 72-discovery-storage-version-hash.txt 2절(파이썬으로 가공한 줄) | 반영: 명령 줄 끝에 "(JSON에서 두 필드만)" 표시 |
| 73-1 | 73 | 2절 #8825 문단 끝 | "1장의 '서빙 중단'이라는 표현이 여기서 왔어요"는 근거 없는 어원 주장. 같은 표현은 1.16 CHANGELOG·이행 가이드의 "no longer served"에도 있음 | website-prs history #8825(본문은 #8666 리뷰 후속), #8666 liggitt 리뷰, CHANGELOG-1.16 | 반영: "서빙 중단과 제거의 구분을 정책 문서에 적은 것이 이 PR이에요" |
| 73-2 | 73 | 1절 Notable changes 코드 블록 앞 | "Notable changes 일부예요"인데 Deployment 항목 5개를 모두 실음 | web-deprecation-guide.md v1.16 Deployment | 반영: "Notable changes예요" |
| 73-3 | 73 | 3절 KEP-1635 문단 | "beta에 시계를 달았어요"는 비유 | writer-brief "비유 금지" | 반영: "beta에 시한을 정했어요" |
| 73-4 | 73 | 3절 prerelease-lifecycle 문단 | "introduced·deprecated 태그만 있고"인데 types.go 에는 replacement 태그도 있음 | k8s-v1.37.2-versioning-code-excerpts.txt 8절 | 반영: "태그는 있고 removed 태그는 없어요" |
| 73-5 | 73 | 3절 제거 표 앞 문장 | KEP-1635(1.19)를 설명한 뒤 "그 뒤 몇 릴리스에 걸쳐"라 하고 1.16 부터 표를 시작해 순서가 어긋남 | 표 1행 1.16, KEP-1635 stable 1.19 | 반영: "1.16부터 몇 릴리스에 걸쳐" |
| 73-6 | 73 | 도입 원자료 문단 | 본문 설명은 파일과 맞지만, 파일 첫 줄 제목이 "# 75"이고 3·4절이 Endpoints 메트릭이라 독자가 다른 파일로 오해할 수 있음 | 73-old-manifests-dry-run-scan.txt 첫 줄·3·4절, 75편 인용 | 반영: "파일 첫 줄 제목도 75로 적혀 있어요. 이 글은 1·2절을, 3·4절은 75편에서 인용해요" 추가(원자료는 그대로) |
| 73-7 | 73 | 3절 --runtime-config 용어 박스 | "KEP-3136은 그룹/버전/리소스=true 형식으로 넓혔어요"인데 1.16 CHANGELOG 에 이미 `extensions/v1beta1/deployments=true` 형식이 있어 어긋나 보임 | kep-3136 README 184줄 "The --runtime-config flag will be extended to allow group/version/resource=true", CHANGELOG-1.16 | 반박: KEP 원문이 그렇게 적고 있어 그대로 둠. 1.16 의 형식은 extensions 그룹 리소스에 쓰인 예라 일반 확장 시점은 남은 위험으로 보고 |
| 74-1 | 74 | 2절 #5338 인용 뒤 | bgrant0607 의 "For the storage version, it definitely is."를 Hockin 질문에 대한 답처럼 씀. 실제로는 lavalamp 의 "rule 4b 가 꼭 필요한지 고민 중"에 대한 답 | website-prs history #5338: lavalamp(2017-09-07) "…whether this rule 4b is actually necessary." → bgrant0607(2017-09-08) | 반영: "같은 리뷰에서 lavalamp가 Rule #4b가 꼭 필요한지 아직 고민 중이라고 하자 bgrant0607은 …" |
| 74-2 | 74 | 5절 h2 | "남은 숙제는"은 비유 | writer-brief "비유 금지" | 반영: "남은 문제는" |
| 75-1 | 75 | 3절 h2, 3절 강조 문장, 요약 2문단 | gauge 가 "프로세스가 살아 있는 동안 1로 남는다"를 제목에서 단정. 관측은 CRD 삭제(21:14) 뒤 21:15·21:43 두 번뿐이고 notes 9절은 "재시작 전까지 남는다는 것은 관측이고 코드로 확인하지 않았다" | 75-deprecated-ga-endpoints.txt 3절, 73-old-manifests-dry-run-scan.txt 4절, notes.md 9절 | 반영: 제목 "지운 리소스의 줄도 1로 남아 있었다", 본문 "30분 가까이 지나도 … 남아 있었어요. 재시작할 때까지 계속 남는지는 관측 범위를 넘고 코드로도 확인하지 않았어요", 요약 "30분 가까이 1로 남아 있었고" |
| 75-2 | 75 | 그림 3 21:15 눈금 라벨 | "첫 측정"이라 했지만 widgets 줄은 21:13:55 에 이미 측정됨(endpoints 줄도 "21:13 측정부터 1"이라 그림 안에서도 어긋남) | 74-crd-storage-migration-and-deprecation.txt 0·5절 | 반영: "삭제 뒤 측정" |
| 75-3 | 75 | 2절 클라이언트 경고 문단 끝 | "admission webhook이 돌려주는 warnings … 33편에서 본 어드미션 단계의 경고가 이 경로"라 해서 33편 경고가 웹훅에서 온 것처럼 읽힘. 33편 클러스터에는 웹훅이 0개였고 경고는 내장 PodSecurity 플러그인 것 | 33편 본문("웹훅 설정과 정책 객체는 네 종류 모두 0개"), out/33-admission.txt "Warning: existing pods in namespace …", kep-1693 Goals(in-process admission·webhook 둘 다) | 반영: "KEP-1693은 내장 어드미션과 admission webhook도 같은 헤더로 … 33편의 Warning: existing pods … 줄도 내장 어드미션 플러그인이 보낸 경고예요" |
| 75-4 | 75 | 2절 curl 결과 풀이 | kubectl 경고가 "stderr에 찍혔어요"를 관측처럼 씀. 스크립트는 2>&1 로 합쳐 찍어 stdout·stderr 를 구분하지 않음 | 74-crd-storage-migration-and-deprecation.sh 96줄 `2>&1`, CHANGELOG-1.19 "kubectl outputs warnings to stderr" | 반영: "Warning:으로 시작하는 줄로 찍혔어요. 1.19 CHANGELOG에 따르면 kubectl은 이 줄을 stderr로 내보내요" |
| 75-5 | 75 | 그림 3 눈금 5개, X 표시 | `L` 직선 path 6개 | svg-sketch-guide "직선을 긋고 싶으면 제어점이 2~4px 어긋난 베지어" | 반영: 모두 어긋난 베지어로 |

편별: 72편 2건(반영 2), 73편 7건(반영 6, 반박 1), 74편 2건(반영 2), 75편 5건(반영 5).

남은 위험
- 73-7: `--runtime-config` 리소스 단위 형식이 KEP-3136 에서 처음 생긴 것처럼 읽힐 수 있음. KEP 원문 표현을 따른 것이라 두었지만 1.16 에 extensions 리소스용 같은 형식이 있었음.
- 74편 2절 "1.36 이하에 들어온 버전 중에서 고르면 v1beta1이 남아요"는 v1 의 introduced 를 1.37 로 본 계산. v1 타입의 prerelease-lifecycle 값은 발췌에 없음(관측 결과 v1beta1 저장과는 맞음).
- 75편 "프로세스 재시작 전의 기록"(표)은 gauge 가 프로세스 메모리 값이라는 블로그 설명("set to 1 in the kube-apiserver process")에 기댐. 재시작 뒤 초기화는 관측하지 않음.
- 이미지 72/02·75/01 에 실습 IP(192.168.64.2, 192.168.104.1)가 보임. 글 mask-check 는 깨끗했고 이미지 자체는 검사 대상이 아님.

지적 16건 → 반영 15건
