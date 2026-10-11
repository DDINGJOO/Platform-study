# 배포 안전성 실습-3: 클러스터를 손으로 고치면 깃옵스가 되돌린다

kind 클러스터 하나에 Argo CD 와 실습용 git 서버(Gitea)를 띄우고, `apps/web`(Deployment·Service·ConfigMap)을
Argo CD Application 으로 동기화한다. 그 상태에서 다음을 잰다.

| 실험 | 명령 | 결과 파일 |
|---|---|---|
| selfHeal 을 끄면 손으로 바꾼 값이 남는지 | `lab.py selfheal-off` | `out/selfheal-off.txt` |
| `kubectl scale` 로 만든 드리프트를 selfHeal 이 되돌리는 시간, 반복하면 늘어나는 백오프 | `lab.py drift-scale` | `out/drift-scale-*.txt` |
| 무엇이 드리프트로 잡히나(라벨 추가, ConfigMap 수정, Deployment 삭제, 손으로 만든 리소스) | `lab.py drift-misc` | `out/drift-misc.txt` |
| git 에 푸시한 변경이 반영되는 시간. 폴링만 / 웹훅 | `lab.py git-change` | `out/git-change-poll.txt`, `out/git-change-webhook.txt` |
| git 에서 지운 Service: prune 끔 / 켬 | `lab.py prune` | `out/prune.txt` |
| PreSync 훅과 sync wave 의 적용 순서와 간격 | `lab.py waves` | `out/waves.txt` |
| 없는 이미지 태그를 커밋했을 때와 `git revert` 로 되돌리는 흐름 | `lab.py bad-commit` | `out/bad-commit.txt` |

## 돌리기

```bash
cd labs/devops/ds-03-gitops
./scripts/up.sh                         # kind 클러스터 ds-03, gitea, Argo CD, 저장소 시드, Application 생성 (5~10분)
python3 scripts/lab.py selfheal-off
python3 scripts/lab.py drift-scale 6 1  # 6회, 복구 후 1초 쉬고 다시
python3 scripts/lab.py drift-misc
python3 scripts/lab.py git-change 4     # 웹훅 없이 (폴링)
python3 scripts/lab.py webhook on
python3 scripts/lab.py git-change 4     # 웹훅 켬
python3 scripts/lab.py prune
python3 scripts/lab.py waves
python3 scripts/lab.py bad-commit
kind delete cluster --name ds-03
```

- Argo CD UI http://localhost:26080 (admin, 비밀번호는 `up.sh` 가 마지막에 찍는다)
- Gitea http://localhost:26030 (lab / lab-password-123, 실습용 계정)
- git 작업 사본은 저장소 밖 `/tmp/ds-03-work` 에 만든다(`DS03_WORK` 로 바꿀 수 있다)
- 필요한 것: Docker, kind, kubectl, python3, git. `bad-commit` 은 argocd CLI 도 쓴다
- 화면 캡처: `<playwright 가 있는 python> scripts/capture.py <out.png> "/applications/argocd/web?view=tree" --click "Diff|Compact diff" --clip x,y,w,h`

## 버전

| 부품 | 버전 | 고른 이유 |
|---|---|---|
| kind | 0.33.0 | 실습 시점 최신 |
| 노드 이미지 | `kindest/node:v1.36.4` | kind 0.33 의 기본값은 1.37.0 인데, Argo CD 3.5 의 검증 대상(tested versions)이 1.33~1.36 이라 1.36 으로 내렸다 |
| Argo CD | v3.5.4 (2026-10-06) | 최신 안정판. 3.6 은 rc |
| Gitea | 28.1.0 rootless | 최신 안정판. 웹훅을 Argo CD 가 Gogs 형식으로 받는다 |
| 앱 | `traefik/whoami:v1.12.0` | 작고 `/health` 가 있다 |

설치는 공식 `manifests/install.yaml` 을 server-side apply 로 넣고, 실습용으로 세 가지를 바꿨다.
`server.insecure: "true"`(웹훅을 http 로 받기 위해), argocd-server 를 NodePort 30080 으로, 그리고 메모리를 아끼려고
dex·notifications·applicationset 컨트롤러를 0 으로 줄였다.

## 결과

2026-10-11, Docker Desktop(메모리 8GB) 위에 kind 클러스터가 3~4개 함께 떠 있었다. 부하가 높던 구간의 결과는 따로 표시했다.

| 실험 | 결과 | 파일 |
|---|---|---|
| selfHeal 끔 | OutOfSync 표시 0.3초, 60초 뒤에도 replicas 5 그대로. 다시 켜자 0.3초 만에 복구 | `selfheal-off.txt` |
| 반복 드리프트(부하 낮을 때) | 0.3 / 4.8 / 16.8 / 52.8 / 160.6 / 298.9초. 백오프 2·6·18·54·162·300초에서 직전 동기화 뒤 흐른 1~2초를 뺀 값 | `drift-scale-clean.txt` (직접 돌리면 `drift-scale-gap1.txt` 로 저장된다. 글과 구분하려고 손으로 이름을 바꿨다) |
| 반복 드리프트(부하 높을 때) | 감지 최대 44초, 동기화 한 번 최대 96초. 되돌림이 공식보다 일찍 시작된 적은 없지만 길게는 40초 늦었다(횟수 7: 297초 예상, 337초 실측) | `drift-scale-under-load.txt`, `drift-scale-accumulated.txt` |
| 라벨 추가 / 손으로 만든 ConfigMap | 드리프트 아님(Synced 유지, 그대로 남음) | `drift-misc.txt` |
| ConfigMap 값 수정 / Deployment 삭제 | 각각 0.3초 만에 복구·재생성 | `drift-misc.txt` |
| git 푸시, 폴링만 | 새 리비전 인식 86.5 / 216.6 / 224.6 / 239.6초. 주기 새로고침 간격 122~300초 | `git-change-poll.txt`, `poll-refresh-intervals.txt` |
| git 푸시, 웹훅 | 인식 0.7~1.1초, 반영 3.4~4.5초 (새 클러스터에서 다시: 0.3초 / 2.5초) | `git-change-webhook.txt`, `validate-fresh-cluster.txt` |
| prune | 끔: requiresPruning 표시만, 동기화 시작 안 함. 켬: 124.6초 뒤 삭제(다음 주기 새로고침) | `prune.txt` |
| sync wave | PreSync Job 0.3초 → ConfigMap 8.1 → Deployment 10.2(Ready 10.5) → Service 12.3초. 2초 대기는 웨이브 적용 직후에 들어가 Healthy 대기와 겹친다(`delayBetweenSyncWaves`) | `waves.txt` |
| 로그·부하 원자료 | selfHeal 백오프 로그 줄, 새 커밋 직후의 두 번째 동기화, 웹훅이 무시되던 회차의 새로고침 시각, load average | `controller-log-notes.txt` |
| 없는 이미지 태그 커밋 | 2.8초 Synced+Progressing, 62.8초 Degraded. 옛 파드 3개는 Ready 로 남음(트래픽은 보내지 않았다). `argocd app rollback` 은 자동 동기화 때문에 거부. `git revert` 후 2.7초 만에 Healthy | `bad-commit.txt` |

### 문서와 다르게 나온 것

- **selfHeal 재시도는 "기본 5초"가 아니다.** 자동 동기화 문서(auto_sync.md)는 5초라고 적지만 3.5.4 의 기본은 지수 백오프
  (`--self-heal-backoff-timeout-seconds` 2, `-factor` 3, `-cap-seconds` 300)다. 횟수(`autoHealAttemptsCount`)는 시간으로 줄지 않고
  새 동기화 작업(새 커밋의 자동 동기화, 수동 동기화, source 스펙 변경)이 시작될 때만 0 이 된다(3.3 에서 쿨다운 옵션이 효과 없는 옵션이 됐다).
  문서의 `--self-heal-timeout-seconds` 는 `--self-heal-backoff-timeout-seconds` 를 0 으로 꺼야 효과가 있다.
- **Git 폴링은 "최대 3분"이 아니다.** 컨트롤러는 120초마다 앱을 훑되 `reconciledAt` 이 120초를 넘은 앱만 Git 과 비교하고(+지터 0~60초),
  repo-server 는 브랜치→커밋 해석을 3분 캐시한다(`--revision-cache-expiration`, 기본값은 `timeout.reconciliation` 이 없으면 3분).
  주기 새로고침은 캐시를 쓰고, 웹훅과 수동 새로고침은 건너뛴다.
- **prune 을 켜도 바로 지우지 않는다.** 컨트롤러는 자동 동기화나 selfHeal 이 새로 켜질 때만 즉시 비교를 요청한다(`automatedSyncEnabled`).

## 돌리다 만난 함정

- **Gitea 28 의 웹훅 허용 목록 키가 바뀌었다.** `[webhook] ALLOWED_HOST_LIST` 는 `[security] ALLOWED_HOST_LIST` 로 옮겨졌고, `*` 는
  "모든 호스트와 맞는 패턴은 허용하지 않는다"며 무시된다. 기본값(external)은 사설 IP 로 가는 웹훅을 막으니 `private` 를 줬다.
- **`INSTALL_LOCK=true` 로 설치 화면을 건너뛰면 DB 테이블이 없다.** `gitea admin user create` 가 `no such table: user` 로 실패한다.
  `gitea migrate` 를 먼저 돌린다.
- **Argo CD 3.x 의 CRD 는 client-side apply 로 안 들어간다.** annotation 크기 한도를 넘으니 `--server-side --force-conflicts` 로 넣는다.
- **웹훅이 와도 조용히 무시될 수 있다.** Argo CD 는 웹훅 페이로드의 저장소 주소를 Application 의 `repoURL` 과 비교한다. Gitea 는 그 주소를
  `ROOT_URL` 로 만든다. 처음에 `ROOT_URL` 을 `http://localhost:26030/` 으로 두었더니 argocd-server 로그에 `Received push event repo: http://localhost:26030/lab/demo`
  만 찍히고 아무 앱도 새로고침되지 않았다. 클러스터 안 주소(`http://gitea.gitea.svc:3000/`)로 바꿨다. gitea 데이터가 emptyDir 라 바꾸면 저장소를 다시 만들어야 한다.
- **argocd CLI `--core` 는 kubeconfig 의 현재 네임스페이스에서 argocd-cm 을 찾는다.** 기본 네임스페이스면 `configmap "argocd-cm" not found`.
  `lab.py` 는 임시 kubeconfig 에 `--namespace=argocd` 를 설정해 부른다.
- **NodePort 가 막 열린 직후 curl 이 빈 응답(exit 52)을 받는다.** `up.sh` 는 `/api/v1/version` 이 응답할 때까지 기다린다.
- **kubectl 컨텍스트를 고정한다.** 같은 머신에서 다른 kind 클러스터가 만들어지면 현재 컨텍스트가 바뀐다. 스크립트는 모두
  `--context kind-ds-03` 을 붙이고, argocd CLI 는 `kind get kubeconfig --name ds-03` 로 만든 임시 kubeconfig 로 부른다.
