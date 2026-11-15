# 57편: 애플리케이션 한 개 배포로 확인한 Kubernetes

## 실제 남겨둔 앱

- 주소: http://192.168.64.3:30057 (이 Mac과 실행 중인 Lima 실습 클러스터에서 접근)
- namespace: `app-capstone`
- Deployment: `deploy-board`, steady-state replicas=1
- Service: `deploy-board`, NodePort 30057 → Service 80 → container 8080
- 최종 APP_VERSION=v2. 앱 소스·Python 이미지 digest는 v1과 동일하며, 환경 변수 변경으로 Pod template rollout을 관찰했다. 이미지 빌드나 CI/CD 검증은 아니다.
- 화면은 2초마다 실제 `/api/info` HTTP 요청을 보내 버전·Pod·노드·IP·메모리 요청 수를 표시한다. 브라우저와 다른 실험 요청도 앱의 요청 수에 포함된다.

## 실험 결과

| 관찰 | 근거 | 결과 |
|---|---|---|
| 초기 Running/NotReady | `evidence/02*`, `03*`, `04*` | readyz503, 직접 api200, NodePort curl7 |
| Service 이름으로 호출 | `09-dns.json`, `10-internal-http.json`, `11-app-logs.json` | CoreDNS → ClusterIP → 다른 노드의 앱; requestID 동일 |
| readiness만 실패 | `12*`~`17*` | Running/restartCount0 유지, Endpoint 주소는 남고 ready/serving=false; 직접200, NodePort curl7 |
| v1→v2 구성 rollout | `rollout-requests.json` | 35초 관찰, 129건 모두HTTP200(v1=42,v2=87) |
| 앱 Pod 삭제·교체 | `replacement-requests.json` | 35초 관찰, 120건 중108건HTTP200,12건전송실패(rc7=8,28=3,56=1) |
| 교체 후 | `25*`~`30*`, `final-runtime.json` | 새 UID, 관찰된 IP변경; Service IP 유지; 임시 client 삭제; v2 정상 |

표본129건의 성공이 모든 트래픽·부하·장애에서 무중단을 보장하지 않는다. 요청은 응답 완료 후0.25초 쉬므로 정확히4RPS가 아니다. snapshot의 여러 API 조회는 원자적이지 않다. timeline은 Mac 관찰 시각이며 API 조건 시각·VM 로그와 인과나 정밀 지연을 단정하지 않는다. readiness는 방화벽이 아니므로 직접 Pod 접근은 가능하다.

## 재현

`run.py`는 현재 namespace가 존재하면 덮어쓰기를 거부한다. 지금 남겨둔 앱에서 실행하면 의도적으로 중단된다.
새 실습 클러스터나 이 namespace를 정리하기로 결정한 뒤에 재현한다. 클러스터는 k8s-playground wrapper, four Linux nodes, Calico IPIP, NodePort로 접근 가능한 worker1 `192.168.64.3`를 전제로 한다. 환경이 다르면 run.py URL/client node와 Service nodePort를 조정한다.

```bash
python3 /path/to/application-57/run.py --lab-root /path/to/k8s-playground
```

스크립트는 현재 폴더의 `app.py`가 아니라 `application-v1.json`에 포함된 immutable ConfigMap 코드로 실행한다. 소스 수정 시 두 파일을 같이 갱신해야 한다. 사용한 앱 이미지는 digest로 고정되어 있다. 임시 BusyBox client는 관찰 후 삭제하지만 앱과 namespace는 남긴다.

실패 시 자동으로 namespace를 삭제하지 않는다. `touch /tmp/not-ready` 후 중단됐다면 해당 파일을 지워 readiness를 복구하고 상태를 확인한다. 이 실험은 해당 namespace의 앱만 바꾸며 기존 monitoring/default 등의 workload는 변경하지 않는다.

## 산출물과 검수

- `evidence/`: 원본 명령·응답 JSON, 관찰 timeline, HTTP 표본, runtime/netns/route 정보. 실제 성공 실행은 2026-11-15 00:07:23~00:09:22 KST. 첫 listener 대기 race를 수정한 이전 실패 시도는 playground에 별도로 보존하며 이 글의 표본에 합산하지 않는다.
- `captures/`: 이미지로 렌더링한 원자료 발췌. 01은 실제 브라우저 화면의 별도 텍스트 캡처라 요청 수/시각은 PNG와 조금 다를 수 있다. 02/03은 저장 출력을 터미널 형태로 렌더링한 이미지이며 화면 녹화가 아니다.
- `manifest.json`: 최종 HTML 제목·경로.
- `verify.py`: 원본 표본·상태·소유 관계 및 HTML/CSS/SVG/이미지 검증.
- `reviews/`: 독립4관점검수, 별도 사실관계 감사, 수정결과.
- `mask-value-review.json`: 개인 Lima IP, resourceVersion, netns inode, UID/시각의 정확한 오탐 판정. 회사·인증 정보는 허용하지 않는다.
- `preview.py`: 원본 HTML을 바꾸지 않고 unpublished raw 이미지 URL만 로컬 경로로 바꾸어 제공한다.

```bash
python3 labs/devops/k8s-study/application-57/verify.py
python3 labs/devops/k8s-study/application-57/preview.py
# http://127.0.0.1:18768/__post__/57
```

커밋·push·티스토리 발행·Notion 반영은 수행하지 않았다.
