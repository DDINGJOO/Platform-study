# 51편 실험·집필 근거

2026-11-14 KST. 실험 namespace `calico-blog-51`, worker1에 일반 Pod pair(앱 2개)와 hostNetwork Pod host(앱 1개)를 만들었다. 임시 Pod만 생성·삭제했으며 노드·Calico 설정은 변경하지 않았다.

## 재현

개인 Lima 실습 저장소에 `/Users/dding/orca/workspaces/k8s/tang/lab`가 있는 환경에서 `python3 experiment.py`를 실행한다. 다른 경로에서는 스크립트 LAB 상수를 환경에 맞춰 바꾼다. 호스트 Python 3, Lima, VM의 sudo/crictl/ip/nsenter/ethtool이 필요하다. VM worker1에 busybox:1.36.1 캐시가 있어 imagePullPolicy=Never를 사용했다. 메모리·CPU를 제한하고 서비스 계정 토큰 마운트를 끈다. 전용 namespace 이름을 사용하며 다른 자원을 건드리지 않는다. 이 스크립트는 실험 자료를 같은 디렉터리에 새로 쓰므로 기존 실행 자료를 보존하려면 복사본에서 실행한다.

## 확인한 사실

- sandbox PID 232563, app0 PID 232590, app1 PID 232625의 netns가 모두 net:[4026532560]으로 같았다. 호스트와 hostNetwork Pod는 net:[4026531840]으로 같았다. PID·인덱스·netns inode는 이 실행의 값이다.
- Pod eth0 ifindex 3/link_index 64와 호스트 cali0cbfd12677e ifindex 64/link_index 3을 양방향으로 대조하고 ethtool peer_ifindex=3을 확인했다. 양쪽 장치 종류는 veth였다.
- Pod 주소는 10.244.194.79/32, MTU 1480이었다. 내부에는 default via 169.254.1.1과 그 주소의 link 경로가 있었다.
- 호스트 cali의 MAC은 ee:ee:ee:ee:ee:ee였고 proxy_arp=1, forwarding=1이었다. 통신 뒤 Pod의 이웃 테이블에서도 169.254.1.1은 같은 MAC이었다. ARP 패킷 자체는 캡처하지 않았다.
- 호스트 ip route get이 해당 cali 장치를 선택했다. 별도 ping은 2/2 성공했다. 이것은 노드→해당 Pod ICMP 범위의 확인이다.
- cleanup에서 해당 namespace 삭제를 기다린 뒤 NotFound를 확인했다. 이후 링크 목록에 실험 veth가 없음을 render-summary.py가 검증한다. 다른 담당 실험이 동시에 존재할 수 있으므로 노드 전체의 링크 개수 동일성을 주장하지 않는다.

## 원문과 검증

`commands.json`은 37개 명령의 시각·명령·종료 코드·stdout/stderr를 보관한다. 36개는 종료 코드 0, 삭제 후 namespace 조회 1개는 의도한 NotFound로 종료 코드 1이다. `resources.json`, `pod-summary.json`, `verified.json`과 개별 번호 txt를 대조한다. CRI inspect의 전체 민감 필드는 저장하지 않고 PID만 선택한다.

`render-summary.py`는 저장된 관측으로 `capture-peer-summary.txt`를 생성한다. 라이브 조회가 아니다. term-shot.py --from으로 그 출력을 터미널 모양 이미지 `images/calico-51/peer-verification.png`에 렌더링했다. 실제 터미널 창을 촬영한 이미지는 아니다. 원본 출력을 변조하거나 재측정한 것처럼 표현하지 않는다.

스크린샷 텍스트는 마스킹 검사 통과 후 렌더링했다. 기사 본문은 `mask-check.py --allow .../51/mask-allow.txt <article>`로 통과했다. allow의 IP는 개인 Mac Lima의 실습 주소이며, 긴 숫자 두 개는 같은 커널의 netns inode다. 회사 주소·자격증명이 아니다. 공통 .mask-allow는 수정하지 않았다. GitHub 토큰·AWS 키·조직 식별자·회사 내부 URL은 사용하지 않았다.

`validation.json`: h2 6개, 용어 박스 6개, SVG 3개 XML/태그/중복 id 검증, 이미지 1개 로컬 존재, 템플릿 CSS 동일, 엠대시 없음. Python py_compile도 통과했다. 별도 리뷰·사실 감사는 통합 담당에게 요청한다. 게시하지 않았으므로 raw/main 이미지와 실습 링크는 커밋·푸시 전에는 공개 경로에 존재하지 않을 수 있다.

## 외부 자료

본문의 Linux man-pages, Kubernetes Pod networking, CNI 규약, Calico 구성 요소 문서를 웹으로 확인했다. 설치 버전의 CNI 코드 두 파일은 `sources/`에 URL·수집 시각·해시와 함께 보관했다. 생성 시점 코드와 현재 장치 관측을 대조했을 뿐 실행 중 어느 프로세스가 경로를 작성했는지 이 실험에서 추적한 것은 아니다. BIRD/Felix 중단은 하지 않았다. 30·34·43편의 기존 결과를 이번 실험과 구분해 연결했다.
