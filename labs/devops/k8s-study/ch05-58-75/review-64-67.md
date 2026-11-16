# 64~67편 감사 기록 (PID 1과 신호)

대조한 원자료: BLOG/labs/devops/k8s-study/out/63-termination-timing.txt, 64-*, 65-*, 66-*, 67-* (.sh/.txt), LAB/shared/why/07-pid1-and-signals/notes.md·sources/(_index.txt 포함), LAB/shared/why/02-pod-and-pause/sources/(pause.c, pr-36853, prs-41583-45236-51634, kep-495, issue-1615), why/02 notes.md 연대표(9b747c3a9d).

일치를 확인한 것(지적 없음):
- 커널: 2009-04-02 Sukadev 커밋 3개, v2.6.29 없음/v2.6.30 있음, 921cf9f63089 인용문, 3597dfe01d12(2018) 인용문, v6.8 sig_task_ignored 코드(81~101줄 원문 그대로), send_signal_locked force 계산, SIG_KERNEL_ONLY_MASK = SIGKILL·SIGSTOP, copy_process의 SIGNAL_UNKILLABLE, __send_signal_locked의 ret=0, zap_pid_ns_processes, find_new_reaper 주석, sig_ignored의 blocked 주석, do_sigtimedwait의 real_blocked.
- man 페이지: kill(2) NOTES, pid_namespaces(7) 세 인용 원문 일치.
- 06 실험: kill 종료코드 네 번 모두 0, 안 -TERM·안 -KILL·노드 -TERM 생존, 노드 -KILL만 죽음(137/Error), 호스트 PID 57872.
- 63-termination-timing: NotFound +32.5/+31.7/+31.7초, Kill container +31.2/+30.5/+30.4초, Pod removed broadcasted +32.3/+31.5/+31.5초.
- 02-delete-timing 9가지: 31.0/30.9/31.0/30.8초 137, 0.7/0.7초 0, 0.6/0.7초 143, 5.7초 137, 신호 +0.1초, SIGKILL +30.1초/+5.1초, nginx만 quit.
- POSIX 2.12 인용(SIGINT·SIGQUIT 상속 포함), Dockerfile reference shell form 인용·top -b 10.19초/0.20초·exec "$@"·exec gosu, nginx #377(2019-11-15)·trac #753·1.19.1·3fb70ddd70(2020-11-24).
- Docker: #26061(2016-08-26 생성, 2016-09-20 머지, 기본 꺼짐), asottile 2016-10-06, #28037(2016-11-03), 1.13.0 CHANGELOG 2017-01-18, tianon·ndeloof·thaJeztah 인용.
- 쿠버네티스: #29747(2016-07-28, 미머지, 2016-11-17 닫힘, thockin의 docker 이슈), #36853(2016-11-15 생성, 2017-01-20 머지), #45236(2017-05-10 머지, kill 1 경고), #48937(2017-07-14, yujuhong·dchen1107 2017-08-08, verb 2017-08-30), #51634(2017-09-06), KEP-495(1.10/1.12/1.17, Non-Goals, Risks 3개), #1615 smarterclayton 2017-09-13, #84210 본문·코멘트·라벨.
- kubelet v1.37.2: killContainer(preStop 시간 차감, ordering 차감, 최소 2초), executePreStopHook(794줄 logger.Error, V(2) 로그, 초 단위 반환), setTerminationGracePeriod, minimumGracePeriodInSeconds=2, getContainerConfigStopSignal. 05 실험 수치(+10.0/+30.1, +30.1/+32.1, +10.1, timeout 20/2, deletionTimestamp +29초) 일치.
- containerd v2.4.1 신호 선택 순서(스펙 stop_signal → 기록된 STOPSIGNAL → 이미지 재조회 → SIGTERM) 코드 원문 일치.
- KEP-4960: 1.33 알파 기본 false가 v1.37.2 유일 항목, dropContainerStopSignals·PrepareForCreate(128)→Validate(146), SIGFOO dry-run 통과, kep.yaml 이력(2025-01-31, 2026-06-10 v1.37, 2026-09-22 v1.38), #143690 master 머지 2026-11-06(UTC), #142565 열림, Version Skew "silently dropped", Risks.
- 링크 URL 전부 _index.txt 원문 URL과 일치. 이미지 7개 존재, alt 수치가 이미지·out 원자료와 일치.
- 형식: style 블록 동일, lead 134~150자, tags 있음, 시리즈 박스 series-boxes.html과 동일, h2 5, SVG 3, 용어 박스 6, 콜아웃 2~3, 요약 박스로 끝남, 엠대시 0, 강의·슬라이드 0, 띄운 조사 0, 중복 id 0, 태그 짝 맞음, mask-check 깨끗함.

## 지적 목록

| # | 편 | 위치 | 문제 | 근거 | 조치 |
|---|---|---|---|---|---|
| 1 | 64 | 5절 h3 "그래서 PID 1 문제는 여러 곳에서 나온다" | 도입의 사이드카 PID 1 셸이 "TERM에 핸들러를 걸지 않았어요"라고 측정한 것처럼 단정. 그 사이드카의 마스크는 읽지 않았다 | 64-native-sidecar-finish.sh/txt에 마스크 측정 없음. 근거가 되는 것은 64-pid1-sigmask.txt c-sh-c-2cmds의 sh SigCgt INT CHLD | 반영: 셸이 PID 1로 남는 모양이라고 쓰고, c-sh-c-2cmds 측정을 근거로 들도록 고침 |
| 2 | 64 | 2절 신호 마스크 출력 블록 | f-nginx의 "PID 1 nginx" 줄과 SigCgt 줄을 한 줄로 합쳐 원본에 없는 줄을 만들었다. a-sleep 들여쓰기도 원본과 달랐다 | 64-pid1-sigmask.txt: PID 1 줄은 SigBlk, 다음 두 줄이 SigIgn·SigCgt | 반영: 원본 세 줄(SigBlk/SigIgn/SigCgt)과 들여쓰기로 복원 |
| 3 | 64 | 💡 콜아웃 셋째 줄 | "0이나 143이면 PID 1이 신호에 반응해 끝난 거예요". 143은 g-share처럼 PID 1이 아닌 첫 프로세스가 기본 동작으로 죽은 경우도 포함 | 65-delete-timing.txt g-share 143(sleep은 PID 6), notes 3-5 | 반영: "컨테이너의 첫 프로세스가 정지 신호에 끝난 거예요" |
| 4 | 64 | 1절 "kubelet의 Pod removed broadcasted" | 63-termination-timing에는 이 로그가 어느 구성 요소 것인지 적혀 있지 않다 | 노드 k8s-worker3 journal(읽기만): `SYSLOG_IDENTIFIER=kubelet`, `server.go:190] "Pod removed broadcasted"` | 반박: kubelet 로그가 맞음. 유지 |
| 5 | 65 | 도입 둘째 문단 | "sleep infinity & wait로 두 글자를 바꾼 파드". 실제로는 `; echo bye`를 ` & wait`로 바꿨다 | 64-pid1-sigmask.txt d·e command | 반영: "같은 trap을 걸고 뒷부분만 sleep infinity & wait로 바꾼 파드" |
| 6 | 65 | 3절 e 문단 | "백그라운드 sleep은 SIGTERM을 받지 않았어요" 단정. 정지 신호가 첫 프로세스에만 간다는 것은 runc·shim 소스 미확인 추론(notes 9)이고 e에서는 관측할 수 없다. 이어지는 SigIgn INT QUIT 문장도 TERM 수신과 무관하다 | notes.md 3-6, 9절 넷째 항목 | 반영: "2절의 추론대로라면"으로 한정하고 이 실험으로는 가릴 수 없다고 적음. TERM이 무시 목록에 없다고 밝히고, 어느 쪽이든 zap_pid_ns_processes로 끝난다고 정리 |
| 7 | 65 | 그림 2 결론 문구 | "정지 신호는 PID 1에만 가고"라고 추론을 단정 | 같은 곳(본문은 추론이라고 밝힘) | 반영: "신호는 PID 1에서 멈췄고 자식 sleep에는 닿지 않았어요 (c의 결과로 본 추론)" |
| 8 | 65 | 💡 실무 콜아웃 넷째 줄 | `crictl inspecti`의 "config.StopSignal". 실제 경로는 info.imageSpec.config.StopSignal | 64-pid1-sigmask.sh 84줄 | 반영: 경로를 고침 |
| 9 | 65 | 2절 "Docker의 기본 grace인 10초" | Dockerfile reference 발췌에는 10초 기본값이 없다 | sources/nginx-docker-stopsignal-sigquit.md #377 본문 "Docker will then wait 10 seconds before sending SIGKILL" | 반박: 원자료로 받쳐짐. 유지 |
| 10 | 66 | 4절 #36853 verb 인용 해석 | "신호 전달과 다른 init 기능은 kubelet이 더 잘 다룰 것이니"라고 풀었다. verb 본인이 뒤에 정정한 말을 빼고 그 뒤 문장만 인용해서, kubelet이 신호를 전달한다는 반대 뜻으로 읽혔다 | why/02 sources/pr-36853-pause-sigchld.md: vishh 2016-12-24 "How do you expect kubelet to forward signals?", verb 2017-01-14 "I don't expect the kubelet to forward signals. I meant that init features *other* than signal handling are better handled by the kubelet." | 반영: vishh의 반문과 verb의 정정 인용을 넣고 해석을 고침. "신호 전달 없이 좀비 수거만 넣은 채 머지"로 맺음 |
| 11 | 66 | 1절 첫 문단 | "z-sleep의 ps를 보면 좀비들은 모두". ps는 앞 6줄(좀비 5개)만 남겼다 | 66-zombie-pile.txt "z-sleep의 ps (앞 6줄)", 노드 "자식 중 Z 상태: 20개" | 반영: "ps 앞 6줄에 보인 좀비는 모두…, 노드에서 세어 보면 20개 전부가 같았어요" |
| 12 | 67 | 1절 preStop 용어 박스 | "preStop이 끝난 뒤에 정지 신호가 가요". p45-exec처럼 grace를 넘기면 훅이 도는 중에 신호가 간다 | 67-prestop-grace.txt p45-exec, executePreStopHook 801~808줄 | 반영: "preStop이 끝나거나 grace를 다 쓰면 그다음에 정지 신호가 가요(2절)" |
| 13 | 67 | 4절 결과 아래 문단 | "어느 쪽이든 SIGKILL은 StopContainer 뒤 30초 근처". 앞선 실행(+0.0초)의 SIGKILL 시각은 out/에도 notes에도 없다 | 67-stopsignal-gate.txt(+1.4초 → +31.5초), notes 6절 04 | 반영: "이번 실행에서 SIGKILL은 StopContainer 뒤 30.1초에 갔어요"로 한정 |
| 14 | 67 | 4절 마지막 문단 | "SIGKILL이 아닌 다른 신호를 지정해도 커널이 버려요". sig_task_ignored의 예외는 SIGKILL·SIGSTOP 두 개다(노드에서 온 SIGSTOP은 멈춤) | kernel-v6.8-signal.c 91~93줄, signal.h SIG_KERNEL_ONLY_MASK | 반영: "SIGKILL·SIGSTOP이 아닌 신호를 지정하면" |
| 15 | 67 | 5절 첫 문단 | "containerd PR #11774는 … 머지됐고 작성자 sreeram-venkitesh는". #11774의 작성자로 읽히는데 원자료에는 #11774 작성자가 없다. sreeram은 KEP 작성자다 | kep-4960 kep.yaml authors, issue-enh-4960-tracking.md | 반영: "KEP 작성자 sreeram-venkitesh" |
| 16 | 67 | 3절·5절 "containerd PR #11774(2026-04-28 머지), 2.3.0부터 포함" | sources 원문에는 머지 날짜와 2.3.0이 없다 | notes.md 연대표 37줄에 있고, 추적 이슈 2026-04-30 "merged this week"와 맞음 | 반박: notes 연대표와 일치. 유지(2.3.0 포함은 notes에만 있는 사실이라 남은 위험에 적음) |

## 남은 위험
- 정지 신호가 컨테이너 첫 프로세스에만 간다는 것은 runc·shim 소스로 확인하지 않은 추론이다. 65편은 추론으로 밝혔고, 64·66편은 첫 프로세스가 곧 받는 쪽인 경우만 다룬다.
- busybox sh가 명령을 exec하는 동작은 관찰만 했다(65편 콜아웃에 밝힘).
- containerd #11774가 2.3.0부터 포함됐다는 것은 notes.md에만 있다.
- 66편 그림 4 연표의 점 위치는 대략이다(1.17 GA 2019-12, #84210 2019-10이 2018~2019 중간쯤에 그려짐). 날짜를 적은 것은 아니라서 고치지 않았다.
- 67편 공식 문서 인용은 website main 기준이다(1.38 문서일 수 있음, notes 9). 인용한 문장은 v1.37.2 코드 동작과 맞는다.
- 67편 이미지 01의 kubelet 로그 줄 끝에 podUID 조각(ace0e568-…)이 보인다. mask-check는 통과했다.

지적 16건 → 반영 13건
