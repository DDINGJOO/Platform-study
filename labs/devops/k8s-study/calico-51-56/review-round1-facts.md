# 51~56편 독립 퇴고 1차: 사실관계

판정: **통과**. 차단 0건 / 수정 필요 0건 / 확인 필요 0건. 수정 지적(F 번호)은 없다.

여섯 HTML의 본문·코드·표·SVG 텍스트·캡션을 읽고, 주소·장치·수치·프로토콜·실험 결론을 저장된 원문과 대조했다. 연결된 PNG 9개도 직접 열어 수치를 확인했다. 클러스터에 접속하거나 실험을 다시 실행하지 않았으며, 이 보고서 외 파일은 수정하지 않았다.

## 핵심 주장별 대조 결과

| 편 | 판정 | 확인한 주장과 원문 |
|---|---|---|
| 51 | 통과 | sandbox/app0/app1의 netns inode `4026532560` 일치, hostNetwork와 호스트 inode 일치. Pod eth0 `ifindex=3/link_index=64`와 호스트 `cali0cbfd12677e`의 `64/@if3` 및 ethtool peer 3을 함께 확인했다. MTU 1480, Pod /32, gateway 169.254.1.1, proxy_arp=1·forwarding=1, 호스트 /32 경로와 ping 2/2가 원문과 맞는다. 설정만으로 ARP 패킷을 관찰했다고 쓰지 않는다. |
| 52 | 통과 | 같은 노드 연결 45252와 다른 노드 연결 45253의 지점별 12개/0개 집계가 `analysis.json`과 맞는다. 원격 SYN의 seq `3184915459`, inner IP ID 3100, TTL 64→63→62, outer 노드 주소 `.3→.4`, IPv4 protocol 4 내부 TCP가 맞는다. `worker1-eth0.pcap`을 별도 tcpdump로 읽어 SYN을 직접 확인했다. eth0 전체 파일 26/21개와 실험 연결 12개를 구분한다. |
| 53 | 통과 | 실제 Calico 경계 ping 1452 성공/1453 로컬 오류 MTU1480이 기록과 맞는다. 1452+8+20=1480, IPIP 외부 IPv4 20바이트가 맞다. 별도 Linux netns의 1300 병목 실험에서 ICMP 차단 시 curl28/HTTP000, 허용 시 서버 `received=65536`·HTTP200과 cache MTU1300을 확인했다. 전송량 `uploaded`와 서버 수신량을 구분하며, 이 격리 실험을 실제 Calico 장애로 서술하지 않는다. |
| 54 | 통과 | 17개 결과가 `results.json` 및 정책 JSON과 맞는다. A/B ingress 허용의 합집합, 송신 egress와 수신 ingress의 양쪽 허용, DNS UDP/TCP 별도 검증이 맞다. 동일 소켓 `.81:56494→.25:80`에서 12회 HTTP200이 기록되었고 신규 연결은 차단됐다. 전부 deny 이후의 12회라고 하지 않는다. 마지막 endpoint 체인의 RELATED,ESTABLISHED ACCEPT가 정책보다 앞에 존재한다. 이 스냅샷을 deny 직후 카운터라고 주장하지 않는다. |
| 55 | 통과 | Pod `.92:45555`가 노드 `.3:7165`로 바뀌는 동일 ISN `345155042`를 cali·송신 eth0·수신 eth0 원문에서 확인했다. cali와 송신 eth0 pcap도 별도 tcpdump로 다시 읽었다. 응답은 cali에서 Pod 원래 주소/포트로 복원된다. 수신 로그의 일반/hostNetwork/노드 세 요청과 conntrack original/reply tuple, src_nat 상태가 맞는다. MASQUERADE --random-fully와 IP set 조건이 실제 규칙과 일치한다. |
| 56 | 통과 | 새 curl 프로세스 24회와 66개 명령 기록을 확인했다. targetPort8081 오류/selector 불일치에서 Service만 curl7, ingress deny에서 원격 대상 및 그 Service가 curl28, 오타 이름에서 curl6인 표가 원문과 일치한다. EndpointSlice의 ready=true/port8081과 endpoints=null은 실제 조회값이다. blackhole /26과 실제 Pod /32를 함께 조회했으며 `.28`은 cali를 선택하고 `.62`는 EINVAL이었다. `.62`가 IPAM 미할당이라고 추론하지 않는다. |

## 검토했으나 결함으로 채택하지 않은 우려

- **56편 ready=true와 targetPort8081의 모순:** 기각. `56/resources.json`의 nginx readinessProbe는 실제 서비스 포트 80을 검사한다. Service targetPort를 8081로 잘못 바꿔도 해당 probe 성공과 EndpointSlice ready=true는 모순되지 않는다.
- **54편 정책 적용 뒤 기존 연결이 유지되므로 정책 우회라고 단정하는지:** 기각. 글은 구현별 동작으로 한정하고, 적용 전 첫 응답·관측 시계 차이·최종 규칙 스냅샷을 구분한다. 표준 API 동작과 관찰을 뒤섞지 않는다.
- **55편 목적지가 클러스터 노드이므로 outgoing NAT 실험이 무효인지:** 기각. Calico IPPool 밖의 목적지라는 조건이 핵심이다. 실제 pool은 10.244.0.0/16이고 목적지는 192.168.104.4다. 글도 이 실험을 인터넷 구간 검증으로 확대하지 않는다.
- **51편 현재 경로만으로 CNI/Felix/BIRD 작성 주체를 입증했는지:** 기각. 글은 현재 경로 조회·실제 ping과 버전 고정 공식 소스를 구분한다. IPIP 경로 소유권은 별도 선행 실험을 참조하며 이번 관찰로 새롭게 입증했다고 하지 않는다.
- **이미지를 직접 터미널 사진으로 가장하는지:** 기각. PNG는 원문 발췌 또는 파생 요약의 렌더링이라고 캡션/README에 설명한다. 이미지 9개의 수치는 대응 자료와 맞는다.

## 실제 확인 자료

- 공통: `review-brief.md`, `writer-brief.md`, `manifest.json`, 상위 `calico-follow-up-outline.md`, 지정된 두 SKILL.md와 easy-read-guide, verifier 역할 지침.
- HTML: manifest에 지정된 51~56편 여섯 파일 전체. PNG: calico-51/peer-verification, calico-52/capture-summary, calico-53/mtu-boundary·pmtud-feedback, calico-54/matrix·keepalive, calico-55/receiver·conntrack, calico-56/matrix.
- 51: README, commands.json, verified.json, netns·link·route·proxyarp·neighbor·ping·cleanup 원문, `sources/dataplane_linux.go`와 plugin 호출부. 특히 `07-pair-netns.txt`, `14-pair-app0-netns.txt`, `14-pair-app1-netns.txt`, `08-pair-links.txt`, `17-peer-link.txt`, `18-peer-statistics.txt`, `19-host-route.txt`, `20-pod-route-proxyarp.txt`, `21-reach-pod.txt`, `22-neighbours-after.txt`, `25-cleanup-check.txt`.
- 52: README, commands.json, environment.json, capture-map.json, analysis.json 전체, 캡처 해석 원문, 요청 결과. `worker1-eth0.pcap`은 읽기 전용 tcpdump로 추가 확인.
- 53: README, commands.json, 실제 MTU·1452/1453 ping 원문, `07-isolated-pmtud.txt`, blocked/allowed 패킷 해석 원문, cleanup 기록, 격리 실험의 설정/명령.
- 54: README, commands.json, results.json 전체, 정책 JSON, keepalive.jsonl·connection-summary.txt·keepalive-packets.txt, worker rules·server-endpoint-chain.txt, `calico-v3.33.0-endpoints.go`.
- 55: README, commands.json, pool·route·NAT 전후·규칙·수신 로그·conntrack 원문, 세 지점 패킷 해석 원문, `conntrack-read.py` 전체, cleanup 기록. cali.pcap·sender-eth0.pcap은 읽기 전용 tcpdump로 추가 확인.
- 56: README, facts.json, matrix.json 24개 전체, commands.json, resources.json 전체, EndpointSlice·blackhole 경로·route get·복구·cleanup·4노드 Ready 원문.

공식 문서와 버전 고정 소스도 대조했다.

- [Kubernetes NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/): 허용 규칙의 합집합, 양쪽 방향의 격리, 기존 연결에 대한 구현별 처리.
- [Calico MTU](https://docs.tigera.io/calico/latest/networking/configuring/mtu): underlay1500/IPIP1480, IPIP20·IPv4VXLAN50바이트, 경로 MTU 기준.
- [Calico outgoing NAT](https://docs.tigera.io/calico/latest/networking/configuring/workloads-outside-cluster): 모든 Calico pool 밖 목적지의 SNAT, 송신 노드에서 수행, 응답 역변환.
- [Calico architecture](https://docs.tigera.io/calico/latest/reference/architecture/overview): CNI·Felix·BIRD·confd의 구분. 구체 구현은 저장된 v3.33.0 소스와 함께 판단했다.

재현은 보관된 스크립트와 README의 개인 Lima 경로·노드 이름·캐시 이미지·sudo 도구 전제 아래 설명된다. 다른 환경에서 IP/장치 이름과 임시 포트가 동일하게 나온다고 보장하지 않는다. 이번 검수는 저장 증거와 글의 일치성을 확인했으며, 다른 커널·Calico 데이터플레인에서 같은 결과가 나온다는 별도 검증은 수행하지 않았다.
