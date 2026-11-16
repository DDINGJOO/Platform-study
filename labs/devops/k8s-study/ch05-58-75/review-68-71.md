# 68~71편 감사 (사이드카 묶음)

대조한 원자료: `labs/devops/k8s-study/out/68-*·69-*·70-*·71-*` (LAB `shared/why/06-sidecar-containers/0N-*`, `shared/ch05-pod/12*` 와 diff 결과 모두 동일), `LAB/shared/why/06-sidecar-containers/notes.md`, `sources/` 전 파일, 캡처 PNG 7장.

형식 점검(수정 뒤): 4편 모두 style 블록이 템플릿과 같음, 시리즈 박스가 series-boxes.html 블록과 글자 단위로 같음, lead 146·148·144·147자, h2 5·6·5·5, SVG 3·3·3·2, 용어 박스 6·6·5·4, 콜아웃 3·3·5·5, 요약 박스가 마지막, 엠대시 0, 강의·슬라이드·수업 0, 산문의 띄운 조사 0, 태그 짝·중복 id 문제 없음, mask-check 깨끗함, 이미지 7장 존재.

## 지적 목록

| # | 편 | 위치 | 문제 | 근거 | 조치 |
|---|---|---|---|---|---|
| 1 | 68 | 1절 old-sidecar 문단 | "app이 11:29:55에 끝났지만 30초 뒤에도 logger가 running"은 앱 종료 30초 뒤로 읽힌다. 30초는 파드 생성 기준이다 | out/68-init-sidecar.txt `## old-sidecar (30초 뒤)`, 생성 20:29:47 KST | 반영: "파드를 만들고 30초가 지난 시점에도" |
| 2 | 68 | 5절 첫 KEP 문단 | "2018년 5월 14일 ... 첫 KEP를 올렸어요 ... 목표는 #25908과 #65502"는 5월 판이 6월에 생긴 #65502를 겨냥한 것처럼 읽힌다 | #65502 생성 2018-06-26(kep-753-history), 발췌 파일은 last-updated 2018-11-20인 병합본 | 반영: "병합된 판의 Goals는 #25908과 그 뒤 6월에 올라온 #65502를" |
| 3 | 68 | 그림 1·3 (70 그림 2·4, 71 그림 1도 같음) | 캡처의 명령 줄이 out/ 이름이 아니라 LAB 스크립트 경로(`04-job-completes.sh` 등) | out/ 파일은 LAB 원본과 diff 동일, 꼬리말 경로는 out/ 파일. 실제 실행 명령을 찍은 것이라 사실 오류 아님 | 반박(유지) |
| 4 | 68 | 요약 마지막 문장 | "다음 질문, 표시를 어디에 붙이느냐를 남겼어요"가 다음 편 예고처럼 보일 수 있다 | 5절 결론(원안 Non-Goals·Risks가 남긴 문제)을 되짚는 문장이고 다음 편을 언급하지 않는다 | 반박(유지) |
| 5 | 69 | 1절 #1344 문단 | "같은 판의 Risks 절"이 바로 앞의 2019-11 #1344 판을 가리키는 것처럼 읽힌다. 인용한 systemd 문장은 2019-06-19 implementable 판에 있다 | kep-753-v2019-06-19-d4277c2d61-implementable.md L225 | 반영: "implementable 판의 Risks 절" |
| 6 | 69 | 3절 용어 박스 graceful node shutdown | "2020년 당시 KEP는 ... systemd가 컨테이너를 멈춘다고 적었어요"는 판이 틀렸다. systemd 문장은 2019 판, 2020-06-24 판은 "the kubelet doesn't gracefully shutdown all of the containers" | 두 판본 발췌 | 반영: 2019 판과 2020 판을 나눠 적음 |
| 7 | 69 | 4절 WG 요구사항 인용 | 요구사항 4번의 하위 5항목(Security isolation 등)을 생략 표시 없이 뺐다 | gdoc-sidecar-wg-notes 11/15/2022 | 반영: 4번 아래에 `...` 추가 |
| 8 | 69 | 5절 smarterclayton | "initContainers 전체를 새 이름으로 바꾸는 안에도 반대"는 원문과 다르다. 그는 init·infra 컨테이너를 따로 된 목록으로 나누는 것에 반대했고, SergeyKanzhelev가 뒤에 "이 대안은 이름 바꾸기였다"고 정정했다 | pr-enh-3761 discussion_r1083039652, r1083167975, r1084417416 | 반영: "init 컨테이너와 인프라 컨테이너를 서로 다른 목록으로 나누는 것에도 반대 ... 둘 다 init 컨테이너의 한 종류로" |
| 9 | 69 | 5절 started 결론 | "2023년 2월 1일 워킹 그룹 회의"는 날짜가 틀릴 수 있다. 코멘트는 2023-02-01T01:58Z에 "today's Sidecar WG meeting"이라고 썼고, 미국 시각으로는 1월 31일(화, WG 정례 요일)이다 | pr-enh-3761 discussion_r1092674043, WG 회의록 날짜(11/15·11/22·12/6·12/13·1/3·1/10 모두 화요일) | 반영: "회의의 결론은 그가 2023년 2월 1일(UTC) PR에 옮겼어요" |
| 10 | 69 | 6절 Istio 문단 | "그 사이 사용자들은 holdApplicationUntilProxyStarts와 /quitquitquit을 계속 썼어요"는 사용 실태 근거가 없다(notes.md 5절의 서술을 단정) | sources에 사용 실태 자료 없음 | 반영: "그 사이 기본 설정의 Istio에서 순서와 Job 종료를 맞추는 방법은 ... 같은 우회였어요" |
| 11 | 70 | 3절 "중요한 점" 문단과 요약 | "사이드카 때문에 파드의 유예 시간이 늘어나지 않는다"는 실험 (c)와 어긋난다. 유예 6초인데 삭제(12:12:43) 뒤 사이드카 종료는 12:12:51, 약 8초. 최소 2초 때문에 유예를 2초 넘긴다 | out/70-shutdown-order.txt (c), kuberuntime_container.go L907~L910 | 반영: "사이드카 몫의 유예 시간이 따로 생기지 않는다 ... (c)의 파드가 유예 6초보다 2초쯤 늦게 끝난 것도 이 2초 때문", 요약도 같은 뜻으로 |
| 12 | 70 | 5절 끝 | "03처럼 틀려요"의 03은 LAB 실험 번호라 독자가 알 수 없다 | 글 안에서 그 실험은 never-native(68-restart-never.txt) | 반영: "never-native의 crashy에서처럼" |
| 13 | 70 | 3절 sidecar-ignore 문단 | "ch05에서 돌린"은 LAB 디렉터리 이름이라 독자가 알 수 없다 | 68편은 같은 실험을 "같은 날 먼저 돌린 실험"으로 부름 | 반영: "같은 날 먼저 돌린" |
| 14 | 70 | 2절 콜아웃 | "사이드카의 preStop은 앱이 SIGTERM을 받는 순간에 와요"는 파드 삭제일 때만 맞다. 앱이 스스로 끝나는 (a)에서는 앱 종료 0.08초 뒤 | out/70-shutdown-order.txt (a)(b) | 반영: "파드를 지우면" 추가 |
| 15 | 71 | lead | "앱이 끝나고 75초가 지나도 파드가 Running"은 틀렸다. 75초는 생성 기준이고 app은 10초에 끝났다(앱 종료 뒤로는 약 65초) | out/71-restart-rules.txt `## 생성 후 약 75초`, .sh app `sleep 10` | 반영: "앱이 끝났는데도 생성 75초 뒤까지" (길이 147자로 조정) |
| 16 | 71 | 요약 첫 문단 | 15와 같은 문제("app이 끝난 뒤 75초가 지나도") | 같음 | 반영: "app이 10초에 끝났는데도 생성 75초 뒤까지" |
| 17 | 71 | 3절 always-never 문단 | "once는 3초 뒤 exit 0으로 끝난 뒤 60초가 지나도"도 생성 기준을 종료 기준처럼 썼다 | out/71-restart-combos.txt `## 생성 후 약 60초` | 반영: "파드를 만들고 60초가 지나도" |
| 18 | 71 | 3절 never-onfail 문단 끝 | "컨테이너와 파드의 restartPolicy가 하나도 같지 않은 파드는 이번에 시험하지 않았어요"는 사실과 반대다. never-onfail은 컨테이너가 app(OnFailure) 하나뿐인 Never 파드라 바로 그런 파드다 | out/71-restart-combos.sh never-onfail 스펙, KEP-753 Future 절 "likely ... require at least one container to have a restartPolicy matching" | 반영: never-onfail이 그런 파드이고 v1.37.2가 그 조건을 요구하지 않았다고 고침 |
| 19 | 71 | 1절 KEP 예상 문단 | "needs to be carefully reviewed ..."를 "Future use of restartPolicy field" 절의 문장처럼 "동시에"로 이었다. 실제로는 "Use Always vs. New enum value" 절 문장 | kep-753-README-excerpts.md L262~L270 vs L407~ | 반영: "Always와 새 enum 값을 비교한 절에서는" |
| 20 | 71 | 2절 KEP-5307 Motivation | "한 파드가 실패하면 ... 그 자리에서 컨테이너를 다시 띄워"는 원문과 다르다. 원문은 "interrupt all Pods by restarting them, so they all will start from the previous checkpoint" | kep-5307 README Motivation | 반영: "한 파드라도 실패하면 모든 파드를 다시 시작해 ... 제자리에서 하도록 따로 다뤄야" |
| 21 | 71 | 4절 KEP-753 종료 절 | "1.29 베타를 준비하던 KEP-753의 종료 절은 이런 문장을 담고 있었어요"는 지금은 없는 것처럼 읽힌다. 2025-02 현재판(fc09a26d42)에도 그대로 있다 | kep-753-README-excerpts.md L368~L369 | 반영: "1.29 베타를 준비하며 적은 이런 문장이 있고 지금 판에도 남아 있어요" |
| 22 | 71 | 3절 첫 문장 | "이 필드의 이력은 한 바퀴를 돌았어요"는 비유 | writer-brief 비유 금지 | 반영: "이 필드는 2022년에 한 번 버려졌던 생각이에요" |
| 23 | 71 | 1절 STATUS 설명 | "그 순간 helper가 막 끝나 있었기 때문"의 "막"은 근거가 없다(75초 시점 helper는 terminated, 마지막 재시작은 RESTARTS `52s ago`) | out/71-restart-rules.txt | 반영: "그 순간 helper도 끝나 있어서 두 컨테이너가 모두 terminated였기 때문" |

## 확인한 것 (문제 없음)
- #25908: 2016-05-19 a-robinson, 2021-02-07 닫힘, 코멘트 132, +1 422, 2024-11 Pierre-VF 코멘트 일치.
- KEP 판본: 2018-05-14(community PR #2148, 2018-11-29 병합), 2019-03-26 enh #919 → 2019-06-19 implementable, 2020-06-24 provisional(enh #1874, rata), 2020-08 sig-node 이동 일치.
- 1.15~1.18 연기: 2019-04-12·04-29, 08-23, 11-13, 2020-03-04~06 일치. 2020-03-04 Joseph-Irving, 03-05 derekwaynecarr·liggitt, 03-06 smarterclayton 인용문 원문과 글자 단위로 일치(UTC 날짜). 2020-03-10 thockin 코멘트 인용 3개 원문 일치, 서명자 실명은 단정하지 않음.
- 2020-05-08 thockin, 2020-06-23 회의·06-24 #1874, 2020-10-21 닫힘 인용 일치.
- 2022-10-06 thockin(#2869), 2022-11-15 WG 버린 설계·요구사항, 11-22 Tim·Felix, 12-06 예시 YAML·jpbetz 발언 일치.
- 1.27 목표 → 2023-03-15 marosset 해제, 1.28 알파 #116429(2023-07-08), 1.29 베타 #120620·#121579(2023-10-31), 1.33 GA #129731(2025-02-05, "will be removed in v1.36"), 1.37 #137755(2026-04-23) 일치. 늦어진 이유는 "확인 못 함"으로 한정돼 있음.
- 2024-10 KEP 문장 변경(#4880, 33d91fe4d2)·#120234 인용 일치.
- 종료 순서: preStop 동시(29.271/29.276/29.280), 역순 TERM(35.309 → 37.357), 유예 바닥 시 동시 TERM(49.748/49.755) 뒤 2초에 137, kubelet 코드(newTerminationOrdering, killContainer L895~L915, minimumGracePeriodInSeconds) 일치.
- readiness는 다음 시작을 막지 않음(notready·slow 모두 12:14:19), postStart 5초(12:14:14 → 19), startupProbe 뒤 init2 12:14:30·app 12:14:31, READY 3/4 일치.
- BackOff 중 137: 42초 waiting:CrashLoopBackOff → 45초 terminated:137, reason·message가 status_manager.TerminatePod L757~L770, initializedContainers L837~L848과 일치.
- KEP-5307 kep.yaml(alpha 1.34, beta 1.35, stable v1.36), #132642·#134631 병합일, kube_features.go L1438~L1441(1.35 Beta에서 멈춤), 규칙 20개·값 255개(validation.go L3810, L3829) 일치. KEP-4438 kep.yaml(implementable, alpha v1.38, 게이트 이름), Goals, 이슈 열림 일치.
- Istio: 1.7부터·1.27부터 같은 노트의 해석은 글에 쓰지 않았고 PR 번호와 머지일(#15123 2019-06-26, #15406 2019-07-09, #24737 2020-07-17, #45959 2023-07-17, #47226 2023-10-19, #56428 2025-07-07)만 썼음. 일치.
- 70편 그림 4(캡처 02): 꼬리말 원자료가 out/68-restart-never.txt이고 4절이 "같은 파일(68-restart-never.txt)의 never-native"라고 밝힘. alt의 137·ContainerStatusUnknown·message·lastExit 1·Succeeded 모두 캡처와 일치.
- 링크 URL은 sources/_index.txt 및 발췌 파일의 URL과 일치(validation.go L3931~L3978, L3776~L3837, types.go L3204~, startContainer L291~L340 등).

지적 23건 → 반영 21건
