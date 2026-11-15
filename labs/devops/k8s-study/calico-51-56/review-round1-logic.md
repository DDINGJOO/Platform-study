# 51~56편 독립 퇴고 1라운드: 논리

판정: **통과**. 차단 0건, 수정 필요 0건, 확인 필요 0건. 본문·표·SVG 라벨·캡션의 논리 정합성을 검수했다. 이 보고서는 별도 사실 감사와 형식·렌더링 검사를 대체하지 않는다.

## 편별 확인

| 편 | 확인한 핵심 논리 | 근거와 판정 |
|---|---|---|
| 51 | netns·veth 식별 → 경로 선택 → 실제 통신을 서로 다른 증거로 연결하는가 | `verified.json`의 netns·양쪽 링크 대조와 별도 ping을 나누어 설명한다. `ip route get`을 전달 성공의 증거로 쓰지 않는다. 생성 시점 CNI와 지속 관리 Felix, BGP 정보 교환과 커널 전달을 분리한다. 통과. |
| 52 | 같은 노드/다른 노드 비교와 캡슐화/NAT 구분이 본문·도식·표에서 일치하는가 | `analysis.json`은 여덟 지점별 기록이며 본문은 동일 연결의 주소·포트·seq·IP ID를 대조한다. 라우팅 조회의 `src`를 전달 패킷의 출발지 변환으로 오독하지 않는다. 내부 Pod 주소 유지와 외부 노드 헤더 추가가 일치한다. 통과. |
| 53 | 실제 Calico 한도 측정과 격리 PMTUD 장애 재현을 섞는가 | 실제 Pod DF ping의 로컬 거절과 새 Linux 3netns의 중간 MTU 장애를 도입·3절·6절에서 분리한다. `isolated-pmtud.sh`는 동일 경로/MTU에서 ICMP 3/4 차단만 제거하며, 본문은 새 TCP 연결 및 PMTU 캐시 학습을 명시한다. 통과. |
| 54 | 정책 합집합·방향별 AND·기존/신규 연결의 인과 설명이 일치하는가 | `results.json` 17행과 `run.py`의 실행 순서가 설명과 일치한다. 첫 HTTP 응답 이후 deny를 적용하고 별도 신규 연결을 검사한다. 12회 중 정책 전 첫 요청을 포함한다고 명시한다. 최종 규칙 스냅샷을 deny 직후 카운터라고 쓰지 않는다. 통과. |
| 55 | NAT 지점과 수신기 범위를 구분하고 응답 역변환을 설명하는가 | 수신기는 worker2 호스트로 명확히 한정하며 공인 인터넷/상위 NAT와 분리한다. cali↔양쪽 eth0 및 original/reply tuple의 변환이 본문·도식에서 일치한다. 카운터 22→23을 단독 인과 증거로 쓰지 않는다. 통과. |
| 56 | 요청 비교로 조사 구간을 좁히는 것과 단일 원인 확정을 구분하는가 | `matrix.json`의 targetPort 오류와 대상 부재가 모두 curl 7이며 EndpointSlice로 구분된다는 전개가 일치한다. 정책 차단·DNS 오타도 대조와 복구로 구분한다. 같은/다른 노드 서버가 서로 다른 Pod라는 한계를 적고, blackhole lookup 실패를 IPAM 미할당 증거로 쓰지 않는다. 통과. |

## 반례를 검토하고 기각한 의심

- **L-C1, 51편:** 장치·경로 조회만으로 생성 프로세스나 전달 성공을 입증했다는 의심은 기각한다. 4절은 조회와 ping의 근거를 나누고 5절은 코드·기존 실험과 이번 관측을 구분한다. ARP 패킷을 캡처했다고도 쓰지 않는다.
- **L-C2, 52편:** `ip route get`의 tunnel IP 출발지와 실제 Pod 출발지 불일치는 모순이 아니다. 본문이 로컬 발신 조회와 포워딩 패킷을 명시적으로 나눈다. 도식의 도착 Pod eth0는 직접 캡처하지 않았다는 범위도 적는다.
- **L-C3, 53편:** tunl0 `nopmtudisc`인데 DF/ICMP 장애를 Calico 터널의 실제 동작으로 단정했다는 의심은 기각한다. 해당 경계와 격리 후반 실험의 차이를 반복 없이 필요한 위치에서 명시한다. HTTP `uploaded=65536`과 원격 수신 완료도 구분한다.
- **L-C4, 54편:** HTTP 12회 전체를 정책 적용 후의 성공으로 계산했다는 의심은 기각한다. 5절은 첫 요청이 정책 전임을 명시하고, 수집 스크립트는 첫 응답→apply→신규 요청 검사 순서를 보장한다. 시계 차이를 적용 지연으로 계산하지 않는다.
- **L-C5, 54편:** Kubernetes 정책 합집합을 Calico 자체 Deny/order/tier에도 적용했다는 의심은 기각한다. 표준 API와 자체 API를 별도 콜아웃에서 구분한다.
- **L-C6, 55편:** 다른 노드 주소를 인터넷 외부 수신기라고 표현했다는 의심은 기각한다. 도입·1절·5절·요약에서 Pod 풀 밖인 같은 클러스터 노드라는 관측 경계를 유지한다. NAT 비활성화 비교는 미실행으로 명시한다.
- **L-C7, 56편:** curl 7을 반드시 RST/connection refused라고 판정하거나 빈 IP lookup으로 IPAM 미할당을 단정했다는 의심은 기각한다. 2절과 5절에서 각각 해당 추론을 명시적으로 제한한다.

위 항목은 수정 지적이 아니라 기각한 검토 기록이다. 변경 요청 ID는 없다.

## 직접 읽은 자료

- `manifest.json`에 지정된 51~56편 HTML 전체. SVG의 text 라벨·본문·캡션을 포함한다.
- 공통 `review-brief.md`, `writer-brief.md`, `../calico-follow-up-outline.md`.
- `blog-post-pipeline`, `tistory-sketch-post` 스킬 및 easy-read-guide.
- 각 편의 `README.md` 전체.
- 51편 `verified.json` 구조와 본문이 연결하는 netns/peer/통신 근거.
- 52편 `analysis.json` 구조, 본문 전체 캡처 표와 헤더 발췌.
- 53편 `isolated-pmtud.sh`의 netns 구성·MTU·sysctl·offload·ICMP 규칙 변경·cleanup 부분.
- 54편 `run.py`의 baseline·동일 HTTPConnection·정책 적용·신규 요청·DNS 질의 순서, `results.json` 17행.
- 55편 `verification.json`, 본문 original/reply 및 SNAT 대응.
- 56편 `matrix.json` 24행 중 각 장애/복구 단계, `resources.json`의 실제 readinessProbe 정의.

글·실험 코드·공통 파일을 수정하지 않았으며 클러스터 실험을 재실행하지 않았다. 파일 내용에 대한 퇴고이며 별도 pcap 전수 재분석·라이브 환경 재검증은 수행하지 않았다.
