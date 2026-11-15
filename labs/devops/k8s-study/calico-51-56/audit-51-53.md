# 51–53편 독립 사실 감사

## 결과

현재 최종 HTML을 저장된 명령 원문, 패킷 파일, 설치 버전 소스, 공식 문서와 독립 대조했다. **수정 필요 사항 및 잔여 지적 0건**이다. 이전 작성자·4관점 검수의 통과 판정은 증거로 사용하지 않았다.

긍정적인 핵심 주장 30개 묶음은 확인했다. 별도로 점검한 미검증 범위 3개는 확인 불가이나, 본문이 이미 명시적으로 한정하여 사실 오류나 과장으로 분류하지 않았다. 이 수치는 문장 전체의 개수가 아니라 아래 표의 감사 단위 개수다.

| 범위 | 확인 | 불일치 | 확인 불가 | 과장 |
|---|---:|---:|---:|---:|
| 51편 | 10 | 0 | 1 | 0 |
| 52편 | 10 | 0 | 1 | 0 |
| 53편 | 10 | 0 | 1 | 0 |
| 합계 | **30** | **0** | **3** | **0** |

## 감사 대상과 고정본

저장소 기준 경로는 `/Users/dding/orca/workspaces/Platform-study/k8s-study`다. 아래 해시는 현재 HTML 원본 바이트에서 직접 계산했다.

| 편 | HTML 경로 | SHA256 |
|---|---|---|
| 51 | `posts/CS/DevOps/k8s-study/51_51편 - 파드의 eth0 반대편에는 무엇이 있을까, Calico의 netns와 veth 추적.html` | `8b148e411ab1b729916dcdecc9baa927fa9e445aeb460058657834dce2fb25a1` |
| 52 | `posts/CS/DevOps/k8s-study/52_52편 - 다른 노드의 파드까지 패킷은 어떻게 갈까, Calico IPIP를 tcpdump로 보기.html` | `660fa5381faadd0135da51194b19fd5306d664ec75f5b0f38169a209da4c22dc` |
| 53 | `posts/CS/DevOps/k8s-study/53_53편 - 작은 요청은 되는데 큰 요청은 왜 멈출까, Calico MTU와 PMTUD.html` | `799fa034f2eab4c2850e2bdae4af5e4e3395db15fe0d48a846f93624252d7b7c` |

판정은 저장된 이번 실행의 증거에 대한 것이다. 추가 클러스터 실험, 현재 클러스터 상태 조회, 본문 수정, 자식 에이전트 생성은 하지 않았다.

## 읽은 자료와 검증 방식

- 공통: `audit-brief.md`, `manifest.json`, `writer-brief.md`, `review-brief.md`, 설치된 researcher 역할 지침과 blog-post-pipeline의 독립 사실 감사 절. 이전 검수 결과는 판정 근거에서 제외했다.
- 51편: 최종 HTML 전체, `51/README.md`, `commands.json`, 생성·CRI PID·netns·링크·주소·경로·이웃·통신·삭제 원문, 실험 스크립트, `verified.json`과 캡처용 요약, `sources/dataplane_linux.go`, `sources/plugin.go`, `sources/manifest.json`.
- 52편: 최종 HTML, `52/README.md`, `commands.json`, `environment.json`, `pods.json`, `manifest.json`, 실험·분석 스크립트, 여덟 `.pcap` 및 대응 `.txt`, 요청 출력, 분석·캡처 요약 자료.
- 53편: 최종 HTML 전체, `53/README.md`, `commands.json`, `01`–`10`번 원문, `isolated-pmtud.sh`, 수집·캡처 생성 스크립트, `blocked.pcap`, `allowed.pcap`, 대응 패킷 해석 텍스트와 캡처용 발췌.
- 실제 PNG 4개를 열어 확인했다: `images/calico-51/peer-verification.png`, `images/calico-52/capture-summary.png`, `images/calico-53/mtu-boundary.png`, `images/calico-53/pmtud-feedback.png`. HTML 내 SVG의 텍스트·주소·수치도 원문과 대조했다.
- 52·53편 pcap은 작성자의 분석 JSON만 신뢰하지 않고 별도 일회성 Python 파서로 직접 읽었다. pcap 레코드, Ethernet/Raw IPv4 링크 타입, IP 길이·프로토콜·주소·TTL·ID, 중첩 IPIP, TCP 포트·시퀀스·페이로드 길이, ICMP type/code 및 next-hop MTU를 추출했다. 기존 분석 스크립트는 실행하지 않았다.
- 51편의 버전 고정 공식 소스 두 파일을 다시 가져와 저장 사본과 바이트 단위로 비교했다. 둘 다 일치했다. SHA256은 `dataplane_linux.go`가 `6a1e946bd2b68e20e624de2b543127ae210933ae1da7912713cc144543a3b79e`, `plugin.go`가 `020f047955e416006c199c64c415aab544695656a33834e056a361fa82318b4e`다.

## 51편 주장별 대조

아래 근거 경로는 공통 실험 디렉터리 `labs/devops/k8s-study/calico-51-56/` 기준이다.

| ID | 주장 | 직접 대조 근거 | 판정 |
|---|---|---|---|
| 51-01 | 일반 Pod의 sandbox와 앱 컨테이너 두 개가 같은 netns를 공유한다. | `51/07-pair-netns.txt`, `14-pair-app0-netns.txt`, `14-pair-app1-netns.txt`: PID 232563·232590·232625 모두 `net:[4026532560]`. PNG·SVG도 일치. | 확인 |
| 51-02 | hostNetwork Pod는 호스트 netns를 사용한다. | `07-host-netns.txt`, `14-host-app0-netns.txt`, `15-host-netns.txt`: 모두 `net:[4026531840]`. 일반 Pod의 inode와 구별됨. | 확인 |
| 51-03 | Pod eth0와 호스트 cali는 양방향 인덱스로 대응하는 veth다. | `08-pair-links.txt`: eth0 ifindex 3, link_index 64, kind veth. `17-peer-link.txt`: `64: cali0cbfd12677e@if3`. `18-peer-statistics.txt`: peer_ifindex 3. 단순 이름 유사성으로 판정하지 않음. | 확인 |
| 51-04 | Pod 주소는 `10.244.194.79/32`, MTU는 1480이다. | `09-pair-addresses.txt`의 eth0 주소·prefixlen·mtu 필드. netns 내 DOWN tunl0를 실제 전달 장치라고 서술하지 않음. | 확인 |
| 51-05 | Pod 기본 경로는 `169.254.1.1`이며 링크 범위 경로도 있다. | `10-pair-routes.txt`의 default·scope link 출력. v3.33.0 `dataplane_linux.go`의 gateway 경로 및 /32 주소 처리와 일치. | 확인 |
| 51-06 | host cali의 proxy_arp·forwarding 설정과 gateway 이웃 MAC이 설명을 뒷받침한다. | `20-pod-route-proxyarp.txt`: 둘 다 1. `22-neighbours-after.txt`: gateway MAC `ee:ee:ee:ee:ee:ee`; 호스트 링크 MAC과 같음. CNI 소스의 host MAC·sysctl 처리와 일치. ARP 패킷을 캡처했다는 주장은 없음. | 확인 |
| 51-07 | 호스트 route get은 cali를 고르며 실제 ICMP 전달은 별도로 확인했다. | `19-host-route.txt`: 목적지 cali0cbfd12677e, source 192.168.104.3. `21-reach-pod.txt`: 송신 2·수신 2·손실 0%. 본문은 조회와 전달 성공을 구별하고 다른 노드·모든 포트로 일반화하지 않음. | 확인 |
| 51-08 | CNI의 생성 구성, Felix의 지속 관리, BIRD/confd의 경로 정보·구성 처리, 커널의 전달 역할을 구별한다. | 버전 고정 CNI 소스의 DoNetworking·SetupRoutes 및 [Calico 구성 요소 공식 문서](https://docs.tigera.io/calico/latest/reference/architecture/overview). 이번 실험에서 BIRD/Felix를 중단했다는 주장은 없음. | 확인 |
| 51-09 | 37개 명령과 실제 원문이 보관되어 있고 캡처는 저장 자료를 렌더링한 것이다. | `commands.json` 직접 집계: 36개 exit 0, 삭제 확인 NotFound 1개. PNG 내용이 netns·링크 원문과 일치. 본문은 실시간 터미널 촬영이 아님을 명시. | 확인 |
| 51-10 | 전용 namespace 삭제 후 해당 veth도 없어졌다. | `24-cleanup.txt`: 삭제. `25-cleanup-check.txt`: NotFound. `26-host-links-clean.txt` 전체 링크 JSON에서 cali0cbfd12677e 부재. 단순 삭제 메시지만으로 완료 판정하지 않음. | 확인 |

## 52편 주장별 대조

| ID | 주장 | 직접 대조 근거 | 판정 |
|---|---|---|---|
| 52-01 | 실험은 IPIP Always·VXLAN Never 구성에서 같은 노드와 다른 노드의 Pod 직접 연결을 비교했다. | `52/environment.json`, `pods.json`, `manifest.json`, 요청 원문 및 `commands.json`. client `10.244.194.75`, local `.78`, remote `10.244.126.10`; 노드 `192.168.104.3`·`.4`. Service/DNS 경로와 혼동하지 않음. | 확인 |
| 52-02 | 여덟 캡처에서 local 연결은 세 지점 각 12개, remote 연결은 일곱 지점 각 12개다. | 여덟 pcap을 포트 45252·45253으로 독립 집계. local은 client-eth0/client-cali/local-cali, remote는 local-cali를 제외한 일곱 지점. 분석 표·PNG와 일치. | 확인 |
| 52-03 | 같은 remote SYN을 여러 관측 지점에서 대응시켰다. | 직접 해석한 5-tuple, TCP seq `3184915459`, inner IP ID `3100`, flags SYN과 inner 길이 60이 일치. 본문의 seq·IP ID·TTL 용어 설명도 해당 필드와 부합. | 확인 |
| 52-04 | 노드 eth0 구간에서 바깥 IP가 추가되고 내부 Pod 주소가 유지된다. | worker1/worker2 eth0 pcap: outer `.104.3 → .104.4`, proto 4, total 80; inner `10.244.194.75:45253 → 10.244.126.10:80`, proto 6, total 60. 바깥 헤더 20바이트. 본문 발췌·SVG와 일치. [RFC 2003](https://www.rfc-editor.org/rfc/rfc2003.html). | 확인 |
| 52-05 | 관측한 inner TTL은 출발 64 → 송신 tunl0/양쪽 eth0/수신 tunl0 63 → 수신 cali 62다. | 독립 pcap 파싱으로 각 캡처의 remote SYN TTL 확인. RFC 2003의 전달·역캡슐화 시 TTL 처리와 모순 없음. tunl0 관측은 outer 헤더가 없는 Raw IP임. | 확인 |
| 52-06 | route get의 source를 전달 중 Pod의 SNAT 결과로 해석하면 안 된다. | 조회 출력과 실제 pcap을 분리하여 대조. inner source는 캡처 전 구간에서 `.194.75`로 유지된다. 도식은 내부 헤더 전체의 불변을 주장하지 않고 Pod 주소 유지를 설명함. | 확인 |
| 52-07 | 일부 가상 장치의 incorrect TCP checksum만으로 손상 패킷 도착을 확정할 수 없다. | 동일 SYN은 client eth0/worker1 tunl0에서 incorrect, 양쪽 노드 eth0/remote cali에서 correct. [Linux checksum offload 문서](https://docs.kernel.org/6.8/networking/checksum-offloads.html)와 부합하며, 본문은 정확한 계산 함수까지 단정하지 않음. | 확인 |
| 52-08 | 캡처 시간·크기·지점의 한계를 명시한다. | 수집 명령의 10초 timeout·snaplen 256 확인. 호스트 간 시계 차이를 전달 지연으로 계산하지 않음. local Pod 내부 eth0는 직접 캡처하지 않았다는 문구가 SVG에도 있음. | 확인 |
| 52-09 | 8개 캡처의 kernel drop은 0이지만 전체 네트워크 무손실 보장은 아니다. | `commands.json`의 tcpdump stderr 8개 직접 확인. 51개 기록은 exit 0 41개, timeout exit 124 8개, 사전·사후 NotFound exit 1 2개. eth0 전체 패킷 수와 선택 연결 12개를 혼동하지 않음. | 확인 |
| 52-10 | 생성 namespace와 원격 임시 pcap을 정리했다. | 임시 pcap 8개에 대한 `sudo rm -f` 모두 exit 0. namespace 삭제 exit 0, 이후 조회 NotFound. 로컬 증거 pcap은 보관됨. 원격 파일 정리는 rm 성공 기록이 근거이며, 별도의 사후 ls 기록까지 있다고 확장하지 않음. | 확인 |

## 53편 주장별 대조

| ID | 주장 | 직접 대조 근거 | 판정 |
|---|---|---|---|
| 53-01 | 실제 Calico의 underlay MTU는 1500, Pod/tunl0 MTU는 1480이다. | `53/02-underlay-mtu.txt`, `03-tunnel-mtu.txt`, `04-pod-mtu.txt`. [Calico MTU 표](https://docs.tigera.io/calico/latest/networking/configuring/mtu)의 IPv4 IPIP 1500→1480과 일치. | 확인 |
| 53-02 | IPv4 옵션 없는 ping 데이터 1452는 inner 1480, outer 1500에 해당한다. | IPv4 20+ICMP 8+1452=1480, IPIP outer 20 추가=1500. SVG는 Ethernet 헤더가 계산 밖임을 명시. [ping 매뉴얼](https://man7.org/linux/man-pages/man8/ping.8.html), RFC 2003과 부합. | 확인 |
| 53-03 | 실제 Pod의 DF ping 1452는 2/2 응답, 1453은 로컬 MTU 검사에서 거절된다. | `06-ping-1452.txt`, `06-ping-1453.txt` 원문과 `mtu-boundary.png`. `local error: message too long, mtu=1480`를 상대 노드 드롭으로 바꾸지 않음. `-M do`의 커널 PMTU 검사 의미도 매뉴얼과 일치. | 확인 |
| 53-04 | PMTUD 실패 재현은 실제 Calico 경로의 장애 주입이 아닌 별도 Linux netns 실험이다. | `isolated-pmtud.sh`, `07-isolated-pmtud.txt`: cb53-src/rtr/dst, 양 끝 1500·라우터 송신 1300. 변경은 새 netns와 veth에 한정. 본문·SVG가 실제 Pod 측정과 별도 경로를 분리함. | 확인 |
| 53-05 | TCP MTU probing은 출발 실험 netns에서 끄고 새 veth의 TSO/GSO/GRO를 껐다. | 실행 원문·스크립트의 netns exec sysctl/ethtool 확인. `tcp_mtu_probing=0`의 의미는 [Linux 6.8 IP sysctl 문서](https://docs.kernel.org/6.8/networking/ip-sysctl.html)의 PLPMTUD 비활성화와 일치. 노드 전체 설정 변경으로 설명하지 않음. | 확인 |
| 53-06 | ICMP 3/4를 차단하면 작은 ping은 성공하지만 큰 요청은 관찰 시간 안에 끝나지 않는다. | `07-isolated-pmtud.txt`: 100바이트 ping 성공, 1400바이트 실패, curl exit 28/HTTP000/4.002032초. DROP 16에는 앞선 큰 ping도 포함됨을 본문이 명시. 4초를 TCP의 일반적인 장애 확정 시간으로 쓰지 않음. | 확인 |
| 53-07 | 차단 캡처에는 큰 데이터의 동일 시퀀스 재전송이 있고 MTU ICMP는 없다. | `blocked.pcap` 독립 파싱: IP 길이 1500·TCP payload 1448, seq `4286112550`의 상대 시각 약 0/0.21/0.62/1.43/3.10초. ICMP type 3/code 4는 0개. curl 오류 하나만으로 원인을 확정한 구조가 아님. | 확인 |
| 53-08 | ICMP 규칙 삭제 뒤 같은 1300 병목에서 HTTP200과 서버 수신 65536을 확인했다. | `07-isolated-pmtud.txt`: 해당 OUTPUT ICMP 규칙 삭제, `received=65536`, HTTP200, route cache MTU1300·expires599sec. 이후 ping1272 성공·1273 로컬 거절. curl의 uploaded만 수신 증거로 삼지 않음. | 확인 |
| 53-09 | ICMP 피드백 후 TCP가 1300에 맞게 패킷을 줄인다. | `allowed.pcap` 독립 파싱: ICMP3/4 next-hop MTU1300 10개, IP1300/TCP payload1248 50개. 20+32+1248=1300. 초기 IP1500 시도 10개도 존재하지만 본문은 피드백 이후의 조정을 설명하므로 모순 없음. MSS1460과 실제 timestamp 포함 payload1248을 구별함. | 확인 |
| 53-10 | 삭제 원문과 별도 조회가 실험 리소스 정리를 뒷받침한다. | `08-pod-cleanup.txt`·`09-namespace-absent.txt`: namespace 삭제/NotFound. cleanup 출력만 신뢰하지 않고 `10-netns-after.txt` 전체에서 cb53-src/rtr/dst 부재 확인. 기존 CNI netns가 남아 있어도 실험 netns 정리 주장에 대한 반례는 아님. `commands.json` 20개 중 exit0 17개, 예상 exit1 3개. | 확인 |

## 확인 불가이나 이미 적절히 한정한 범위

아래는 글이 입증했다고 주장하지 않는 경계다. 위의 긍정 주장 30개와 구분하여 누락 없이 기록한다.

| 범위 | 확인할 수 없는 사항 | 현재 본문의 처리 | 판정 및 조치 |
|---|---|---|---|
| 51편 | 이번 상태 조회에서 보인 개별 경로를 마지막으로 쓴 프로세스, BIRD/Felix 중단의 장애 효과 | `ip link`만으로 관리 프로세스를 알 수 없다고 설명하고, 생성 소스·구성 문서·이전 별도 실험을 구분한다. 이번에 중단 실험을 하지 않았다고 명시. | 확인 불가. 한정 적절, 수정 불필요. |
| 52편 | 미완성 TCP checksum을 정확히 어느 커널 함수/장치가 완성했는지 | 여러 캡처의 checksum 차이는 관측하되, 모든 offload 설정·커널 경로를 추적하지 않았으므로 함수까지 확정하지 않는다고 명시. | 확인 불가. 한정 적절, 수정 불필요. |
| 53편 | 실제 Calico underlay에 병목을 주입했을 때 outer DF·단편화·PMTUD가 어떻게 작동하는지 | 실제 tunl0의 nopmtudisc와 inner DF를 구별하고, 정상 경계 측정으로 바깥 단편화까지 검증하지 않았다고 명시. 장애 비교는 별도 Linux 실험으로 제한. | 확인 불가. 한정 적절, 수정 불필요. |

공통 한계: 원문과 pcap은 저장 당시 실행을 뒷받침한다. 독립 재실험이나 현재 시점 리소스 부재의 재확인은 하지 않았다. 이 한계는 저장 증거의 일관성 감사와 구별된다.

## 공식 출처

외부 동작은 검색 요약·제3자 블로그 대신 다음 원문을 직접 확인했다.

- [Calico v3.33.0 Linux CNI dataplane 소스](https://github.com/projectcalico/calico/blob/v3.33.0/cni-plugin/pkg/dataplane/linux/dataplane_linux.go), [CNI plugin 소스](https://github.com/projectcalico/calico/blob/v3.33.0/cni-plugin/pkg/plugin/plugin.go): 실제 저장 소스와 재수신 바이트·해시까지 동일.
- [Linux network_namespaces(7)](https://man7.org/linux/man-pages/man7/network_namespaces.7.html), [veth(4)](https://man7.org/linux/man-pages/man4/veth.4.html): netns의 자원 격리, veth pair와 peer 인덱스 해석.
- [Calico 구성 요소](https://docs.tigera.io/calico/latest/reference/architecture/overview), [overlay networking](https://docs.tigera.io/calico/latest/networking/configuring/vxlan-ipip), [MTU 설정](https://docs.tigera.io/calico/latest/networking/configuring/mtu): 열람 당시 3.33 문서. 역할 구분, 캡슐화 범위, IPIP MTU 표와 대조.
- [RFC 2003](https://www.rfc-editor.org/rfc/rfc2003.html): IP-in-IP의 outer/inner 구조, protocol4와 TTL 처리.
- [iputils ping 매뉴얼](https://man7.org/linux/man-pages/man8/ping.8.html): 데이터 길이와 `-M do`의 DF·커널 검사.
- [RFC 1191](https://www.rfc-editor.org/rfc/rfc1191.html), [RFC 2923](https://www.rfc-editor.org/rfc/rfc2923.html): ICMP 기반 IPv4 PMTUD와 black-hole 문제의 범위.
- [Linux 6.8 IP sysctl](https://docs.kernel.org/6.8/networking/ip-sysctl.html), [checksum offloads](https://docs.kernel.org/6.8/networking/checksum-offloads.html): PLPMTUD 설정값 및 캡처 지점에 따른 미완성 checksum 해석.

## 상대적으로 신뢰도가 낮은 편과 잔여 사항

**세 편 중 상대적으로 가장 신뢰도가 낮은 편은 53편**이다. 실제 Calico의 정상 MTU 측정과 별도 Linux의 실패 재현이라는 두 증거 체계를 연결하고, 실패 구간 pcap의 관측 위치도 출발지 쪽에 한정되기 때문이다. 이 선택은 글의 오류 판정이 아니다. 변경한 ICMP 규칙, 라우터 DROP 카운터, 출발지 재전송·ICMP 캡처, 정상화 후 서버 수신량이 서로 보완하고 본문도 두 환경을 구분하므로 현재 결론은 근거 범위 안에 있다.

정리 완료 주장도 삭제 메시지보다 사후 NotFound·장치 및 netns 목록을 우선하여 반례를 찾았으나 충돌을 발견하지 못했다. 캡처 이미지들은 요약·발췌 렌더링임을 밝히며 원문과 핵심 수치가 일치했다. 기존 검수의 무지적 결론을 그대로 승계한 것이 아니라 위 대조로 독립 재확인한 결과다.

**필수 수정 0건, 잔여 지적 0건.**
