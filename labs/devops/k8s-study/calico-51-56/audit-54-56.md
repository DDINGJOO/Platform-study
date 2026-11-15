# Calico 54~56편 독립 사실 감사

감사일: 2026-11-14 KST. 감사 역할: researcher. 최종 HTML의 본문·코드·표·도식 문구를 실험 원문, 수집 코드, 원본 pcap, 공식 문서 및 버전 고정 소스와 대조했다. 이전 작성자·패널의 통과 보고는 근거로 사용하지 않았다. 추가 실험이나 클러스터 명령은 실행하지 않았고, 저장된 pcap만 로컬 `tcpdump -nn -S -r`로 다시 읽었다. 본문과 실험 자료는 수정하지 않았다.

## 결론과 판정 분포

**핵심 주장 36개 묶음에서 확인 36, 불일치 0, 확인 불가 0, 과장 0. 수정 필요 사항 및 잔여 지적 0건.**

숫자는 아래 주장별 표의 행 수다. 같은 사실을 반복한 문장·도식·요약은 하나로 묶었다. 글에서 명시적으로 제외한 인터넷 상위 NAT, 모든 CNI의 기존 연결 처리, 정밀한 정책 적용 지연, 장기 연결·TLS·복합 장애 복구는 검증했다고 주장한 항목이 아니므로 확인 주장에 포함하지 않았다. 이 범위 밖의 사항은 이번 증거로 확인할 수 없으며, 본문도 이를 적절히 한정한다.

| 편 | 확인 | 불일치 | 확인 불가 | 과장 |
|---|---:|---:|---:|---:|
| 54 | 12 | 0 | 0 | 0 |
| 55 | 12 | 0 | 0 | 0 |
| 56 | 12 | 0 | 0 | 0 |
| 합계 | 36 | 0 | 0 | 0 |

## 감사 대상 고정

대상 디렉터리: `posts/CS/DevOps/k8s-study/`.

| 파일 | SHA256 |
|---|---|
| `54_54편 - NetworkPolicy를 적용했는데 왜 어떤 연결은 계속될까.html` | `56d8eff4b8f09d2bc60554e9acdaa6effc047db03ef50f2b4595355cfe1cb33c` |
| `55_55편 - 파드가 밖으로 나갈 때 출발지 IP는 어디서 바뀔까, Calico NAT와 conntrack.html` | `514d97f14dcc2bee3055f7a4a72cf7c5a6ee8f0c6aa34932da5effa5eda4855f` |
| `56_56편 - 파드 통신 장애는 어디부터 볼까, Calico 장애를 구간별로 좁히기.html` | `543d29e9bf9869d42dfa770bd76d884192abf13328902c49da7f098bcbbf7416` |

이하 실험 경로는 이 보고서가 있는 디렉터리 기준이다.

## 읽은 자료와 공식 출처

공통 지침은 `audit-brief.md`, `manifest.json`, `writer-brief.md`, `review-brief.md`, 저장소 `.claude/skills/blog-post-pipeline/SKILL.md`의 사실관계 감사 절, 설치된 `~/.codex/agents/researcher.toml`이다. 세 HTML 전체와 각 `54/README.md`, `55/README.md`, `56/README.md`를 읽었다.

- 54: `run.py`, `commands.json`, `results.json`, `policy-matrix.txt`, 정책 JSON들, `keepalive.jsonl`, `keepalive.pcap`, `keepalive-packets.txt`, `worker1-rules.txt`, `worker2-rules.txt`, `server-endpoint-chain.txt`, `calico-v3.33.0-endpoints.go`.
- 55: `run.py`, `commands.json`, `00-preflight.txt`, `04-pods.txt`, `05-pod-route.txt`, `06-pool.txt`, `07-nat-before.txt`, `08-nat-rules.txt`, `09-route.txt`, 세 요청 원문, `receiver.py`, `receiver.txt`, `13-conntrack.txt`, `conntrack-read.py`, `14-nat-after.txt`, `cali.pcap`, `sender-eth0.pcap`, `receiver-eth0.pcap` 및 텍스트, 정리 확인 원문.
- 56: `run.py`, `commands.json`, `matrix.json`, `matrix-capture.txt`. 명령 기록 안의 각 단계 Pod·Service·EndpointSlice·정책 JSON, 요청 stdout/stderr/exit, 경로 및 정리 결과를 직접 읽었다.

대조한 외부 기술 근거는 다음 1차 출처다. 조회 당시 Kubernetes 문서는 v1.37, Calico latest 문서는 3.33으로 표시됐다. 구현 설명은 설치 버전 v3.33.0 소스를 우선했다.

1. [Kubernetes NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/): 방향별 격리, 허용 합집합, 발신·수신 조건, 기존 연결 처리가 구현에 맡겨진다는 범위.
2. [Calico v3.33.0 endpoints.go](https://github.com/projectcalico/calico/blob/v3.33.0/felix/rules/endpoints.go): endpoint conntrack 규칙. 저장된 파일을 공식 raw 소스와 바이트 비교해 일치를 확인했다. 파일 SHA256은 `d4a69ce50a7c63997a154a539f506221a2fd63a835175349f2905e7fdf56e5ee`다.
3. [Calico outgoing NAT](https://docs.tigera.io/calico/latest/networking/configuring/workloads-outside-cluster), [v3.33.0 nat.go](https://github.com/projectcalico/calico/blob/v3.33.0/felix/rules/nat.go): 풀 밖 목적지의 SNAT, NAT 대상 출발 집합과 목적지 제외 집합, 추가 host-IP 제외 조건.
4. [Netfilter NAT 결정](https://www.netfilter.org/documentation/HOWTO/NAT-HOWTO-5.html), [iptables 확장 매뉴얼](https://man7.org/linux/man-pages/man8/iptables-extensions.8.html): 연결 단위 NAT 결정, MASQUERADE의 송신 인터페이스 주소, `--random-fully` 의미. 오래된 HOWTO로 최신 세부 구현까지 증명하지 않고, 실제 규칙·pcap 및 최신 매뉴얼과 함께 사용했다.
5. [커널 conntrack netlink 명세](https://docs.kernel.org/netlink/specs/conntrack.html), [Linux v6.8 conntrack 상태 UAPI](https://github.com/torvalds/linux/blob/v6.8/include/uapi/linux/netfilter/nf_conntrack_common.h), [v6.8 netlink 속성 UAPI](https://github.com/torvalds/linux/blob/v6.8/include/uapi/linux/netfilter/nfnetlink_conntrack.h): original/reply/status/timeout 속성과 `IPS_SRC_NAT = 1 << 4`.
6. [Kubernetes Service 진단](https://kubernetes.io/docs/tasks/debug/debug-application/debug-service/): Service 포트·selector·EndpointSlice·Pod 직접 요청의 대조.
7. [curl 종료 코드](https://everything.curl.dev/cmdline/exitcode.html): 6/7/28의 범위.
8. [ip-route 매뉴얼](https://man7.org/linux/man-pages/man8/ip-route.8.html): blackhole 폐기·EINVAL 및 경로 프로토콜 식별자.

## 54편: 정책·DNS·기존 연결

| # | 주장과 판정 | 원문·소스 대조 |
|---|---|---|
| 54-1 | **확인** — 전용 namespace와 Pod 배치·주소 | `commands.json`의 생성·placement 결과와 `run.py`. client-a `.81`, 서버 `.25`, worker1/worker2 배치가 본문과 일치한다. |
| 54-2 | **확인** — 서버 ingress만 빈 허용 목록으로 격리 | `deny-server-ingress.json`의 `role: server`, `policyTypes: [Ingress]`, `ingress: []`. 모든 Pod·egress를 함께 차단한다는 설명이 아니다. 공식 출처 1과 일치한다. |
| 54-3 | **확인** — 새 A·B 요청이 deny 후 실패 | `deny-new-a`, `deny-new-b`는 모두 exit 1, `wget: download timed out`. 적용 요청 성공만으로 차단을 단정하지 않고 새 연결 관측을 사용한다. |
| 54-4 | **확인** — allow-a 후 A만 성공, allow-b 추가 후 B도 성공 | 명령의 정책 적용 순서와 세 probe exit, `allow-a.json`, `allow-b.json`을 대조했다. 기존 deny 객체를 유지한 허용 합집합 설명이며 Calico 자체 Deny/order와 구분한다. 공식 출처 1과 일치한다. |
| 54-5 | **확인** — 서버 ingress 허용만으로 격리된 A egress를 통과할 수 없음 | `ingress-allowed-egress-denied` 실패 후 `a-to-server` 적용, `both-directions-allowed` 성공. 허용된 연결의 응답에 반대 방향 신규 연결 규칙을 복제해야 한다는 설명으로 확장하지 않는다. |
| 54-6 | **확인** — 같은 DNS 이름의 UDP/TCP를 따로 검사 | `run.py`의 A netns 직접 질의와 명령 기록. 기본 두 질의 성공, DNS 미허용 두 질의 실패, UDP만 허용하면 UDP 성공/TCP 실패, TCP 추가 후 TCP 성공과 hostname wget 성공을 확인했다. 자동 TCP fallback 실험이라고 쓰지 않는다. |
| 54-7 | **확인** — DNS 정책의 namespaceSelector와 podSelector는 같은 항목의 교집합 | `a-dns-udp.json`, `a-dns-tcp.json` 및 수집 코드가 본문의 YAML과 같다. NodeLocal DNSCache까지 같은 결과라고 주장하지 않는다. 공식 출처 1과 일치한다. |
| 54-8 | **확인** — 17개 검사와 12개의 HTTP 200 기록 | `results.json`/명령 원문의 probe 17개를 대조했다. `keepalive.jsonl`은 i=0~11, 전부 200, 전부 `.81:56494 → .25:80`이다. 명령 실패 exit 1/2를 의도한 차단과 구분한 설명도 맞다. |
| 54-9 | **확인** — 첫 응답은 정책 전이며 기존 연결 유지와 새 연결 실패를 구분 | `run.py`는 첫 stdout에서 200을 받은 후 deny를 적용한다. 원본 pcap에는 56494의 SYN/SYN-ACK과 후속 트래픽, 별도 56496의 재전송 SYN이 있다. **12회 전부 정책 후라는 주장은 없고**, Mac/VM 시계로 적용 지연을 계산하지 않는다고 명시한다. |
| 54-10 | **확인** — endpoint의 ESTABLISHED 허용이 정책 규칙 앞에 있음 | `server-endpoint-chain.txt`와 전체 worker2 규칙의 순서, v3.33.0 `appendConntrackRules`를 직접 대조했다. 카운터는 최종 수집 시점이지 deny 순간이라고 쓰지 않는다. 공식 출처 2와 일치한다. |
| 54-11 | **확인** — 관측한 기존 연결 동작의 구현·모드 범위 한정 | 공식 출처 1은 기존 연결에 대한 정책 변경 효과를 구현에 맡긴다. 본문은 Calico 3.33 iptables 경로의 결과로 한정하고, 도구의 `nf_tables` 문자열과 Calico native nftables 모드를 동일시하지 않는다. |
| 54-12 | **확인** — 전용 namespace 삭제와 4노드 Ready | 명령 기록의 cleanup 성공, 후속 namespace 조회의 NotFound, nodes-after 4개 Ready를 확인했다. 전역 conntrack 삭제나 기존 워크로드 정책 변경은 수집 코드에 없다. |

## 55편: NAT·pcap·conntrack

| # | 주장과 판정 | 원문·소스 대조 |
|---|---|---|
| 55-1 | **확인** — 수신기는 인터넷이 아닌 worker2 호스트 | 명령·수신기 실행 코드에서 `192.168.104.4:18555`를 확인했다. 본문 첫 부분과 도식에서 VM 노드 경계를 반복해 지정한다. |
| 55-2 | **확인** — 단일 Pod 풀과 natOutgoing 조건 | `06-pool.txt`의 `10.244.0.0/16`, `natOutgoing: true`; `.104.4`는 풀 밖이다. 출처 3 및 실제 규칙을 함께 사용하며 모든 노드 목적지를 무조건 NAT한다고 일반화하지 않는다. |
| 55-3 | **확인** — 일반 Pod·hostNetwork·노드 요청의 주소·포트 | 요청 원문과 `receiver.txt`의 `/pod`, `/hostNetwork`, `/node`를 대조했다. 수신기 관측은 `.104.3:7165`, `:45556`, `:45557`; 원래 일반 Pod는 `.194.92:45555`다. |
| 55-4 | **확인** — POSTROUTING에서 outgoing NAT 체인으로 이어지는 규칙 | `08-nat-rules.txt`의 호출 및 `src` NAT 풀/`! dst` 네트워크 풀/MASQUERADE 규칙을 확인했다. v3.33.0 `nat.go`의 집합 조건과 일치하고 host-IP 제외 설정 가능성도 본문에 적혀 있다. |
| 55-5 | **확인** — MASQUERADE와 random-fully 해석 | 규칙에 두 옵션이 실제 존재한다. 출처 4는 송신 인터페이스 주소 매핑 및 출발지 포트 무작위화를 뒷받침한다. `7165`는 이번 관측값으로 한정했다. |
| 55-6 | **확인** — 세 지점 원본 pcap에서 동일 SYN 대조 | pcap을 직접 다시 읽었다. cali는 `.194.92:45555`, 송신·수신 eth0는 `.104.3:7165`; SYN seq `345155042`, TS val `2719713481`가 같다. 주소 변환의 증거를 카운터 하나에 의존하지 않는다. |
| 55-7 | **확인** — 응답의 목적지가 Pod로 되돌아옴 | 원본 cali pcap의 SYN-ACK 목적지는 `.194.92:45555`, eth0 pcap은 `.104.3:7165`다. 순방향과 역방향을 모두 확인했다. 노드 간 pcap 시각 차이로 지연을 계산하지 않는다. |
| 55-8 | **확인** — NAT 카운터 22→23와 해석 한계 | `07-nat-before.txt`, `14-nat-after.txt`의 값이 일치한다. 본문은 공유 카운터만으로 연결 귀속을 확정하지 않고, 후속 패킷 수만큼 NAT 규칙 카운터가 늘어난다는 오해를 배제한다. 출처 4와 일치한다. |
| 55-9 | **확인** — original/reply와 src_nat 표 | `13-conntrack.txt`의 original `.194.92:45555 → .104.4:18555`, reply `.104.4:18555 → .104.3:7165`, true를 확인했다. hostNetwork/노드는 false이고 원래 포트가 보존됐다. |
| 55-10 | **확인** — Python 조회는 읽기 전용이며 SRC_NAT 판독에 근거가 있음 | `conntrack-read.py`는 nfnetlink get/dump와 출력 필터만 사용한다. 목적지 포트 18555 TCP만 저장한다. 출처 5의 v6.8 UAPI에서 original/reply/status 속성과 `IPS_SRC_NAT_BIT=4`를 확인해 코드의 `status & 16`과 맞음을 확인했다. 전체 TCP 상태 전이나 유지 시간까지 검증했다고 쓰지 않는다. |
| 55-11 | **확인** — 이번 목적지 경로는 eth0이며 관측 경계가 제한됨 | `09-route.txt`와 eth0 양쪽 캡처가 일치한다. IPIP Always를 모든 목적지의 tunl0 경유로 일반화하지 않는다. 상위 인터넷 NAT·공인 IP와 NAT 비활성화 비교는 미실험으로 명시한다. |
| 55-12 | **확인** — namespace 및 수신기 정리 완료 | namespace 후속 조회는 `--ignore-not-found -o name`에서 빈 출력·exit 0; worker2의 `ss -lnt sport = :18555`는 헤더뿐이다. 단순 삭제 요청 성공에 그치지 않고 사후 부재를 확인했다. |

## 56편: 같은 증상·다른 원인과 복구

| # | 주장과 판정 | 원문·소스 대조 |
|---|---|---|
| 56-1 | **확인** — 배치·주소와 단일 Service 대상 | Pod/Service/EndpointSlice 원문에서 client `.194.80`, local `.194.84`, remote `.126.28`, ClusterIP `10.104.230.204`를 확인했다. local과 remote가 다른 Pod라는 한계도 명시한다. |
| 56-2 | **확인** — nginx listen·localhost 및 4개 baseline 성공 | `remote-listen-localhost`의 80 LISTEN과 `localhost_http_ok`, baseline 4회 exit 0/HTTP 200을 확인했다. Running만으로 listen을 추정한 설명이 아니다. |
| 56-3 | **확인** — 매번 새 curl, 시간 제한, 총 24회 요청 | 코드와 24개 요청 명령의 `--noproxy *`, connect-timeout 2/max-time 3을 대조했다. 다섯 단계 각 4회 외에 포트·selector 복구 2회와 이름 오류/복구 2회다. 표의 각 칸이 순차 관측임도 명시한다. |
| 56-4 | **확인** — targetPort 8081에서 ready 대상은 있으나 Service 실패 | Service·EndpointSlice 원문에 ready=true, 대상 `.126.28`, port 8081이 있다. readinessProbe는 여전히 80이다. Pod IP 두 요청은 200, Service/DNS는 exit 7이며 출처 6의 진단 항목과 일치한다. |
| 56-5 | **확인** — selector 오류는 같은 curl 7이지만 endpoint 부재 | `app=does-not-exist`, EndpointSlice `endpoints: null`, Pod IP 성공과 Service/DNS exit 7을 직접 확인했다. 포트 오류와 endpoint 부재를 동일 원인으로 합치지 않는다. |
| 56-6 | **확인** — 두 Service 오류 모두 개별 복구 검사가 있음 | `restore-target-port` 뒤 `port-restored-cluster-ip` 200, `restore-selector` 뒤 `selector-restored-cluster-ip` 200이다. 최종 전체 성공만으로 중간 복구까지 추정한 주장이 아니다. |
| 56-7 | **확인** — ingress 격리는 remote만 막고 local 대조군은 성공 | `deny-web`은 app=web만 선택한다. local exit 0/200, remote·ClusterIP·DNS exit 28, 원문 stderr의 약 2초 연결 제한이 본문과 일치한다. |
| 56-8 | **확인** — 정책 제거 후 4개 요청 모두 복구 | `restore-policy` 삭제 성공 뒤 네 개 `policy-restored-*`가 모두 exit 0/200. 최종 정책 JSON도 빈 목록이다. 장기 연결·TLS·복합 장애의 복구로 확장하지 않는다. |
| 56-9 | **확인** — 잘못된 이름과 CoreDNS 장애를 구분 | URL `web-typo...`는 exit 6, `web...`는 200. 수집 코드가 DNS 설정을 바꾸지 않는다. 이름 해석 실패 관측을 CoreDNS 장애 실험이라고 주장하지 않는다. |
| 56-10 | **확인** — curl 6/7/28 및 HTTP 000의 의미를 한정 | 출처 7과 일치한다. 특히 exit 7만으로 RST/refused·Calico·BGP 장애를 확정하지 않는다. HTTP 응답을 받은 경우 및 TLS 단계의 구분은 일반 설명이며 이번 관측이라고 쓰지 않는다. |
| 56-11 | **확인** — blackhole /26과 실제 /32 경로 공존 | 경로 원문에 `/26 proto 80` 및 `.28 dev cali98721e3d585`가 있다. route get `.28`은 cali 성공, `.62`는 exit 2/EINVAL이다. 출처 8과 일치하며 `.62`의 IPAM 미할당이나 route get만으로 패킷 전달을 입증했다고 쓰지 않는다. 실제 HTTP 성공은 별도로 있다. |
| 56-12 | **확인** — 복구된 객체와 namespace 삭제·4노드 Ready | 최종 Service targetPort 80/selector app=web, ready EndpointSlice `.28:80`, 빈 정책 목록을 확인했다. cleanup 뒤 namespace 조회 빈 출력·exit 0, post-nodes 4개 Ready다. 코드도 기존 namespace 발견 시 시작하지 않고 자신이 만든 namespace만 정리한다. |

## 우선 반례 탐색 결과

- **“54편의 12회는 모두 정책 적용 후 성공”이라는 의심은 기각한다.** 첫 응답 후 정책을 적용하는 코드와, 정책 전 요청이 포함됐음을 밝힌 최종 본문이 일치한다. pcap에서도 기존 연결과 별도 신규 SYN을 구분할 수 있다. 정책 반영 완료의 정확한 밀리초나 12회의 정책 후 비율을 새로 주장하지 않았다.
- **“55편이 인터넷 출구 NAT를 입증했다”는 의심은 기각한다.** 수신기는 통제된 worker2 호스트이며 실제 풀 밖 목적지에 대한 worker1 SNAT를 입증한다. 상위 NAT·공인 출발지 주소와 비활성화 비교는 명시적으로 제외했다.
- **“56편의 curl 7 두 건은 같은 장애”라는 해석은 기각한다.** 8081의 ready endpoint와 대상 null의 차이를 원문으로 확인했다. 두 경우는 실제로 같은 exit 7이었고, 각각의 수정 후 새 요청 성공도 존재한다.
- **“정리 완료는 삭제 명령만 실행한 것”이라는 의심은 기각한다.** 54는 사후 NotFound, 55·56은 ignore-not-found의 빈 결과를 확인했다. 55 리스너 부재, 54·56의 4노드 Ready도 원문에 있다. 이를 기존 모든 워크로드의 무영향 보증으로 확대하지 않았다.

## 가장 신뢰도가 낮은 편과 남은 한계

상대적으로는 **54편**이다. 기존 연결이 유지됐다는 관측 자체는 JSONL·pcap·새 연결 실패·버전 소스로 교차 확인되지만, 정책 반영 완료 순간의 동일 시계 커널 스냅샷은 없다. 따라서 정확히 몇 번째 요청부터 정책 반영 이후인지, 적용 지연이 얼마인지는 입증할 수 없다. 본문은 첫 응답이 정책 전임과 Mac/VM 시계 차이를 명시하고 그 수치를 주장하지 않으므로 **수정 사항은 아니다**.

55편의 커스텀 netlink 판독은 Linux v6.8 UAPI까지 확인했고 pcap·수신기 로그와 독립적으로 일치한다. 56편은 한 번에 한 원인을 넣은 새 연결 실험으로서 근거가 충분하지만, 순차 조회·단일 대상·별개 local/remote Pod라는 범위를 넘어서 동시성·장기 연결·실서비스 복합 장애를 보장하지 않는다.

최종 수정 필요 사항: **없음. 잔여 지적 0건.** 이 보고서의 판정은 위 SHA256의 HTML과 보관된 실험 결과에 대한 사실 감사이며, 이번 감사에서 실험을 재실행했다는 뜻은 아니다.
