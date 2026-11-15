# 53편: Calico MTU와 격리 PMTUD 실측

2026-11-14 23:35 KST. Lima VM 4대의 개인 실습 클러스터에서 측정했다. 글: `posts/CS/DevOps/k8s-study/53_53편 - 작은 요청은 되는데 큰 요청은 왜 멈출까, Calico MTU와 PMTUD.html`.

## 관측과 범위

| 실험 | 관측 | 근거 |
|---|---|---|
| 실제 Calico 경로 | worker1 eth0 MTU1500, tunl0와 임시 Pod eth0 MTU1480 | `02`~`04` 출력 |
| 실제 두 노드의 Pod 간 DF ping | 데이터1452 성공2/2, 1453 로컬 `message too long, mtu=1480` | `06-ping-1452.txt`, `06-ping-1453.txt` |
| 격리 Linux 3netns, 중간 egress MTU1300, ICMP3/4 DROP | 작은ping 성공, 큰ping 실패, TCP3way handshake와 HTTP헤더 ACK 뒤 IP길이1500 데이터 재전송. curl4초타임아웃 | `07-isolated-pmtud.txt`, `blocked.pcap`, `blocked-packets.txt` |
| 같은 격리 경로에서 ICMP3/4 DROP만 제거 | ICMP need-to-frag1300, IP길이1300/TCP데이터1248, 서버 `received=65536`, HTTP200, 경로PMTU1300 캐시 | `07-isolated-pmtud.txt`, `allowed.pcap`, `allowed-packets.txt` |

- 후반 장애 실험은 기존 Calico 터널에 MTU 장애를 넣은 실험이 아니다. 새로 만든 Linux netns의 경로다.
- 실제 tunl0는 `nopmtudisc`였다. 내부 DF와 외부 DF를 같다고 쓰지 않았으며 외부 단편화 실험으로 일반화하지 않았다.
- 격리 출발지의 `tcp_mtu_probing=0`, 실험용 veth의 TSO/GSO/GRO off를 통제했다. 기존 노드 인터페이스 offload는 바꾸지 않았다.
- `uploaded=65536`은 원격 수신 완료 증거가 아니다. 성공은 서버가 본문 전부를 읽은 뒤 보낸 `received=65536` 응답과 HTTP200으로 판단했다.
- DROP카운터16은 큰ping과 TCP 업로드를 함께 센 값이다. TCP만16회실패했다고 쓰지 않는다.
- 4초는 curl 관찰 한도다. TCP 자체의 고정 timeout이나 모든 설정에서의 영구 장애를 뜻하지 않는다.
- 순서번호 `4286112550:4286113998`의 재전송 시각은 최초12.774810초에서 약0.21,0.62,1.43,3.10초 후다. `blocked-packets.txt`에 원문이 있다.

## 재현·파일

`python3 run-experiment.py`는 실제 클러스터 도구 `/Users/dding/orca/workspaces/k8s/tang/lab`를 사용한다. 이 경로를 해당 Lima 실습 저장소에 맞춘다. 캡처 증거를 덮어쓰므로 재측정은 이 디렉터리의 별도 복사본에서 실행한다. `calico-blog-53`, `cb53-src/rtr/dst`, `/tmp/cb53-evidence`가 이미 있으면 기존 자원을 덮어쓰지 않도록 거절한다.

1. 전용 Kubernetes namespace와 pause Pod 두 개를 worker1/worker2에 생성하고 캐시된 이미지를 사용한다.
2. container PID를 조회해 `nsenter -n`으로 파드 네트워크에서 노드의 iputils ping을 실행한다.
3. worker1의 root bash로 `isolated-pmtud.sh`를 실행한다. sysctl/iptables/MTU는 새 netns 안에서만 바꾼다. 다른 노드 경로나 전역 정책은 변경하지 않는다.
4. 원격 pcap을 로컬로 보관한 뒤 해당 원격 임시 디렉터리를 제거한다. 서버와 tcpdump는 종료하고 Linux netns 세 개와 Kubernetes namespace를 정리한다.

`commands.json`은 바깥 호출 20개의 시작시각·명령·종료코드·stdout/stderr다. 17개는0이며 3개는 예상된1이다: 생성 전 namespace NotFound, 1453 ping 거절, 정리 후 namespace NotFound. `07` 내부의 probe 종료코드는 출력에 별도로 기록돼 있다. 원격 shell의 stdout과 stderr는 바깥 수집기에서 분리 저장하고 텍스트 파일에는 stdout 다음 stderr를 붙였으므로, 파일 끝의 curl/ping 오류를 시간순 마지막 이벤트로 읽지 않는다.

`blocked.pcap`, `allowed.pcap`은 출발지 실험 veth에서 `icmp or tcp port 18553` 필터로 캡처했다. `*-packets.txt`는 tcpdump `-K -nn -tttt -vv -S` 디코딩 결과다. 소스 캡처, 라우터 DROP카운터, 구성된 MTU와 전송 결과를 함께 해석했으며 모든 관측지점 캡처를 수행했다고 주장하지 않는다.

## 캡처와 마스킹

`prepare-captures.py`는 저장된 실제 출력의 행만 선택하고 행 번호를 `capture-line-map.json`에 보관한다. MTU화면의 대상 Pod IP는 `{대상 Pod IP}`로 치환한다. PMTUD화면은 원문 행을 발췌하고 DROP카운터의 공백만 정리한다. 본문 캡션에서 발췌·치환을 명시했다.

```sh
python3 prepare-captures.py
python3 /Users/dding/orca/Platform-study/.claude/skills/blog-post-pipeline/assets/mask-check.py capture-mtu.txt capture-pmtud.txt
```

텍스트 마스킹 검사 통과 후 `term-shot.py --from`으로 이미지2장을 생성했다. 실제 터미널 창 촬영이 아니라 저장 출력 렌더링이다. 이미지 위치는 `posts/CS/DevOps/k8s-study/images/calico-53/`이며 원문 정보는 이미지 바닥글에 있다.

실험에서 나온 `10.244.126.40`은 개인 클러스터의 임시 Pod IP이고 `192.0.2.0/24`, `198.51.100.0/24`는 격리 실습에 사용한 문서용 주소다. 회사 주소·자격증명·Secret·kubeconfig를 수집하지 않았다. 마스킹 도구가 `192.0.2.*`를 사설IP로 탐지하므로 최종 캡처에서는 해당 주소가 나오는 명령 줄을 발췌 대상에서 제외했다. 원문은 그대로 보관했다.

HTML의 실제 TCP 순서번호 두 개는 일반 숫자 탐지의 오탐이라 `mask-allow.txt`에 이유와 함께 등록했다. 공통 `.mask-allow`는 변경하지 않았다. `mask-check.py --allow mask-allow.txt <53편HTML> capture-mtu.txt capture-pmtud.txt`는 깨끗함이다.

## 검증과 청소

- 공통 검증기의 53편 결과: h2 6, 용어박스5, SVG3, 이미지2, CSS원본일치, HTML/SVG구조와 중복ID 검사 통과.
- 원문·pcap·성공/실패·청소9개 검사 통과. 결과는 `validation.json`이다.
- Python 소스 compile, `bash -n isolated-pmtud.sh` 통과.
- `08-pod-cleanup.txt`, `09-namespace-absent.txt`, `10-netns-after.txt`와07의 cleanup행에서 실험 자원 제거를 확인했다.
- 본문의 공식 문서 링크를 웹으로 확인했다: Calico3.33 MTU, iputils ping 매뉴얼, RFC1191, RFC2923, Linux6.8 IP sysctl.
- 커밋·푸시·발행은 수행하지 않았다. 이미지와 실습자료의 GitHub 링크는 저장소에 반영된 후 공개 주소에서 사용할 수 있다.
