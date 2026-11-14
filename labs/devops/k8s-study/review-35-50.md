# 35~50편 작성·검토 기록

2026-11-14 · 원고 작성·검토 완료 · 티스토리 비공개 등록 완료

이전 세션은 35~49편 작성 뒤 검토하던 중 중단됐다. 저장된 대화와 현재 파일을 대조한 뒤 50편을 작성하고 35~49편의 사실 확인·문장 교정·교차 검수를 마쳤다. 아래 링크에서 16편을 확인할 수 있다. 실험 출력과 실행 도구는 [원자료 목록](README.md)에 정리했다.

## 글 목록

| 편 | 원본 HTML | 티스토리 |
|---|---|---|
| 35 | [쿠버네티스 구성 요소들은 누가 누구에게 어떤 프로토콜로 연결할까](../../../posts/CS/DevOps/k8s-study/35_35%ED%8E%B8%20-%20%EC%BF%A0%EB%B2%84%EB%84%A4%ED%8B%B0%EC%8A%A4%20%EA%B5%AC%EC%84%B1%20%EC%9A%94%EC%86%8C%EB%93%A4%EC%9D%80%20%EB%88%84%EA%B0%80%20%EB%88%84%EA%B5%AC%EC%97%90%EA%B2%8C%20%EC%96%B4%EB%96%A4%20%ED%94%84%EB%A1%9C%ED%86%A0%EC%BD%9C%EB%A1%9C%20%EC%97%B0%EA%B2%B0%ED%95%A0%EA%B9%8C.html) | [비공개 /759](https://dding-shark.tistory.com/759) |
| 36 | [API 서버는 왜 파드로 떠 있고 매니페스트 플래그는 각각 무엇을 정할까](../../../posts/CS/DevOps/k8s-study/36_36%ED%8E%B8%20-%20API%20%EC%84%9C%EB%B2%84%EB%8A%94%20%EC%99%9C%20%ED%8C%8C%EB%93%9C%EB%A1%9C%20%EB%96%A0%20%EC%9E%88%EA%B3%A0%20%EB%A7%A4%EB%8B%88%ED%8E%98%EC%8A%A4%ED%8A%B8%20%ED%94%8C%EB%9E%98%EA%B7%B8%EB%8A%94%20%EA%B0%81%EA%B0%81%20%EB%AC%B4%EC%97%87%EC%9D%84%20%EC%A0%95%ED%95%A0%EA%B9%8C.html) | [비공개 /760](https://dding-shark.tistory.com/760) |
| 37 | [마스터 노드에도 일반 파드를 올릴 수 있을까, taint와 toleration](../../../posts/CS/DevOps/k8s-study/37_37%ED%8E%B8%20-%20%EB%A7%88%EC%8A%A4%ED%84%B0%20%EB%85%B8%EB%93%9C%EC%97%90%EB%8F%84%20%EC%9D%BC%EB%B0%98%20%ED%8C%8C%EB%93%9C%EB%A5%BC%20%EC%98%AC%EB%A6%B4%20%EC%88%98%20%EC%9E%88%EC%9D%84%EA%B9%8C%2C%20taint%EC%99%80%20toleration.html) | [비공개 /761](https://dding-shark.tistory.com/761) |
| 38 | [etcd는 데이터를 어떻게 쌓고 왜 지워도 파일이 줄지 않을까](../../../posts/CS/DevOps/k8s-study/38_38%ED%8E%B8%20-%20etcd%EB%8A%94%20%EB%8D%B0%EC%9D%B4%ED%84%B0%EB%A5%BC%20%EC%96%B4%EB%96%BB%EA%B2%8C%20%EC%8C%93%EA%B3%A0%20%EC%99%9C%20%EC%A7%80%EC%9B%8C%EB%8F%84%20%ED%8C%8C%EC%9D%BC%EC%9D%B4%20%EC%A4%84%EC%A7%80%20%EC%95%8A%EC%9D%84%EA%B9%8C.html) | [비공개 /762](https://dding-shark.tistory.com/762) |
| 39 | [캐시가 늦어도 쿠버네티스는 왜 꼬이지 않을까, watch 캐시와 410·409](../../../posts/CS/DevOps/k8s-study/39_39%ED%8E%B8%20-%20%EC%BA%90%EC%8B%9C%EA%B0%80%20%EB%8A%A6%EC%96%B4%EB%8F%84%20%EC%BF%A0%EB%B2%84%EB%84%A4%ED%8B%B0%EC%8A%A4%EB%8A%94%20%EC%99%9C%20%EA%BC%AC%EC%9D%B4%EC%A7%80%20%EC%95%8A%EC%9D%84%EA%B9%8C%2C%20watch%20%EC%BA%90%EC%8B%9C%EC%99%80%20410%C2%B7409.html) | [비공개 /763](https://dding-shark.tistory.com/763) |
| 40 | [etcd 3.7에서는 백업과 복원을 어떻게 할까](../../../posts/CS/DevOps/k8s-study/40_40%ED%8E%B8%20-%20etcd%203.7%EC%97%90%EC%84%9C%EB%8A%94%20%EB%B0%B1%EC%97%85%EA%B3%BC%20%EB%B3%B5%EC%9B%90%EC%9D%84%20%EC%96%B4%EB%96%BB%EA%B2%8C%20%ED%95%A0%EA%B9%8C.html) | [비공개 /764](https://dding-shark.tistory.com/764) |
| 41 | [스케줄러는 어떤 파드를 집어 가고 바인딩은 무엇을 쓸까](../../../posts/CS/DevOps/k8s-study/41_41%ED%8E%B8%20-%20%EC%8A%A4%EC%BC%80%EC%A4%84%EB%9F%AC%EB%8A%94%20%EC%96%B4%EB%96%A4%20%ED%8C%8C%EB%93%9C%EB%A5%BC%20%EC%A7%91%EC%96%B4%20%EA%B0%80%EA%B3%A0%20%EB%B0%94%EC%9D%B8%EB%94%A9%EC%9D%80%20%EB%AC%B4%EC%97%87%EC%9D%84%20%EC%93%B8%EA%B9%8C.html) | [비공개 /765](https://dding-shark.tistory.com/765) |
| 42 | [컨트롤러 매니저에는 무엇이 들어 있고 Service 컨트롤러는 왜 없을까](../../../posts/CS/DevOps/k8s-study/42_42%ED%8E%B8%20-%20%EC%BB%A8%ED%8A%B8%EB%A1%A4%EB%9F%AC%20%EB%A7%A4%EB%8B%88%EC%A0%80%EC%97%90%EB%8A%94%20%EB%AC%B4%EC%97%87%EC%9D%B4%20%EB%93%A4%EC%96%B4%20%EC%9E%88%EA%B3%A0%20Service%20%EC%BB%A8%ED%8A%B8%EB%A1%A4%EB%9F%AC%EB%8A%94%20%EC%99%9C%20%EC%97%86%EC%9D%84%EA%B9%8C.html) | [비공개 /766](https://dding-shark.tistory.com/766) |
| 43 | [쿠버네티스는 왜 컨테이너가 아니라 파드를 띄우고 pause 컨테이너는 왜 있을까](../../../posts/CS/DevOps/k8s-study/43_43%ED%8E%B8%20-%20%EC%BF%A0%EB%B2%84%EB%84%A4%ED%8B%B0%EC%8A%A4%EB%8A%94%20%EC%99%9C%20%EC%BB%A8%ED%85%8C%EC%9D%B4%EB%84%88%EA%B0%80%20%EC%95%84%EB%8B%88%EB%9D%BC%20%ED%8C%8C%EB%93%9C%EB%A5%BC%20%EB%9D%84%EC%9A%B0%EA%B3%A0%20pause%20%EC%BB%A8%ED%85%8C%EC%9D%B4%EB%84%88%EB%8A%94%20%EC%99%9C%20%EC%9E%88%EC%9D%84%EA%B9%8C.html) | [비공개 /767](https://dding-shark.tistory.com/767) |
| 44 | [노드당 파드 110개는 어디서 나온 숫자일까](../../../posts/CS/DevOps/k8s-study/44_44%ED%8E%B8%20-%20%EB%85%B8%EB%93%9C%EB%8B%B9%20%ED%8C%8C%EB%93%9C%20110%EA%B0%9C%EB%8A%94%20%EC%96%B4%EB%94%94%EC%84%9C%20%EB%82%98%EC%98%A8%20%EC%88%AB%EC%9E%90%EC%9D%BC%EA%B9%8C.html) | [비공개 /768](https://dding-shark.tistory.com/768) |
| 45 | [쿠버네티스는 왜 kubelet에서 Docker를 떼어 냈을까, CRI와 dockershim](../../../posts/CS/DevOps/k8s-study/45_45%ED%8E%B8%20-%20%EC%BF%A0%EB%B2%84%EB%84%A4%ED%8B%B0%EC%8A%A4%EB%8A%94%20%EC%99%9C%20kubelet%EC%97%90%EC%84%9C%20Docker%EB%A5%BC%20%EB%96%BC%EC%96%B4%20%EB%83%88%EC%9D%84%EA%B9%8C%2C%20CRI%EC%99%80%20dockershim.html) | [비공개 /769](https://dding-shark.tistory.com/769) |
| 46 | [쿠버네티스 API는 REST인데 CRI와 etcd는 왜 gRPC일까](../../../posts/CS/DevOps/k8s-study/46_46%ED%8E%B8%20-%20%EC%BF%A0%EB%B2%84%EB%84%A4%ED%8B%B0%EC%8A%A4%20API%EB%8A%94%20REST%EC%9D%B8%EB%8D%B0%20CRI%EC%99%80%20etcd%EB%8A%94%20%EC%99%9C%20gRPC%EC%9D%BC%EA%B9%8C.html) | [비공개 /770](https://dding-shark.tistory.com/770) |
| 47 | [kube-proxy는 왜 iptables와 IPVS를 거쳐 nftables로 왔을까](../../../posts/CS/DevOps/k8s-study/47_47%ED%8E%B8%20-%20kube-proxy%EB%8A%94%20%EC%99%9C%20iptables%EC%99%80%20IPVS%EB%A5%BC%20%EA%B1%B0%EC%B3%90%20nftables%EB%A1%9C%20%EC%99%94%EC%9D%84%EA%B9%8C.html) | [비공개 /771](https://dding-shark.tistory.com/771) |
| 48 | [쿠버네티스는 왜 etcd와 Raft를 골랐고 Kafka는 왜 ZooKeeper를 버렸을까](../../../posts/CS/DevOps/k8s-study/48_48%ED%8E%B8%20-%20%EC%BF%A0%EB%B2%84%EB%84%A4%ED%8B%B0%EC%8A%A4%EB%8A%94%20%EC%99%9C%20etcd%EC%99%80%20Raft%EB%A5%BC%20%EA%B3%A8%EB%9E%90%EA%B3%A0%20Kafka%EB%8A%94%20%EC%99%9C%20ZooKeeper%EB%A5%BC%20%EB%B2%84%EB%A0%B8%EC%9D%84%EA%B9%8C.html) | [비공개 /772](https://dding-shark.tistory.com/772) |
| 49 | [노드 하트비트는 왜 Node 객체에서 Lease로 빠졌을까](../../../posts/CS/DevOps/k8s-study/49_49%ED%8E%B8%20-%20%EB%85%B8%EB%93%9C%20%ED%95%98%ED%8A%B8%EB%B9%84%ED%8A%B8%EB%8A%94%20%EC%99%9C%20Node%20%EA%B0%9D%EC%B2%B4%EC%97%90%EC%84%9C%20Lease%EB%A1%9C%20%EB%B9%A0%EC%A1%8C%EC%9D%84%EA%B9%8C.html) | [비공개 /773](https://dding-shark.tistory.com/773) |
| 50 | [노드 장애 판단의 50초와 300초는 왜 그 값일까](../../../posts/CS/DevOps/k8s-study/50_50%ED%8E%B8%20-%20%EB%85%B8%EB%93%9C%20%EC%9E%A5%EC%95%A0%20%ED%8C%90%EB%8B%A8%EC%9D%98%2050%EC%B4%88%EC%99%80%20300%EC%B4%88%EB%8A%94%20%EC%99%9C%20%EA%B7%B8%20%EA%B0%92%EC%9D%BC%EA%B9%8C.html) | [비공개 /774](https://dding-shark.tistory.com/774) |

## 업로드 결과

신규 35~50편 16개를 티스토리에 비공개로 등록했고 기존 32~34편 수정도 반영했다. 글 번호가 만들어진 뒤 시리즈의 앞뒤 편 링크를 다시 갱신했다. [자동 업로드 작업](https://github.com/DDINGJOO/Platform-study/actions/runs/43603771170)이 성공했고, 저장된 32~50편 19개의 매니페스트 해시·제목·카테고리·태그가 현재 렌더 결과와 일치함을 확인했다. 새 글 공개 범위는 모두 private다.

이미지 65개는 GitHub main의 원본 주소에서 HTTP 200, 이미지 응답 형식, 파일 크기 일치를 확인했다. 글별 업로더 검사에서도 SVG 개수·본문 길이·태그·공개 범위를 통과했다.

## 주요 교정

- **35~39편:** 포트만으로 프로토콜을 판단하던 설명, 컨트롤러 ServiceAccount 총수와 접미사별 집계의 혼동, CRI·스트리밍·TLS 범위, APF exempt의 적용 범위를 고쳤다. 클라우드 초기화 taint의 제거 주체와 etcd 메모리 색인·디스크 데이터의 차이를 바로잡았다. WatchList 기본 경로와 LIST-WATCH 대체 경로를 구분하고 DNS 실험의 관찰 범위를 명시했다.
- **40~42편:** 복원 시작부터 readyz 복귀까지 약 45초인 관측 구간을 연속 장애 시간으로 단정하지 않도록 했다. 스케줄러 대상·큐 재시도·전역 메트릭의 해석 범위를 좁혔다. 컨트롤러별 Role/ClusterRole과 공용 클라이언트의 용도를 구분하고 `spec.replicas`를 객체 수가 아닌 설정된 파드 수로 설명했다.
- **43~46편:** 컨테이너 종료 후 약 0.76초는 CreateContainer 시작, 약 0.80초는 StartContainer 성공, 1.3초는 Ready 관측으로 구분했다. 110개 파드 실험은 기존 4개에 pause 파드 106개를 더한 결과로 고쳤다. HTTP/2 watch와 gRPC 스트리밍의 범위 및 과거 선택 이유를 정밀하게 설명했다.
- **47~49편:** Kafka 3.3의 실제 발표일과 신규 클러스터 지원 범위, etcd NOSPACE에서 읽기·삭제가 허용되는 점, 2멤버 복제와 3멤버 장애 내성의 차이를 바로잡았다. fsync·commit 수치와 Lease 24회/revision 증가 104는 각각 해당 관측 구간으로 한정했다. 40·41·48편에 반복된 informer 설명도 39편과 일치시켰다.
- **50편:** 50초·300초·55%·50대의 기원을 원문과 고정 버전 소스로 설명했다. 단일 kubelet 정지 실험의 객체 생성(+72/+342초)과 Running 최초 관측(+74.7/+344.3초)을 구분했다. 워커 세 대의 동시 정지에서 NoExecute 공급 제한과 이미 시작된 파드 축출 타이머가 별도로 동작한 결과를 담았다.

32·33편에는 이전 세션에서 시작한 객체 검증 순서 교정을 유지했다. mutating 어드미션 뒤 객체 검증(422), validating 어드미션(403), 저장 순서다. 33·34편을 포함한 인접 시리즈 박스를 5항목으로 맞추고 `tistory-series.json`에 35~50편 제목을 추가했다. 34편 본문과 공통 스타일은 그대로다.

현재 [공식 resourceVersion 계약](https://kubernetes.io/docs/reference/using-api/api-concepts/#resource-versions)은 1.35부터 같은 API 그룹·리소스 종류의 정수 순서 비교를 허용한다. 검토 중 나온 오래된 opaque 전면 금지 제안은 적용하지 않았다. 저장소 구현과 다른 리소스 종류 간 차분의 한계를 함께 적었다.

## 검증 결과

작성·수정 담당과 다른 검토자가 35~39, 40~42, 43~46, 47~49, 50편을 각각 재검수했다. 해당 범위에서 수정 필수 잔여 항목은 없었다. 한국어 문장 교정은 별도로 수행했다.

| 검사 | 결과 |
|---|---|
| 32~50편 HTML/SVG 구조 | 19개 통과 |
| HTML 및 35~50편 원자료 마스킹 | HTML 19개 + 원자료 109개 통과 |
| 35~50편 자산 | PNG 65개 존재·로드 확인, SVG 51개 텍스트 경계 확인 |
| 공통 스타일 | 검사한 19개 모두 34편 스타일 블록과 바이트 동일 |
| 브라우저 | 1280px·390px에서 16편씩 총 32화면, 이미지 누락·페이지 가로 넘침·SVG 경계 초과 없음 |
| 실행 도구 구문 | Bash 47개 `bash -n`, Python 1개 AST 구문 검사 통과 |
| 공유 파일 | 제목 매핑 JSON 파싱, 35~50편 5항목 시리즈 박스 확인 |

HTML 구조는 `tistory-sketch-post`의 `validate_html.py`, 마스킹은 `blog-post-pipeline`의 `mask-check.py`로 검사했다. 마스킹 예외는 실제 관측값으로 확인한 고정 숫자만 이유와 함께 추가했다. 브라우저에서는 외부 이미지 URL을 같은 저장소의 로컬 PNG로 치환해 확인했다. 35·36편의 긴 인라인 코드와 주소 목록은 본문 스타일 블록을 바꾸지 않고 줄바꿈을 보완했다. 원자료 스크립트는 이 검토에서 실행하지 않았다.

## 해석 범위와 상태

- 수치는 저장된 각 실험 시점의 관측이다. 다른 시각의 카운터·컨트롤러 목록·파드 수를 하나의 동시 측정으로 합치지 않았다.
- 47편 IPVS 제거 일정은 KEP·고정 소스와 게시 예정 블로그 원고가 달라 출처와 불일치를 본문에 남겼다. 미래 일정을 확정 사실로 처리하지 않았다.
- 유휴 pause 파드 실험은 실제 앱의 성능 보장이 아니다. 50편의 kubelet 정지는 VM 전원·네트워크 단절, FullDisruption, 여러 zone 실험을 대신하지 않는다.
- 원고·검토 기록·실험 자료를 커밋해 main에 푸시하고 티스토리 비공개 등록까지 완료했다. Notion 쓰기는 수행하지 않았다. 실습 저장소와 이전 세션 기록은 읽기 전용으로 다뤘다.
