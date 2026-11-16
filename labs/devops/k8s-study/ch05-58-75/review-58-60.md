# 58~60편 감사 기록 (2026-11-15)

대조한 원자료: out/58-*, 59-*, 60-*, 01-components.txt, LAB shared/ch05-pod/(part1-summary.md, lecture-notes.md, 05~17·00 번 .sh/.txt, sources/). out/ 의 ch05 복사본 18개는 원본과 cmp 로 같음(58-object-map=05, 58-kind-apiversion=06, 59-alpha-beta-served=07, 59-spec-typo=08, 59-explain-tips=09, 60-rs-labels=10, 60-rs-vs-deploy=11, 59-strace-vs-verbose=16, 59-h2c-probe-alpha=17, 59-fields-1.37=00, 59-k8s-v1.37.2-h2c-probe-excerpts=sources/).

형식 점검(세 편 공통, 수정 뒤): style 블록이 템플릿과 같음, 시리즈 박스가 series-boxes.html 과 같음, lead 131·149·150자, tags 있음, h2 6·6·5, SVG 3·3·3, 용어 박스 7·6·5, 콜아웃 3·4·3, 요약 박스로 끝, 예고 없음, 엠대시 0, "강의·슬라이드·수업·강사" 0, 띄운 조사는 코드 블록 안에만, svg·div·p·text·path 짝 맞음, 중복 id 0, mask-check 세 편 모두 깨끗함. 이미지 6개 모두 있고 alt 숫자가 화면과 맞음.

확인만 하고 문제없던 것
- 59편 strace 총수 1,788, fcntl 326·read 318·futex 269·rt_sigaction 114: out/59-strace-vs-verbose.txt 와 같음(lecture-notes 의 1794 는 쓰지 않음).
- 58편 허브의 편 번호: 1·2·19(구성 요소 그림), 10(SA 토큰과 바인딩), 16(portainer-pv, local-path, WaitForFirstConsumer), 20(CRD 23개 중 Calico 22개, 컨트롤러 매니저 정지 때 scale 7이 RS에 안 내려감), 22(Secret 평문), 24(cloud-controller-manager 0개), 28·47(kube-proxy, EndpointSlice), 30·31(Calico, IPAM), 32(인가), 39(level-triggered), 41(pods/binding), 42(컨트롤러 매니저), 59(검증, --cpu 다룸) 는 파일 본문과 맞음. 61·62·64·68·72·73 은 manifest 제목과 작성된 초안의 h2 와 맞음, 63 은 manifest·plan 의 주제(phase·conditions)와 맞음. 72·73 한 곳만 어긋나 아래 58-3 으로 고침.
- 59편 KEP-3136 URL 은 why/08 sources/_index.txt 와 같음, PR #139429·KEP-5999 는 sources/k8s-v1.37.2-h2c-probe-excerpts.txt 와 같음. 36편 Bad_Name 422 는 36편 본문과 같음.
- 60편 42편 0.1초, 50편 단독 파드, 37편 FailedScheduling 문구 참조는 각 편 본문과 같음.

| # | 편 | 위치 | 문제 | 근거 | 조치 |
|---|---|---|---|---|---|
| 58-1 | 58 | lead, 도입 2문단, 요약 2문단 | Ingress 를 만들 때 kubectl 이 "created" 를 돌려줬다고 출력처럼 인용했지만 증거에 그 줄이 없음 | 58-object-map.sh 의 `create ingress ... >/dev/null` (출력 버림), .txt 에 created 없음 | 반영: "에러 없이 만들어졌지만", "만들기가 성공한 뒤에도" 로 바꿈 |
| 58-2 | 58 | 4절 그룹별 종류 수 풀이 | "05의 HPA가 찾던" 은 원자료 파일 번호라 독자가 알 수 없음 | 05-object-map 은 LAB 파일 번호 | 반영: "2절의 HPA가 찾던" |
| 58-3 | 58 | 4절 extensions/v1beta1 풀이 | "옛 버전이 목록에서 빠지는 규칙은 72편과 73편" 인데 72편은 내부 버전·변환·저장 버전을 다룸 | 72편 h2 1~5, 73편 h2 1~4 | 반영: 72편은 "여러 버전을 동시에 서빙하는 구조", 73편은 "빠지는 규칙" 으로 나눔 |
| 58-4 | 58 | 5절 h3 | "이번 web의 파드도 ownerReferences는 ReplicaSet" 이라 했지만 web 파드의 owner kind 는 출력에 없음 | 58-who-writes.txt 는 managedFields 의 작성자(kube-controller-manager)와 칸 이름만 찍음 | 반영: obj-demo 파드 두 개(58-object-map.txt 3절)로만 말함 |
| 58-5 | 58 | 도입 3문단 | "마스터 1대, arm64 워커 3대" 는 마스터만 다른 아키텍처처럼 읽힘 | lecture-notes "노드 아키텍처가 arm64 다" | 반영: "마스터 1대, 워커 3대, 모두 arm64" |
| 58-6 | 58 | 4절 CRD 문단 | "노드마다 도는 calico-node와 calico-kube-controllers" 는 calico-kube-controllers 도 노드마다 뜨는 것처럼 읽힘 | 01-components.txt: calico-kube-controllers 파드 1개(owner ReplicaSet) | 반영: "클러스터에 하나만 뜬 calico-kube-controllers" |
| 59-1 | 59 | 그림 3 연결 화살표 2개, 그림 5 init-a→init-b 화살표 | 제어점이 한 줄에 있는 완전 직선 path | svg-sketch-guide "제어점이 2~4px 어긋난 베지어" | 반영: 제어점을 2px 어긋나게 |
| 59-2 | 59 | 2절 콜아웃 4번째 줄 | "기능 게이트" 가 용어 박스(4절)보다 먼저 설명 없이 나옴 | easy-read-guide 1 "처음 등장하는 자리에" | 반영: "기능 게이트(4절)" 로 앞으로 가리킴 |
| 59-3 | 59 | 6절 뼈대 YAML 코드 블록 | 출력의 `namespace: blog-59` 줄이 빠짐 | 59-imperative-skeleton.txt 1절 | 반박: 본문 명령도 `-n` 없이 적었고 `-n` 이 없으면 namespace 줄이 나오지 않으므로 보이는 명령과 출력이 맞음. 뜻이 바뀌지 않아 그대로 둠 |
| 60-1 | 60 | 1절 정렬 기준 문단 | (가) "더 최근에 준비된 파드가 먼저" 는 인용한 발췌(1~3번, 8번 기준)에 없음 (나) "기존 파드 셋은 이미 준비된 지 오래였어요" 는 틀림: rs-demo-wdnfr 는 bare 바로 앞 단계에서 새로 생긴 파드 (다) "3초 전에 만든 bare" 는 시점이 섞임 (라) bare 가 지워진 이유가 추론인데 추론이라고 쓰지 않음 | 60-k8s-v1.37.2-replicaset-excerpts.txt(4~7번 생략), 60-rs-labels.sh(1단계 delete → sleep 3 → 바로 bare 생성), 60-rs-labels.txt 1·2절 | 반영: 발췌 범위의 기준만 적고, 어느 단계에서 앞섰는지는 기록하지 않았다고 밝힌 뒤 "배정 전이거나 준비 전이었을 가능성" 을 추론으로 표시 |
| 60-2 | 60 | 요약 1문단 | "그래서 ... bare는 3초 만에 지워졌고" 가 정렬 기준을 원인으로 단정 | 60-1 과 같음 | 반영: "그래서" 를 빼고 "3초 안에 지워졌고" |
| 60-3 | 60 | 4절 마지막 문단 | 옛 RS 파드 td62q 를 "지워지는 중이었고" 로 단정 | 60-rs-vs-deploy(=11) 실행은 deletionTimestamp 를 찍지 않음, lecture-notes 11 행 "종료 중으로 추정, 미확인", 확인은 19 번 실행(62편) | 반영: "지워지는 중이었을 거예요. 이 실행에서는 deletionTimestamp를 찍지 않아 단정하지 않는다" 로 바꾸고 확인은 62편으로 넘김, 뒤 문장의 "그래서" 도 정리 |
| 60-4 | 60 | 5절 소유자 목록 풀이 | "이름에 해시가 두 번 붙은" 은 틀림: 둘째 꼬리는 임의 문자열 | 01-components.txt coredns-559f6c778d-4ml68 | 반영: "pod-template-hash와 임의 꼬리가 차례로 붙은" + 예시 |
| 60-5 | 60 | 그림 2 app=debug 화살표, 그림 4 단계 화살표 2개 | 완전 직선 path | 59-1 과 같음 | 반영 |
| 60-6 | 60 | 2절 콜아웃 4번째 줄 | pod-template-hash 가 용어 박스(4절)보다 먼저 설명 없이 나옴 | easy-read-guide 1 | 반영: "템플릿 해시 라벨 pod-template-hash(4절)" |
| 60-7 | 60 | 2절 콜아웃 4번째 줄 | "pod-template-hash 만 바꾸면 RS 에서는 떨어져도 Service 에는 계속 맞는다" 는 실험하지 않은 내용 | 58-object-map.txt: RS 셀렉터 {app, pod-template-hash}, Service 셀렉터 {app} | 반박: 두 셀렉터의 정의에서 바로 나오는 결론이고 1·2절 실험(셀렉터 밖으로 나가면 놓아줌, Service 는 라벨만 봄)과 같은 규칙이라 그대로 둠. 남은 위험으로 보고 |
| 공통-1 | 58·59·60 | 그림 alt (58/02, 59/02, 60/01) | alt 와 화면의 명령 줄이 LAB 파일 이름(05-object-map.sh, 17-h2c-probe-alpha.sh, 10-rs-labels.sh)이라 본문이 가리키는 out/58·59·60 이름과 다름 | 이미지 파일 직접 확인 | 반박: alt 는 화면 내용과 정확히 같고 화면 아래에 out/ 경로가 찍혀 있음. 바꾸려면 재촬영이 필요해 그대로 둠 |

보고할 것(이 감사에서 고치지 않음)
- out/ 파일 mask-check [일반] 경고: 58-object-map.txt 의 1000243654(resourceVersion), 10.110.168.250(ClusterIP), 10.244.100.241(파드 IP), 59-strace-vs-verbose.txt 의 1000249171(resourceVersion). 모두 실습 클러스터 값이라 .mask-allow 후보.

지적 17건 → 반영 14건
