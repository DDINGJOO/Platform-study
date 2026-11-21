# 80편 감사 기록 (2026-11-21)

대상: `posts/CS/DevOps/k8s-study/80_80편 - 롤링 업데이트 중에 요청이 왜 끊길까, preStop과 readiness는 각각 무엇을 막나.html`
대조한 원자료: out/80-* 전부, LAB shared/ch05-pod 28·32·32b·32c(.sh/.txt, out 사본과 바이트 단위로 같음), lecture-notes.md, out/29-addons.txt·39-dns-source.txt(Corefile), out/64-pid1-sigmask.txt(노드 커널 6.8.0-149-generic), 작성자 스크래치의 추적 원본(w80/tmp2/*.tcpd·.pod·.mon·.meta)과 원문 사본(w80/src).

## 지적 목록

| # | 위치 | 문제 | 근거 | 조치 |
|---|---|---|---|---|
| 1 | 3절 첫 문단 | "이 RST는 모두 Killing된 옛 파드에서 왔어요"가 e7 전부를 옛 파드 RST로 읽히게 함. 추적 3(a)의 e7 14건 중 8건은 RST가 없고 SYN이 노드의 어느 인터페이스로도 나가지 않은 채 실패 | 80-e28-trace.txt 추적 3: e7 14, "RST 받은 시도 8개". tcpdump 원본 재분석: e7 6건=옛 hns5h RST, 8건=Out SYN 없음(+0.84~0.88s) | 반영: 잡힌 RST만 옛 파드, 추적 3의 8건은 RST 아님(ICMP는 안 잡아 거절 주체 미확인)으로 고침 |
| 2 | 3절, 3절 콜아웃 | 옛 파드별 RST 출처, m2kxb 0.87/0.88~0.98/0.99초, 추적 4(b) 최대 2.8초가 인용한 80-e28-trace.txt에 없음 | trace.txt는 회차 요약만 출력(analyze.py가 RST 출처를 print 하지 않음). 원본에서 다시 세면 값은 맞음(아래 "원본 재분석") | 반영: 원본에서 따로 센 값이고 trace.txt엔 요약만 있다고 본문에 명시. out/ 보강은 보고 |
| 3 | 3절 첫 문단 | "순서도 일정했어요" 과일반화 | 원본 재분석: gmcl5·bztcp는 RST 구간 없이 바로 무응답, 2nv5l·hmqdh·g8wbq는 끝까지 응답만 | 반영: "대체로" + RST 구간 없는 파드 명시 |
| 4 | 5절 "CPU나 포트" 문단 | "(e7은 모두 옛 파드의 RST와 같은 순간이었어요)" 부정확(1번과 같은 이유) | 추적 3의 8건 | 반영: "e7이 난 시도는 모두 tcpdump에 SYN이 잡혔다"(포트 고갈이면 SYN 전에 실패)로 바꿈. 원본 재분석에서 e7 전부가 50ms 안의 SYN 시도와 짝 |
| 5 | 3절 콜아웃 첫 줄 | "EndpointSlice 0.35초" (파드 삭제 기준)와 "재시작 뒤 2.8초" (rollout restart 기준) 비교 기준이 달라 kube-proxy 지연을 과장 | ljth2 Killing 10:26:04(초 단위), restart 10:26:02.6, 마지막 새 연결 +2.76 → Killing 뒤 0.36~1.36초 | 반영: "Killing 이벤트 뒤로도 최대 1.4초, 재시작 기준 2.8초" |
| 6 | 2절 둘째 문단 | 처음 실험(80-rollout-drop)도 35초로 씀 | 80-rollout-drop.sh `DUR=40` | 반영: "35초(처음 실험만 40초)" |
| 7 | 2절 종류 실험 설명 | 호출 끝 시각 기준이라 "몇 초 앞설 수 있다" → e28×10이면 첫 실패가 20초 가까이 앞섬 | curl `--max-time 2`는 전송마다. 추적 1 실패가 부하 끝(+31s) 뒤 +47s까지 이어짐 | 반영 |
| 8 | 2절 반복 결과, 4절 끝 | "(c)만 매번 0"인데 DNS 이름으로 보낸 32b(timing) (c)에서 6건 실패를 안 밝힘 | 80-rollout-drop-timing.txt (c): 실패 6, 09:56:14×1(재시작 09:56:17, 부하 시작 직후) | 반영: ClusterIP로 보낸 네 번으로 범위 한정 + timing (c) 6건(롤아웃 전, 원인 모름) 명시 |
| 9 | 4절 둘째 문단 | 부하 시작 직후 e28×5 회차 목록에서 종류 실험 (d) 누락 | kinds (d) 10:00:23(e28)×5, 재시작 10:00:25 | 반영 |
| 10 | 1절 | 75ms·0.35초를 정확한 값처럼 씀, "0.2초마다" 읽음 | 80-delete-race.sh: sleep 0.2 + kubectl, 실제 간격 0.27~0.28초 → 두 값은 상한 | 반영: "안에", "늦어도", 실제 간격 0.3초 남짓 |
| 11 | 1절 "왜 0이었을까" | nginx가 SIGQUIT에 하던 요청을 마친다는 근거로 64·65편을 댐. 64·65편엔 STOPSIGNAL SIGQUIT만 있고 graceful 서술 없음(64편엔 SIGQUIT 언급도 사실상 없음) | 64·65편 본문 검색, nginx.org/en/docs/control.html "QUIT graceful shutdown" | 반영: 정지 신호는 65편, graceful은 nginx 문서. 출처 단락에 링크 추가 |
| 12 | 5절 conntrack 용어 박스 | "이 노드는 SYN_SENT 120초, TIME_WAIT 120초, CLOSE 10초였어요"인데 노드 sysctl은 읽지 않음 | 80-sources-excerpts.txt는 커널 기본값. 덤프의 남은 시간(SYN_SENT 119, CLOSE 5)만 관측 | 반영: 커널 v6.8 기본값 + 덤프의 SYN_SENT·CLOSE 남은 시간이 맞았다로 |
| 13 | 5절 "왜 하필" 문단 | "남은 빈 짝수 포트가 바로 그 포트들이었어요" 단정 | 관측이 아닌 추론. 다만 14,116−14,111=5=gmcl5 SYN_SENT 5개, +25.1·27.2·29.2s에 다섯 포트만 함께 재사용(trace.txt 38~52줄, SYN 간격 줄) | 반영: 산술 근거 추가, "봐요"로 추론 표시 |
| 14 | 5절 커널 문단 | TIME_WAIT 재오픈(FIN 흔적 있으면 지우고 재조회)을 상태표가 하는 것처럼 씀. 이 부분은 excerpts에 없음 | v6.8 tcp_packet(): `old_state < TIME_WAIT`면 break, CLOSE_INIT 또는 같은 쪽 RST면 nf_ct_kill + -NF_REPEAT (w80/src 사본으로 확인) | 반영: tcp_packet() 이름과 "(또는 같은 쪽이 보낸 RST)" 명시. excerpts 보강은 보고 |
| 15 | 5절 "꼭 5개" 문단 | "2절의 e28×5도 같은 숫자예요" 미추적 실행을 같은 원인처럼 암시 | 종류 실험은 tcpdump 없음 | 반영: 같은 숫자지만 추적 안 해 같은 경로인지 모른다고 |
| 16 | 5절 정리 문단 | "추적한 세 회차의 e28은 모두 (i)" | 추적 1 e28 49건 중 8건은 tcpdump 종료 뒤라 미대조 | 반영: "맞춰 본 81건", 8건 미대조 명시 |
| 17 | 5절 콜아웃 마지막 줄 | preStop이 막는 길이라고만 써서 (b)의 e28을 덮음 | kinds (b) e28 29, 반복 (b) 3회 롤아웃 뒤 e28 6 | 반영: 종류 실험 (b) e28 29건, 경로 미추적 추가 |
| 18 | 요약 둘째 문단 | conntrack 원인을 모든 롤아웃 뒤 타임아웃으로 일반화 | 추적은 4회차(그중 e28 있는 3회차)만 | 반영: "tcpdump로 추적한 세 회차에서", 미추적 (b) 확인 못 함 추가 |
| 19 | lead | 같은 일반화 | 위와 같음 | 반영: "롤아웃 뒤 타임아웃을 추적해 conntrack에서 원인을 찾았어요"(136자) |
| 20 | 6절 첫 문단 | "DNS 이름 실험과 ClusterIP 실험이 같은 모양으로 실패한 것도 그 때문" 근거 약함(32는 종류·시각 기록 없음, 수치도 다름) | 80-rollout-drop.txt vs kinds | 반영: "DNS를 빼고 ClusterIP로 보낸 종류 실험에서도 실패가 그대로 난 것이 근거" |
| 21 | 6절 headless 문단 | CoreDNS ttl 30·cache disable 설정의 출처 미표기 | out/29-addons.txt Corefile(29편 인용), out/39-dns-source.txt | 반영: "(Corefile은 29편)" |
| 22 | 5절 추적 표 머리 | "노드 멈춤 최대 0.053초"는 멈춘 시간이 아니라 50ms 잠들기의 걸린 시간 | 80-e28-trace.sh GAP 스크립트(M=최대 간격) | 반영: "50ms 잠들기 최대(워커)" |
| 23 | 그림 4 alt | m2kxb·kgdm8 SYN_SENT가 둘 다 +1.1초부터라고 씀 | trace.txt 추적 2: kgdm8/SYN_SENT는 +4.1s 덤프부터 | 반영 |
| 24 | 5절 포트 60552 설명 | "새 SYN 11번" → 실제는 연결 시도 11번, 시도마다 SYN 2개 | trace.txt "SYN 2번" | 반영 |

## 확인 결과 문제 없음 (고치지 않음)

- e28 81건 = 41(5/36)+30(10/20)+10(5/5), 처음 20 / 다시 씀 61, TIME_WAIT 14,111·14,550·16,384·16,384, CPU 94/94/95/97%, 50ms 잠들기 0.053/0.057/0.057/0.054초: trace.txt와 일치.
- 포트 60552: +0.9 ~ +39.3초 12번 모두 gmcl5, 남은 시간 117→83초, +25.1~+39.3 8번: 일치.
- 반복 표 (a) 30·45·36·64, (b) 0·0·11·62, (c) 0×4 / 419,582+145,715=565,297, (d) 38·32·38·38, Killing 같은 초 e7 (a) 9·20·11 (d) 25·17·14, (b) Killing 순간 e7·e56 매번 0, (b) 3회 11건 모두 e28 중 5건 재시작 전: 일치. 그림 2 alt도 일치.
- 종류 실험 131,037/64(24/1/39), 97,594/62(33/0/29), 145,715/0, 130,101/38(22/2/14): 일치.
- 커널 근거: v6.8 tcp_timeouts(SYN_SENT 2 MINS, TIME_WAIT 2 MINS, CLOSE 10 SECS), 상태표 "sSS -> sSS Retransmitted SYN", inet_hashtables.c "In first pass we try ports of @low parity"(low=32768이 짝수), TCP_TIMEWAIT_LEN 60*HZ: excerpts에 원문. 노드 커널 6.8.0-149-generic(out/64-pid1-sigmask.txt)이라 v6.8 태그 인용은 맞음.
- kube-proxy v1.37.2 cleanup.go "Kubernetes UDP services can be affected by stale conntrack entries", "we are only interested in UDP services", "we only deal with UDP protocol entries": excerpts와 w80/src 사본에 원문.
- headless 74번 중 33번, fresh 0, TTL 30, CoreDNS 문서 ttl 기본 5초·cache disable 문구: 일치.
- 앞단 LB: LBC 문서 인용문·Initial/Draining, ELB deregistration 300초·500-level 인용문: excerpts와 일치. 네임스페이스 라벨·target-type ip 조건은 excerpts엔 없지만 같은 URL 원문(w80/src/lbc-pod-readiness-gate.md)에 있음.
- 번호 참조: 28편(kube-proxy iptables 규칙), 57편(EndpointSlice, readiness로 ready false), 62편(prober_manager.go, terminatingReplicas, 컨테이너 구별), 64·65편(PID 1·sh -c 신호, 점검표 줄), 67편(preStop 뒤 SIGTERM, 2초 하한), 70편(사이드카 종료 순서), 47편(iptables 전체 재작성), 55편(nfnetlink 읽기 전용 덤프): 각 편 본문과 맞음.
- 형식: style 블록 템플릿과 동일, lead 136자, tags, 시리즈 박스 series-boxes.html과 동일, h2 6, SVG 4, 용어 박스 7, 콜아웃 4, 요약 박스로 끝, 엠대시 0, 금지어 0, 띄운 조사 0, 태그 짝 맞음, 중복 id 없음, mask-check 깨끗함, 이미지 2개 존재.

## 원본 재분석 (w80/tmp2, 80-e28-analyze.py 앞부분 재사용. 스크래치라 지워질 수 있어 결과를 남김)

- 옛 파드별(SYN 시도 기준, 재시작 +초): 추적 1 fk92p 마지막 응답 0.63 / RST 0.67~0.78, gmcl5 마지막 응답 0.98 / RST 없음 / 무응답 0.87~2.13, 2nv5l 응답만(0.96). 추적 2 m2kxb 0.87 / RST 0.88~0.98 / 무응답 0.99, kgdm8 3.05 / RST 3.06~3.16 / 무응답 3.16~3.23, g8wbq 응답만. 추적 3 hns5h 0.62 / RST 0.67~0.78, bztcp 1.06 / RST 없음 / 무응답 0.98~2.29, hmqdh 응답만. 추적 4 2qzd5 1.73, ljth2 2.76, v45br 1.74 모두 응답만.
- RST 패킷 출처: 추적 1 12개 전부 옛 fk92p, 추적 2 58개(m2kxb 27, kgdm8 31), 추적 3 8개 전부 옛 hns5h, 추적 4 0개.
- e7·e56을 50ms 안의 SYN 시도와 짝지음: 추적 1 e7 12=fk92p RST 12, 추적 2 e7 52=RST 52(m2kxb 23, kgdm8 29), e56 4=RST 4, 추적 3 e7 14=hns5h RST 6 + Out SYN 없음 8. 짝 없는 e7 0건.
- 응답 판정은 SYN-ACK를 잡지 않아(필터가 SYN·RST만) "재전송도 RST도 없음"으로 추정한 것.

## 공통·원자료 쪽 보고 (직접 고치지 않음)

- out/ 보강 권장: 위 "원본 재분석" 결과를 낸 스크립트와 출력(옛 파드별 RST·응답 시각, e7 짝짓기)을 `out/80-e28-rst-order.txt`(+.py)로 남기면 3절의 수치가 공개 원자료로 받쳐짐. 지금은 본문에 "원본에서 따로 센 값"으로만 적었음.
- out/80-sources-excerpts.txt 보강 권장: nf_conntrack_proto_tcp.c의 tcp_packet() 재오픈 분기(`case TCP_CONNTRACK_SYN_SENT: if (old_state < TCP_CONNTRACK_TIME_WAIT) break; ... IP_CT_TCP_FLAG_CLOSE_INIT ... nf_ct_kill ... -NF_REPEAT`), LBC 문서의 네임스페이스 라벨·target-type ip 줄, nginx control 문서 QUIT/TERM 줄.
- .mask-allow 추가 줄 없음(mask-check 깨끗함).

## 남은 위험

- 출발 포트 범위 32768~60999와 짝수 14,116개는 80-e28-analyze.py에 하드코딩된 값이고 파드의 ip_local_port_range를 읽지 않았음(관측된 포트는 모두 범위 안).
- 추적 3·4의 TIME_WAIT 16,384는 netns TIME_WAIT 상한일 가능성이 있음(상한이면 일부 소켓이 TIME_WAIT를 건너뜀). 본문 결론엔 영향이 작지만 짝수 포트 산술은 추적 1에만 맞음.
- 추적 3의 Out 없는 SYN 8건이 무엇에 거절됐는지(ICMP·로컬 경로)는 미확인.
- 부하 시작 직후 e28×5, 종류 실험 (b) e28 29건, 32b (c) 6건은 원인 미확인으로 남음.

지적 24건 → 반영 24건
