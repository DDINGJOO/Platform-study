# 52편: 같은 노드와 다른 노드의 IPIP 패킷 실측

실행: 2026-11-14 23:34 KST. 개인 Lima Kubernetes 실습 클러스터의 전용 namespace `calico-blog-52`에서만 Pod 세 개를 만들었다. 기존 경로·전역 정책·BIRD·노드 설정은 변경하지 않았다. 현재 namespace는 삭제되어 있다.

## 실행 및 파일

```bash
python3 labs/devops/k8s-study/calico-51-56/52/experiment.py
python3 labs/devops/k8s-study/calico-51-56/52/analyze-pcap.py
```

실험 스크립트의 `LAB` 경로는 개인 Mac의 실습 저장소다. 다른 환경에서는 해당 경로와 노드 이름을 맞춰야 한다. 재실행은 같은 디렉터리의 결과 파일을 갱신하므로 기존 증거를 보존하려면 디렉터리를 복사한 뒤 실행한다. 기존 namespace가 있으면 덮어쓰거나 삭제하지 않고 거절한다. 관측 당시 실행한 뒤, 이 소유권 보호 조건을 추가했다. 변경한 것은 이 보호 조건이며 패킷·관측 원문은 그대로다.

- `manifest.json`: 생성한 Namespace와 curl/nginx Pod 세 개의 명세. 각각 nodeName 고정, imagePullPolicy Never, 작은 자원 제한, ServiceAccount 토큰 자동 마운트 금지.
- `commands.json`: 명령 51개, 실행 시각·종료 코드·stdout/stderr. 종료 코드 0은 41개, 1은 namespace 사전 부재·정리 후 부재 확인 2개, 124는 정상적인 10초 tcpdump 종료 8개다. 실제 명령은 동시 실행했고 기록 순서는 명령 완료 순서일 수 있다.
- `pods.json`, `environment.json`: 생성한 Pod 배치·IP, host veth 경로, 샌드박스 PID, IPPool, 호스트 NIC 주소·offload 조회 결과.
- `local-request.txt`, `remote-request.txt`: 실제 curl 결과. 모두 HTTP 200이다.
- `capture-map.json`: 여덟 지점의 노드·인터페이스·netns 여부·BPF 필터.
- `*.pcap`: 실제 pcap 8개. snaplen 256이므로 큰 HTTP 응답 본문 전체는 보관하지 않았다.
- `*.txt`: 노드의 tcpdump `-nn -tttt -vvv -S -r`로 읽은 원문. `capture-summary.txt`만 분석 스크립트가 출력한 집계 표다.
- `analysis.json`: 표준 라이브러리로 pcap의 IPv4/TCP 헤더를 읽고 추출한 SYN 정보와 연결별 패킷 수.
- `validation.json`: 담당 HTML의 태그·SVG·CSS·이미지·시리즈 검사 및 패킷 분석 검증 결과.
- `mask-allow.txt`: 자동 마스킹 검사에서 남은 개인 실습 값의 판정 근거. 공통 `.mask-allow`는 담당자가 수정하지 않았다.
- `sha256.json`: 원문과 코드·이미지의 파일 무결성 확인용. 실행 시점의 진위나 실험 인과관계 자체를 보증하지 않는다.

## 핵심 관측

| 대상 | client | local nginx | remote nginx |
|---|---|---|---|
| Pod IP | 10.244.194.75 | 10.244.194.78 | 10.244.126.10 |
| Node | worker1 | worker1 | worker2 |
| 노드 쪽 veth | cali0e224c51a15 | calid971ba37c65 | calic93d2b3627d |

- 같은 노드 TCP `client:45252 → local:80`은 client netns eth0·client cali·local cali에서 각각 12개 관찰됐다.
- 다른 노드 TCP `client:45253 → remote:80`은 client netns eth0·client cali·worker1 tunl0·양쪽 노드 eth0·worker2 tunl0·remote cali에서 각각 12개 관찰됐다.
- 다른 노드의 첫 SYN은 각 지점에서 sequence `3184915459`, 내부 IP ID `3100`이었다. 내부 TTL은 client eth0에서 64, worker1 tunl0에서 63, remote cali에서 62였다.
- 양쪽 노드 eth0에서는 outer `192.168.104.3 → 192.168.104.4`, protocol 4, IP 길이 80 안에 해당 Pod SYN, protocol 6, IP 길이 60이 들어 있었다. SYN-ACK와 응답은 바깥 노드 주소가 반대였다.
- 노드 eth0의 전체 pcap에는 실험 밖 IPIP 트래픽도 들어 있다(worker1 26개, worker2 21개). 본문과 이미지의 12는 client Pod 주소·포트로 골라 낸 실험 연결의 패킷 수다. 전체 파일 수로 오독하지 않는다.
- 노드별 시계에 어긋남이 있어 캡처 시각 차이를 전송 지연으로 쓰지 않았다. 동일 연결 판단은 주소·포트·TCP seq·IP ID로 했다.
- 출발지 가상 장치의 체크섬은 incorrect, 노드 eth0와 도착 cali에서는 correct였다. 완성 시점 차이와 맞는 관측이나 정확한 커널 함수까지 입증한 것은 아니다.
- 여덟 캡처 모두 tcpdump의 커널 드롭 카운터는 0이었다. 이 수치로 클러스터 전체의 무손실을 주장하지 않는다.

## 캡처 이미지

`posts/CS/DevOps/k8s-study/images/calico-52/capture-summary.png`는 `capture-summary.txt`를 term-shot.py의 `--from`으로 렌더링한 이미지다. 창을 직접 촬영한 것이 아니다. 원문은 실제 pcap 분석 결과이며 이미지 속 숫자를 바꾸지 않았다. 생성 시각은 23:36 KST이고 패킷 관측 시각 23:34와 구분한다.

```bash
~/.local/share/tistory-uploader/venv/bin/python \
  .claude/skills/blog-post-pipeline/assets/term-shot.py \
  --from labs/devops/k8s-study/calico-51-56/52/capture-summary.txt \
  --cmd 'python3 labs/devops/k8s-study/calico-51-56/52/analyze-pcap.py' \
  --source labs/devops/k8s-study/calico-51-56/52/analysis.json \
  --title 'Calico IPIP: eight capture points' \
  -o posts/CS/DevOps/k8s-study/images/calico-52/capture-summary.png
```

스크린샷 텍스트에는 IP·긴 시퀀스 번호를 넣지 않아 term-shot 기본 마스킹을 통과했다. 본문의 개인 실습 IP, TCP sequence와 timestamp 옵션 숫자는 자동 검사상 오탐 후보이며 별도 파일에 판정 이유를 남겼다. 회사 자원·토큰·Secret·kubeconfig를 수집하지 않았다.

## 범위와 출처

IPv4 IPIP Always인 현재 환경의 단일 실행이다. 같은 노드 요청이 IPIP 캡처에 없었다는 것은 이 관측 구간의 결과다. 도착 Pod 내부 eth0는 직접 캡처하지 않았다. BIRD와 Felix 중 누가 경로를 썼는지에 대한 인과관계는 이번 캡처로 새로 입증하지 않았다.

- https://docs.tigera.io/calico/latest/networking/configuring/vxlan-ipip (열람 시 Calico 3.33 문서)
- https://docs.tigera.io/calico/latest/reference/architecture/data-path
- https://www.rfc-editor.org/rfc/rfc2003.html
- https://docs.kernel.org/networking/checksum-offloads.html

글은 초안 로컬 HTML이며 커밋·푸시·발행하지 않았다. 본문 raw 이미지 링크와 자료 링크는 main에 반영되어야 외부에서 열리므로 발행 전에 통합 확인한다.
