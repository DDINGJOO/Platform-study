# 51~56편 독립 검수 1차: 독자 관점

판정: **수정 필요**. 결함 **1건(R1)**. 차단 0건, 별도 확인 필요 0건.

1~2년차 개발자가 각 글을 처음 읽는 조건으로 여섯 HTML의 본문·명령·표·SVG 라벨·캡션·재현 링크를 모두 읽었다. 실행 위치, 네임스페이스와 장치 구분, 주소·오류 해석, 측정과 추론의 경계에 집중했다. 글·코드·클러스터는 수정하지 않았다.

## R1 — 수정 필요: 52편의 핵심 비교 값에 뜻이 빠져 있다

- 파일: `posts/CS/DevOps/k8s-study/52_52편 - 다른 노드의 파드까지 패킷은 어떻게 갈까, Calico IPIP를 tcpdump로 보기.html`
- 위치: 56행 용어 상자, 74행 TTL 첫 등장, 97·125·129·142행의 대조 결과.
- 근거: 56행 상자 제목은 `5-tuple과 TCP 시퀀스 번호`지만 본문은 5-tuple과 SYN만 정의한다. `TCP 시퀀스 번호와 IP ID도 맞춰`라고 사용 방법만 설명하고 두 값이 무엇인지는 설명하지 않는다. 74행에는 정의 없이 `TTL은 출발 쪽 64에서 local 쪽 63으로 줄었어요`가 나오며, 이후 표에서는 `remote SYN TTL`과 64→63→62가 주요 관측값이 된다. 글 전체에 TTL의 의미를 풀어 주는 문장은 없다.
- 독자 영향: 주소와 포트가 같은 것은 이해해도, 왜 시퀀스 번호·IP ID를 추가로 맞추는지와 TTL 감소가 무엇을 뜻하는지 독자가 구분하기 어렵다. 특히 TTL을 지연 시간이나 캡슐화 자체가 바꾼 값으로 읽을 수 있다. 이 값들은 부수적인 약어가 아니라 글의 중심인 ‘각 캡처에서 같은 SYN을 대조한다’는 근거다.
- 구체적 수정안: 기존 용어 상자에 두 문장을 더한다. 예: `TCP 시퀀스 번호는 TCP 바이트 흐름에서의 위치를 나타내요. 이번에는 첫 SYN의 번호를 비교했고, IPv4 헤더의 식별값인 IP ID도 보조 대조에 사용했어요.` 74행 첫 TTL에는 `TTL(라우터를 거칠 때 줄어드는 IPv4 전달 한도)`처럼 짧은 풀이를 붙인다. 이후 등장마다 설명을 반복하거나 새 절·상자를 늘릴 필요는 없다. IP ID 하나만으로 패킷의 동일성을 보장한다고 바꾸지 않는다.

## 편별 확인 결과

| 편 | 판정 | 독자 관점에서 확인한 사항 |
|---|---|---|
| 51 | 통과 | Kubernetes namespace와 Linux netns, Pod eth0와 호스트 cali를 구분한다. worker1에서 실행하는 nsenter와 PID 조회의 관계가 보인다. ifindex·peer 값, proxy ARP, /32와 /26의 경로 우선순위를 설명한다. route get과 실제 ping 결과를 구분한다. |
| 52 | R1 수정 필요 | 캡처 지점과 장치를 먼저 구분하고 tunl0의 내부 패킷과 eth0의 외부 IPIP 헤더를 나눈다. proto 80·TCP 포트80·IP 프로토콜4를 구별한다. 목적지 Pod eth0를 직접 캡처하지 않은 범위를 명시한다. 핵심 패킷 필드의 뜻만 보완하면 된다. |
| 53 | 통과 | 실제 Calico 경로의 MTU 확인과 별도 Linux netns의 PMTUD 장애 실험을 분리한다. 1452+8+20=1480과 MTU1300 이후 TCP 데이터1248의 계산을 풀어 준다. 오류와 curl 업로드 수치의 한계, ICMP 차단 제거 전후를 설명한다. 명령의 노드·네트워크 위치가 드러난다. |
| 54 | 통과 | ingress·egress, 선택자와 허용 합집합, DNS UDP/TCP를 실제 성공·차단 결과로 설명한다. 기존 연결12회에 정책 전 첫 요청이 포함됨을 밝힌다. 노드 Python을 Pod netns에서 실행한 점과 마지막 규칙 스냅샷의 관측 시점을 구분한다. |
| 55 | 통과 | 목적지가 worker2 호스트이며 인터넷 전체를 검증한 것이 아님을 명확히 한다. Calico pool 바깥이라는 의미, SNAT와 MASQUERADE, 주소·포트 변환, conntrack original/reply 방향을 연결한다. NAT 규칙 카운터만으로 개별 요청을 단정하지 않는다. |
| 56 | 통과 | 같은 curl7을 서로 다른 두 장애로 보여 주고 오류6·7·28을 한 줄씩 풀이한다. `exit/http`와 HTTP000의 뜻, targetPort·EndpointSlice·listen·ClusterIP를 설명한다. blackhole의 `Invalid argument`와 실제 통신 실패를 구분한다. 동일 증상만으로 원인을 단정하지 않는다. |

## 재현 경로·그림 확인

- 여섯 글의 실습·원자료 링크와 `51`~`56/README.md`의 실행 설명을 읽었다. Python 실행 위치, 개인 Lima 노드 및 이미지 캐시 등 전제, 스크립트의 LAB 경로 조정, 전용 자원과 정리 범위를 확인했다. 캡처는 저장 출력 렌더링이라는 설명과 원자료 경로가 있다.
- 초기 의심인 ‘스크립트가 개인 LAB 경로를 쓰므로 외부 독자가 시작할 수 없다’는 차단 지적은 기각한다. 각 실습 README에 경로 조정 안내가 있고 상위 `labs/devops/k8s-study/README.md`에 공개 `k8s-playground` 저장소와 `./lab up` 진입 경로가 있다. 공개 반영 전 GitHub 링크가 아직 제공되지 않는 상태를 원자료 누락으로 세지 않았다.
- 여섯 글의 SVG 라벨·화살표·캡션을 본문과 함께 읽었다. 특히 52편의 같은 노드 그림은 local eth0를 경로 설명에만 포함하고 직접 캡처하지 않았다고 표시한다. 다른 노드 그림은 cali→tunl0→양쪽 노드 eth0→tunl0→cali 순서를 읽을 수 있다. 저장된 `preview-checks/52-desktop.png`에서도 해당 그림 라벨을 확인했다. 전 편·전 뷰포트의 렌더링 검증을 수행했다고 주장하지 않는다.

## 읽은 자료

- `review-brief.md`, `writer-brief.md`, `manifest.json`, `calico-follow-up-outline.md`.
- 설치된 `~/.codex/agents/verifier.toml`.
- `.claude/skills/blog-post-pipeline/SKILL.md`, `.claude/skills/tistory-sketch-post/SKILL.md`, 해당 `references/easy-read-guide.md`.
- manifest의 51~56편 HTML 전체.
- `labs/devops/k8s-study/README.md`, `calico-51-56/51`~`56/README.md`와 재현 스크립트의 실행 진입·LAB 경로 부분.
- `preview-checks/52-desktop.png`.

이 검수는 독해와 재현 안내의 적절성에 대한 판정이다. 실험 재실행이나 전 편 프로토콜 사실관계의 독립 실측은 수행하지 않았다.
