# 79·81편 감사 기록 (2026-11-21)

대조한 것: 본문의 수치·출력 인용 ↔ out/79-*, out/81-*, out/25-kubelet-stop.txt (LAB shared/ch05-pod 25·25b·26·27·29·30·31 원본과 .sh/.txt 모두 diff 동일), 소스 발췌 ↔ 원문(Calico v3.33.0·Kubernetes v1.37.2 태그 파일을 raw.githubusercontent 로 받아 발췌 줄 번호별로 비교: 79 발췌 전 줄, 81 발췌 385줄 불일치 0), 이슈·PR·KEP ↔ gh api 원문, 문서 ↔ kubernetes/website release-1.16·1.17·main, 편 번호 ↔ 해당 편 본문, 이미지 4장 ↔ out 원자료와 alt.

## 지적 목록

| # | 편 | 위치 | 문제 | 근거 | 조치 |
|---|---|---|---|---|---|
| 1 | 79 | 5절 콜아웃 "다른 노드로만 안 될 때" 셋째 줄 | "줄이 없거나 via가 다르면 패킷은 기본 경로로 빠져요"는 via가 다른 경우까지 기본 경로로 간다고 쓴다. via가 다르면 그 노드로 보내진다. 기본 경로로 빠진 것은 30편에서 경로를 지운 경우(via 192.168.64.1 dev lima1)만 확인됐다 | 30편 4절 "지운 직후 ip route get … via 192.168.64.1 dev lima1로 바뀌었어요" | 반영: "줄이 없으면 패킷은 기본 경로로 빠지고 via가 다르면 엉뚱한 노드로 가요" |
| 2 | 79 | 6절 "이 함수를 부르는 곳은 두 군데예요" | v3.33.0 에서 VethNameForWorkload 는 felix/k8sfv/pod.go:119, felix/fv/workload/workload.go:213·215 에서도 불린다(테스트 하네스). 본문이 말한 두 곳은 테스트를 뺀 동작 경로다 | v3.33.0 태그 파일 grep, gh code search | 반영: "테스트 코드를 빼면 이 함수를 부르는 곳은 두 군데예요" |
| 3 | 79 | 6절 79-cali-name-hash 소개 | "담당 네임스페이스에서"라고 했지만 스크립트는 blog-79 와 81편 담당인 blog-81 을 만들고 지웠다. 노드(worker2 고정)도 본문에 없다 | out/79-cali-name-hash.sh 3·21·31행 | 반영: "worker2에 파드를 고정하고 blog-79, blog-81 네임스페이스에서". 절차 문제는 아래 남은 위험에 보고 |
| 4 | 79 | 6절 마지막 콜아웃(진단 순서) 범위 표시 | "VXLAN 모드나 eBPF 데이터플레인은 장치와 경로가 달라서 이번에 실험하지 않았어요"는 실험하지 않은 구성의 차이를 단정하고 그 차이를 실험하지 않은 이유처럼 읽힌다 | 원자료는 IPIP Always·iptables 구성만 | 반영: "장치와 경로가 다를 수 있는데 이번에 실험하지 않았어요" |
| 5 | 79 | 3절 "장치 이름은 같았지만 카운터는 처음부터 다시 셌어요" | 첫 pp1·pp2 의 cali 카운터는 재지 않았으니 3절 자료만으로는 리셋을 못 본다 | 6절 실험(삭제 뒤 `Device … does not exist`, ifindex 82→83)과 k8s.go 437행 주석 "the veth needs (re)creating" 이 같은 메커니즘을 받친다. 본문도 "6절에서 이유를 봐요"로 근거를 연결한다 | 반박(유지) |
| 6 | 79 | 6절 "합쳐서 15자이고 리눅스 인터페이스 이름에 쓸 수 있는 최대 길이와 같아요" | out/ 원자료에 없는 수치 | worker1 /usr/include/linux/if.h:31 `#define IFNAMSIZ 16`(NUL 포함이라 보이는 글자는 15). cali 4자 + 11자 = 15 | 반박(유지, 노드에서 읽기만 해 확인) |
| 7 | 81 | 도입 출력 꼬리 "(Error 줄은 생략)" | 원자료의 `+  0s ContainerCreating` 줄도 빠졌는데 Error 줄만 뺐다고 적었다 | out/81-crashloop-restart.txt 3행 | 반영: "(ContainerCreating 줄과 Error 줄은 생략)" |
| 8 | 81 | 2절 h3 "최댓값 300초는…" 첫 단락 | "KEP-5593의 KubeletCrashLoopBackOffMax는 1.32에 알파로 들어와"는 시기가 어긋난다. KEP-5593 은 2025-09-30 에 KEP-4603 에서 갈라져 나왔고 1.32 알파 당시 이 게이트는 KEP-4603 소속이었다 | enhancements#5593 본문 "takes the (already implemented and in alpha) KEP 4603 and splits it into two KEPs", created_at 2025-09-30. v1.37.2 kube_features.go 는 kep 5593 표기, 1.32 Alpha·1.35 Beta(기본 켜짐) | 반영: "1.32에 KEP-4603의 일부로 알파가 됐고, 2025년 9월 그 KEP에서 갈라져 나온 KEP-5593으로 1.35에 베타", 둘째 게이트는 "KEP-4603에 남은" |
| 9 | 81 | 3절 h2 제목 | "간격에 더해진 1~17초는 … 지터였다"는 단정이다. 본문은 "각 값을 감지 지연, 1초 주기, 지터로 정확히 나누지는 못했어요 … 코드가 허용하는 범위 안이었다는 데까지"라고 한정한다 | 본문 3절 마지막 단락 | 반영: "…지터의 범위 안이었다" |
| 10 | 81 | 3절 pod_workers.go 코드 블록 마지막 줄 | 원문에 없는 주석 `// factor = 0.5`가 코드처럼 붙어 있다 | pod_workers.go v1.37.2 1547행 원문(주석 없음), 0.5 는 330행 상수 | 반영: 주석을 지우고 산문에 "(같은 파일 330행 workerBackOffPeriodJitterFactor = 0.5)" |
| 11 | 81 | 3절 h3 "STATUS 칸에…" 해석 단락 | "이 순서는 … 설명돼요"로 시작해 코드 순서에서 추론했다는 표시가 약하다(끝의 "이유로 보여요" 하나뿐) | 관찰은 watch 기록, 원인은 kubelet.go 2108·2267~2268행과 kubelet_pods.go 2770~2778행을 읽은 추론. kubelet 로그는 보지 않았다 | 반영: "설명할 수 있어요. 아래 설명은 코드 순서에서 추론한 것이고 kubelet 로그로 동기화 시점을 확인하지는 않았어요" |
| 12 | 81 | 3절 같은 단락 62편 비교 | "62편의 파드에서는 waiting(CrashLoopBackOff)이 오래 관찰된 적이 있어요"의 "오래"가 모호하다 | 62편 출력: +8.5s terminated(Error) → +14.4s waiting(CrashLoopBackOff) → +18.6s running. 둘째 백오프(+22.5s→+45.2s)에는 안 보였다 | 반영: "+14.4초 기록부터 +18.6초에 running이 될 때까지 4초가량" |
| 13 | 81 | 4절 Unknown 단락 25편 인용 | "52초 뒤 노드는 Ready=Unknown이 됐지만"은 전이 시점처럼 읽힌다. 원자료는 10초 간격 표본이라 +41s True, +52s Unknown 이다 | out/25-kubelet-stop.txt 10·11행 | 반영: "kubelet을 멈추고 10초마다 확인했을 때 52초 지점에서 노드는 Ready=Unknown이었지만". 파드 "Running/ready=False"는 원자료와 일치 |
| 14 | 81 | 요약 박스 둘째 단락 | "지터를 붙여서, 두 실행에서 1~17초가 더해졌어요. 같은 이유로 STATUS 칸은…"은 본문이 범위 일치·추론으로 한정한 두 인과를 단정한다 | 지적 9·11 | 반영: "지터를 붙이고, 두 실행에서 더해진 1~17초는 그 범위 안이었어요. … 코드 순서로 보면 이것도 이 예약 방식 때문으로 보여요" |

## 확인했고 문제없던 것
- 79 수치: 브리지 0줄, tunl0 `link/ipip`·mtu 1480·`remote any local any`, 파드별 /32(`10.244.100.228 dev cali6d8ce9c91fa`, `.193 dev cali7986f7b7af3`), 파드 eth0 /32 와 `default via 169.254.1.1`, 25b 카운터(tunl0 1528/599 그대로, cali rx 2→27 tx 2→33, rx 3→28 tx 1→33, 20/20 0%), 27(worker1 `via 192.168.104.5 dev tunl0`, worker3 `dev calie3e75f17935`, 캡처 첫 줄, tunl0 rx 1528→1531), 26(blockaffinities 4줄, 네 노드 대칭, proto 80, rt_protos 12 bird, bird·bird6 프로세스), 79-cali-name-hash 표 4행·ifindex 82→83. 25b(12:15:23)와 27(12:16:31) 사이 "1분 남짓"도 맞다.
- 79 해시: `printf 'ns.pod' | shasum -a 1` 로 ch05.pp1·pp2·dst3, blog-79.web·blog-81.web·blog-79.web2 여섯 값을 Mac 에서 다시 계산해 모두 일치. worker1 에도 /usr/bin/shasum 이 있어 "노드에서 바로 계산"도 성립.
- 79 소스: 발췌 workload_endpoint_default.go 75~93·153~156·250~254행, k8s.go 437~441·452~456행이 v3.33.0 원문과 글자 단위로 같다. 본문 코드 블록은 else 분기를 `...`로 줄인 것 외 원문 그대로. 155행 위 주석 인용(153~154행) 일치. 링크 URL 두 개 존재.
- 79 편 번호: 30(proto 80, BIRD 멈춤 무관, 경로 삭제 뒤 바로 실패·약 32~37초 복구, `ip route show proto 80` 3줄+blackhole 1줄), 31(BlockAffinity·podCIDR), 51(veth·proxy_arp·169.254.1.1), 52(같은 노드 TTL 64→63, IPIP 80=20+60), 53(1500−20), 54(NetworkPolicy), 56(listen, blackhole 과 최장 접두사) 모두 해당 편 내용과 맞다.
- 81 수치: 29 간격 1·13·27·48·88초와 UID 7ed33dc2·IP 10.244.100.219 불변, watch 1·11·28·57초, +8.2→+18.3→+18.4 등 STATUS 전이, BackOff count=4 first 10:31:16Z, C절 onfailure Running/restarts 4·never Failed/0, D절 lastProbeTime=null, 30 conditions 5개와 Unschedulable 메시지, 31 `patched (no change)`·phase Running·12초 뒤 6개 type, configz `maxContainerRestartPeriod: 5m0s`, 게이트 메트릭 4줄.
- 81 "관찰값 7개가 모두 범위 안" 계산: 남은 시간 r = 백오프 − 감지(≤1초), 추가 시간 ≤ 0.5r + 1초 틱 + 시작 시간. 10초 → +3·+1 (≤ 약 5), 20초 → +7·+8 (≤ 약 10), 40초 → +8·+17 (≤ 약 20). 80초는 r=79 → 60초로 잘려 Jitter(60,0.5) 로 61~91초에 재동기화, 80초 전이면 다시 Jitter(80−t,0.5) 로 최대 약 89.5초 → 추가 최대 약 11~12초, +8 포함. 본문 계산 맞음.
- 81 소스: 발췌 385줄 전부 v1.37.2 원문과 일치. 발췌 밖 주장도 원문 확인: NewBackOff 는 NewBackOffWithJitter(…, 0.0) 이라 Backoff.jitter 가 0(무작위 없음), Next 가 lastUpdate=Now 를 적어 600초 리셋 해석이 맞음, podWorkers.resyncInterval = kubeCfg.SyncFrequency(kubelet.go 638행), getPhase 가 LastTerminationState 있는 Waiting 을 stopped 로 셈, status_manager.go 1356~1357행 "kubelet should be the source of truth of pod status", LastProbeTime 을 채우는 곳은 status_manager.go 371·1555행(크기 변경)뿐이고 generate.go 0, PodConditionSharedByKubelet = DisruptionTarget, validation.go 254행 1s~300s 범위 검사, kube_features.go PodReadyToStartContainersCondition 1.37 GA(1991행)·EventedPLEG 1.26 알파만·ContainerRestartRules 1.35 베타.
- 81 이력: PR #133066 "Propagate backoff duration for crashloop backoff" merged 2025-10-29, milestone v1.35, merge commit 이 v1.35.0 의 조상(compare behind)이고 v1.34.0 에는 없음. 이슈 #123602 본문 3번 "(minor) the error retry period is 10s, which adds up to 10s to the backoff time" 원문 일치. 1.16 pod-lifecycle 에 `Unschedulable`·"have started successfully", 1.17 에서 Unschedulable 삭제, main 은 "have completed successfully" 확인.
- 81 편 번호: 25(kubelet 정지), 43(pause·netns), 50(축출), 60(컨트롤러가 새 파드), 62(CrashLoopBackOff 관찰), 63(STATUS 칸은 printers.go, 지우는 중 SIGKILL 된 Always 파드가 Failed, PodReadyToStartContainers 시점, 조건 시각은 쓴 쪽 시계), 71(컨테이너별 재시작 규칙) 모두 맞다.
- 이미지: 79/01·02, 81/01·02 파일 있음, 화면 내용이 out 원자료와 같고 alt 의 숫자도 일치. 81 그림 1 막대 길이(1초=4px)가 10+3, 20+7, 40+8, 80+8 과 맞다.
- 형식(두 편 모두): style 블록 템플릿 동일, lead 132·150자, tags 주석, 시리즈 박스 series-boxes.html 동일, h2 6/6, SVG 3/3(rect·line 없음), 용어 박스 7/7, 콜아웃 4/4, 요약 박스로 끝, 예고 없음, 엠대시 0, 강의·슬라이드·수업 0, 띄운 조사는 코드 블록 안에만, 태그 짝·중복 id 이상 없음, mask-check 두 편과 out/79-*·81-* 모두 깨끗함(현재 .mask-allow 기준).

## 남은 위험
- 79-cali-name-hash.sh 가 81편 담당 네임스페이스 blog-81 을 만들고 지웠다(19:18~19:20). 81편 실험 81-crashloop-watch 는 19:31 에 돌아 겹치지 않았지만 "담당 네임스페이스만" 규칙 위반이다. out/ 은 고치지 않았다.
- KEP-5593 분리 시점(2025-09)과 PR #133066·이슈 #123602 원문은 gh api 로만 확인했고 out/ 이나 LAB sources 에 저장된 원문이 없다. 81 발췌 파일 머리말에 PR·이슈 번호만 있다.
- 81 의 "STATUS 가 백오프 내내 Error, CrashLoopBackOff 는 0.1초" 원인은 코드 순서 추론이다(본문에 표시). 62편에서 약 4초 보인 차이의 원인도 확인하지 않았다.
- 79 제목 "Calico 노드에는 브리지가 없다"는 worker3 한 대의 관찰을 일반화한다(제목은 manifest 고정). 본문은 worker3 과 IPIP Always·iptables 구성으로 범위를 밝힌다.
- 79 진단 순서는 IPIP Always·iptables 에서만 확인했다. VXLAN·eBPF 는 실험하지 않았다(본문에 표시).

지적 14건 → 반영 12건
