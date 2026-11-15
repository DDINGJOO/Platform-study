# Calico 해부 51~56편

2026-11-14 개인 Lima Kubernetes 실습을 바탕으로 작성한 후속 글이다. Kubernetes v1.37.2, containerd 2.4.1, Calico v3.33.0, Linux 기본 데이터플레인과 IPIP Always 구성을 기준으로 한다.

| 편 | 본문 HTML | 실험·원문·재현 절차 |
|---|---|---|
| 51 | [파드의 eth0 반대편에는 무엇이 있을까, Calico의 netns와 veth 추적](../../../../posts/CS/DevOps/k8s-study/51_51편%20-%20파드의%20eth0%20반대편에는%20무엇이%20있을까,%20Calico의%20netns와%20veth%20추적.html) | [51/README.md](51/README.md) |
| 52 | [다른 노드의 파드까지 패킷은 어떻게 갈까, Calico IPIP를 tcpdump로 보기](../../../../posts/CS/DevOps/k8s-study/52_52편%20-%20다른%20노드의%20파드까지%20패킷은%20어떻게%20갈까,%20Calico%20IPIP를%20tcpdump로%20보기.html) | [52/README.md](52/README.md) |
| 53 | [작은 요청은 되는데 큰 요청은 왜 멈출까, Calico MTU와 PMTUD](../../../../posts/CS/DevOps/k8s-study/53_53편%20-%20작은%20요청은%20되는데%20큰%20요청은%20왜%20멈출까,%20Calico%20MTU와%20PMTUD.html) | [53/README.md](53/README.md) |
| 54 | [NetworkPolicy를 적용했는데 왜 어떤 연결은 계속될까](../../../../posts/CS/DevOps/k8s-study/54_54편%20-%20NetworkPolicy를%20적용했는데%20왜%20어떤%20연결은%20계속될까.html) | [54/README.md](54/README.md) |
| 55 | [파드가 밖으로 나갈 때 출발지 IP는 어디서 바뀔까, Calico NAT와 conntrack](../../../../posts/CS/DevOps/k8s-study/55_55편%20-%20파드가%20밖으로%20나갈%20때%20출발지%20IP는%20어디서%20바뀔까,%20Calico%20NAT와%20conntrack.html) | [55/README.md](55/README.md) |
| 56 | [파드 통신 장애는 어디부터 볼까, Calico 장애를 구간별로 좁히기](../../../../posts/CS/DevOps/k8s-study/56_56편%20-%20파드%20통신%20장애는%20어디부터%20볼까,%20Calico%20장애를%20구간별로%20좁히기.html) | [56/README.md](56/README.md) |

## 검증한 내용

- 51편: 샌드박스·앱의 netns 일치, hostNetwork 비교, veth 양쪽 인덱스 교차 대조, 호스트→Pod ICMP 왕복.
- 52편: 같은 노드·다른 노드 HTTP 요청, 8지점 pcap, IPIP 외부/내부 주소와 동일 TCP SYN 대조.
- 53편: 실제 Pod의 MTU·DF ping 경계, 별도 3개 netns에서 PMTUD 오류 통지 차단·해제 비교. 이 격리 실험은 실제 Calico 경로 장애와 구분한다.
- 54편: 표준 Kubernetes NetworkPolicy 17개 관측, ingress/egress·허용 합집합·DNS UDP/TCP·기존 TCP와 새 연결 비교.
- 55편: Pod·hostNetwork·노드 요청을 통제 수신기에서 비교, pcap·NAT 규칙·conntrack tuple로 SNAT 확인. 관측 경계는 VM 노드 사이이며 인터넷 전체가 아니다.
- 56편: curl 24개 관측으로 targetPort 오류·대상 부재·정책·이름 오류를 비교하고 복구. 같은 오류 코드만으로 원인을 확정하지 않는다.

각 디렉터리의 commands.json에는 명령과 시각·종료 코드·출력이 있다. 예상한 오류를 정상 실행과 구분하며 표·그림·캡처의 파생 과정을 담당 README에 기록했다. pcap은 제한된 전용 실험 연결을 캡처한 원본이다. 관련 소스와 해시는 각 편 자료에 있다.

## 로컬 미리보기와 검사

저장소 루트에서 실행한다.

```sh
python3 labs/devops/k8s-study/calico-51-56/preview.py
# http://127.0.0.1:18767

python3 labs/devops/k8s-study/calico-51-56/validate.py
```

미리보기는 아직 원격에 없는 raw GitHub 이미지 경로를 로컬 경로로 바꿔 제공한다. HTML 원본 파일은 변경하지 않는다. 다른 환경의 재현에는 각 편 README의 전제와 스크립트 경로를 확인한다. 현재 PID·IP·장치 인덱스는 다시 조회해야 한다.

- `validation.json`: HTML 중첩, 템플릿 CSS, SVG XML·개수, 중복 ID, 용어·절 개수, 이미지·alt, tags/lead, 엠대시 검사.
- `preview-checks/desktop.json`, `mobile.json`: Orca 브라우저의 이미지 로드·도식 라벨 범위·화면 너비 검사. 스크린샷은 같은 디렉터리에 보관했다.
- `mask-review.json`: 여섯 HTML에 일반·조직 목록을 적용한 검사 결과. 개인 실습 IP와 netns/TCP 식별자는 원문을 대조해 .mask-allow에 허용 근거를 추가했다. 조직 문자열이나 자격증명을 허용한 것은 아니다.
- `review-round1-*.md`: 집필자와 분리한 네 관점의 검수 보고서. 최종 처리와 별도 독립 사실 감사는 [검수·감사 최종 처리](review-resolution.md)에 정리했다.

## 자료의 범위

터미널 형태 이미지는 저장된 실제 원문 또는 원문에서 계산한 표를 렌더링한 것이다. 터미널 창 직접 촬영이나 실시간 대시보드라고 표기하지 않는다. 편별로 관측 조건·마스킹·발췌 여부를 적었다.

실험은 전용 namespace, 고유 포트와 격리 netns를 사용했다. 기존 워크로드·Calico 설정·공유 호스트 경로를 수정하지 않았다. 각 편은 생성한 자원을 정리하고 청소 결과를 기록했다. 이 자료의 실험은 정책·라우팅의 모든 버전과 데이터플레인에 대한 보장이 아니다.

커밋·푸시·업로더 실행은 이 집필 작업에 포함하지 않았다. raw 이미지와 실습 자료 링크는 원격에 반영되기 전에는 열리지 않을 수 있다. 로컬 미리보기에서는 확인할 수 있다.

## 최종 상태

51~56편 HTML 6개, 스케치 SVG 16개, 실행 결과 이미지 9장, pcap 14개를 보관했다. 패널 지적 2건 반영·변경부 재검·별도 사실 감사까지 잔여 수정 0건이다. 감사 HTML 해시가 최종 본문과 일치한다. 검증 범위와 미확인 범위는 보고서와 본문에 명시했다.
