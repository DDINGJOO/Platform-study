# 55편: Calico outgoing NAT 실측

2026-11-14 23:35 KST 실행. Kubernetes v1.37.2, Calico v3.33.0, worker1에서 worker2의 호스트 HTTP 수신기로 요청했다. 목적지는 Calico 풀 밖이지만 같은 개인 Lima 클러스터의 노드다. 공인 인터넷·Mac 상위 NAT의 관측 실험이 아니다.

## 실행과 격리

`python3 labs/devops/k8s-study/calico-51-56/55/run.py`

스크립트의 LAB은 개인 실습 저장소 `/Users/dding/orca/workspaces/k8s/tang/lab`을 가리킨다. 다른 환경에서는 경로·노드·목적지 주소를 바꿔야 한다. 사전 namespace 존재 검사 후 `calico-blog-55`와 worker1의 일반/hostNetwork curl Pod 두 개만 생성했다. 두 Pod는 service account token 자동 마운트를 끄고 캐시 이미지를 사용했다. worker2의 기존 포트를 점유하지 않는 임시 Python 서버는 25초, 세 tcpdump는 16초 제한으로 실행했다. 전역 NAT·정책·노드 경로·VM 설정은 바꾸지 않았다.

`finally`에서 전용 namespace 삭제 후 부재를 확인했다. worker2의 TCP 18555 리스너가 사라진 것도 확인했다. `90`~`92` 원문 참조. 서버와 캡처의 종료 코드 124는 의도한 timeout 만료다. 조회·생성·요청·정리 명령 18개는 모두 종료 코드 0이었다.

## 직접 확인한 결과

| 요청 | 송신 원래 주소 | worker2에서 관측한 원격 주소 | conntrack src_nat |
|---|---|---|---|
| 일반 Pod | 10.244.194.92:45555 | 192.168.104.3:7165 | true |
| hostNetwork Pod | 192.168.104.3:45556 | 192.168.104.3:45556 | false |
| 노드 셸 | 192.168.104.3:45557 | 192.168.104.3:45557 | false |

- 수신기: 192.168.104.4:18555. 세 HTTP 요청 경로는 `/pod`, `/hostNetwork`, `/node`.
- 일반 Pod의 호스트 veth: `cali31e758d2ea8`.
- cali와 worker1/worker2 eth0의 첫 SYN에서 TCP ISN 345155042와 TCP timestamp가 일치한다. cali에서는 Pod IP/45555, eth0에서는 노드 IP/7165였다. 반환 SYN-ACK도 eth0의 노드 목적지와 cali의 Pod 목적지로 대조했다.
- 실제 NAT 규칙은 NAT 대상 출발지 풀, 목적지 네트워크 풀의 부정 조건, MASQUERADE `--random-fully`다. IPPool은 natOutgoing=true이며 목적지가 이 풀 밖이다.
- cali-nat-outgoing 카운터 22→23은 보조 자료다. 공유 노드의 다른 요청을 배제한 전용 카운터가 아니므로 이 증가만으로 인과관계를 주장하지 않는다.
- 연결 추적 CLI와 `/proc/net/nf_conntrack`이 없어 `conntrack-read.py`로 nfnetlink에 읽기 전용 dump를 요청했다. 목적지 포트 18555의 IPv4 TCP 연결만 출력·저장했다. 설치·모듈 변경 없이 표준 Python 라이브러리를 사용했다.
- 일반 Pod conntrack original: 10.244.194.92:45555→192.168.104.4:18555; reply: 192.168.104.4:18555→192.168.104.3:7165. TCP 종료 뒤 조회했으므로 전체 상태 전이·정확한 타임아웃을 일반화하지 않는다.

## 자료

- `commands.json`: 명령 실행 시작 UTC 시각, shellquoted 명령, 종료 코드, stdout/stderr. Pod 응답·수신기 로그의 시각도 UTC다.
- `00`~`14`, `90`~`92`: 읽기 편한 명령 원문.
- `pods.json`, `receiver.py`: 실행한 자원·수신기 코드. 수신기는 노드 파일을 쓰지 않고 Python `-c`로 실행했다.
- `background-results.json`: timeout 서버·캡처의 명령과 종료 코드.
- `cali.pcap`, `sender-eth0.pcap`, `receiver-eth0.pcap`: 실험 포트로 제한한 패킷 원본. `.txt`는 Mac tcpdump로 읽은 결과이며 표시 시각은 KST다.
- `capture-receiver.txt`: 세 curl stdout을 순서대로 그대로 모은 파일.
- `capture-tuples.txt`: nfnetlink stdout 원문.
- `capture.py`: term-shot.py를 import하고 ROOT를 이 디렉터리로 지정해 **실험 전용** allowlist를 사용한 렌더링 도구. 공통 검사기·공통 .mask-allow를 바꾸지 않았다.
- `verification.json`: 명령 종료 코드·pcap 대조·정리·HTML 구조 검사 결과.
- `write-post.py`: 템플릿 그대로의 CSS와 원문 기반 본문 생성기.
- `sha256.json`: 파일 해시이며 실행 시점·인과관계를 보증하지 않는다.

## 캡처와 마스킹

`posts/CS/DevOps/k8s-study/images/calico-55/receiver.png`는 세 응답 원문, `conntrack.png`는 `capture-tuples.txt` 1~18행의 일반 Pod 연결을 term-shot.py로 렌더링했다. 직접 터미널 창을 촬영한 사진은 아니다. 두 이미지 모두 열어 숫자·내용을 확인했다.

term-shot 원본은 별도 allowlist 옵션이 없으므로 `capture.py`에서 로컬 ROOT를 사용했다. `.mask-allow`의 각 IP는 개인 Lima 노드·Pod·풀 주소이고 345155042는 패킷의 임시 TCP ISN이다. 회사 정보·조직 ID·자격증명이 아니다. 이 값은 NAT 전후 대조에 필요한 실습 주소이므로 보존했다. HTML 마스킹 검사에 같은 실험 allowlist를 명시하면 깨끗함으로 통과한다. 공통 예외 목록은 수정하지 않았다.

검사 명령:

```
python3 .claude/skills/blog-post-pipeline/assets/mask-check.py 'posts/CS/DevOps/k8s-study/55_55편 - 파드가 밖으로 나갈 때 출발지 IP는 어디서 바뀔까, Calico NAT와 conntrack.html' --allow labs/devops/k8s-study/calico-51-56/55/.mask-allow
```

HTML 검증: h2 5개, 용어 4개, 곡선 SVG 3개, 캡처 이미지 2개. 태그·SVG XML·중복 ID·템플릿 CSS·시리즈 표기·이미지 파일·엠대시 검사 통과. 글 작성자의 자체 검증이며 독립 리뷰·감사를 대신하지 않는다.

## 확인한 공식 자료

- Calico 3.33 outgoing NAT: https://docs.tigera.io/calico/latest/networking/configuring/workloads-outside-cluster
- IPPool: https://docs.tigera.io/calico/latest/reference/resources/ippool
- 설치 버전 Felix 규칙 생성 코드: https://github.com/projectcalico/calico/blob/v3.33.0/felix/rules/nat.go
- 커널 conntrack netlink 명세: https://docs.kernel.org/netlink/specs/conntrack.html
- Netfilter NAT의 새 연결 규칙 평가 설명: https://www.netfilter.org/documentation/HOWTO/NAT-HOWTO-5.html
- MASQUERADE와 random-fully 매뉴얼: https://man7.org/linux/man-pages/man8/iptables-extensions.8.html

NAT 비활성화·상위 NAT·eBPF 모드·다른 Calico 버전 비교는 이번에 수행하지 않았다. 글·스크린샷·자료를 커밋·푸시·발행하지 않았다. 다른 글과 공통 파일은 수정하지 않았다.
