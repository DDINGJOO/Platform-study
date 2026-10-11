# ds-01-bluegreen: 하이랜더와 블루그린을 Argo Rollouts로 돌려 본다

`posts/CS/DevOps/delivery-safety/05_실습-1 - 하이랜더와 블루그린을 Argo Rollouts로 돌려 본다.html` 의 실습 코드.
같은 앱을 재생성(Recreate), 롤링 업데이트, 하이랜더, 블루그린으로 배포하면서 k6 로 초당 50건을 계속 보내
실패 건수와 버전 전환 시점, 롤백 시간을 잰다.

## 구성

| 경로 | 내용 |
|---|---|
| `app/` | Go 로 쓴 작은 웹 서버. 응답에 버전을 싣는다. `STARTUP_DELAY`(기본 10초) 동안 `/ready` 가 503, SIGTERM 을 받으면 새 연결을 받지 않고 처리 중인 요청만 끝낸다 |
| `kind.yaml` | 클러스터 `ds-01`. NodePort 30080 → 호스트 `127.0.0.1:24080`, 30081 → `24081` |
| `k8s/` | 서비스 둘(`web`, `web-preview`), Deployment 셋(Recreate, 롤링, 롤링+preStop), Rollout 셋(블루그린, 하이랜더 흉내, 처음 시도한 `scaleDownDelaySeconds: 0` 하이랜더) |
| `k6/load.js` | 초당 50건을 고르게 보내고 응답 버전을 태그로 남긴다. `NOREUSE=1` 이면 요청마다 새 연결 |
| `scripts/run.sh` | 시나리오 하나를 돌린다. 배포·롤백 명령 시각을 `out/<이름>.events` 에 남긴다 |
| `scripts/chart.py` | 초별 응답(v1, v2, 실패)을 막대로 그려 PNG 로 찍는다(Playwright 필요). 글의 그림 2~4 |
| `scripts/analyze.py` | k6 CSV 를 초 단위로 묶어 실패·버전 전환을 표로 낸다. 결과는 `results/<이름>.txt` |
| `results/` | 글에 실린 실행의 요약. 시각은 부하 시작 기준 상대 초 |

`out/` 은 원자료(유닉스 시각이 들어간 CSV)라 커밋하지 않는다.

## 버전

| 부품 | 버전 | 비고 |
|---|---|---|
| kind | 0.33.0 | |
| 노드 이미지 | kindest/node:v1.37.0 | kind 0.33.0 의 기본값. 다이제스트는 `kind.yaml` |
| kubectl | 1.37.1 | 서버와 마이너 버전 차이가 1 이하여야 한다 |
| Argo Rollouts | 1.10.0 | 컨트롤러와 `kubectl argo rollouts` 플러그인 |
| k6 | 2.3.0 | `grafana/k6:2.3.0` 컨테이너로 돌린다. 설치 불필요 |
| Go | 1.26 | 이미지 안에서 빌드 |

## 돌리기

실행 위치는 전부 `labs/devops/ds-01-bluegreen`.

```bash
# 1. 클러스터와 Argo Rollouts
kind create cluster --config kind.yaml
kubectl --context kind-ds-01 create namespace argo-rollouts
kubectl --context kind-ds-01 apply --server-side -n argo-rollouts \
  -f https://github.com/argoproj/argo-rollouts/releases/download/v1.10.0/install.yaml

# 2. 앱 이미지
docker build -t obs-lab/ds-01-bluegreen:dev app
kind load docker-image obs-lab/ds-01-bluegreen:dev --name ds-01

# 3. 시나리오 (하나에 1~4분)
scripts/run.sh recreate          # Recreate: 지우고 띄운다 (delete + none)
scripts/run.sh rolling           # 롤링 업데이트 25%/25%
scripts/run.sh rolling-prestop   # 롤링 업데이트 + preStop 5초
scripts/run.sh rolling-undo      # 롤링 업데이트 뒤 kubectl rollout undo. 기본은 preStop 5초 매니페스트(UNDO_MANIFEST 로 바꾼다)
scripts/run.sh highlander        # Rollout 블루그린, 자동 승격, scaleDownDelayRevisionLimit 0 (옛 ReplicaSet 즉시 축소)
scripts/run.sh bluegreen         # Rollout 블루그린, 수동 승격, 60초 안에 undo
scripts/run.sh bg-undo-late      # 60초가 지나 옛 ReplicaSet 이 0 이 된 뒤 undo
scripts/run.sh bg-keepalive      # 승격만 하고 둔다. keep-alive 클라이언트가 언제 넘어오는지
scripts/run.sh highlander-delay0 # scaleDownDelaySeconds: 0 (옛 ReplicaSet 이 줄지 않는다)
scripts/icmp-check.sh            # 엔드포인트 0개인 NodePort 에 동시 연결 20개 (Deployment web 이 있어야 한다)

# 되돌리기를 preStop 없는 Deployment 로, 요청마다 새 연결로
UNDO_MANIFEST=deploy-rolling.yaml NOREUSE=1 TAG=noprestop-noreuse scripts/run.sh rolling-undo

# 같은 시나리오를 조건만 바꿔 다시: TAG 는 결과 파일 이름 꼬리, NOREUSE=1 은 k6 가 요청마다 새 연결
NOREUSE=1 TAG=noreuse scripts/run.sh bluegreen      # → results/bluegreen-noreuse.txt
TAG=r2 scripts/run.sh rolling                       # → results/rolling-r2.txt

# 그림
python3 scripts/chart.py out/deploy.png recreate-r2=Recreate rolling-r2=롤링

# 4. 정리
kind delete cluster --name ds-01
```

중간 상태를 직접 보려면:

```bash
curl -s http://127.0.0.1:24080/            # 운영(active) 서비스
curl -s http://127.0.0.1:24081/            # 미리보기(preview) 서비스
kubectl argo rollouts --context kind-ds-01 -n lab get rollout web --watch
```

## 글에 실린 결과 (요약은 `results/`)

| 시나리오 | 실패 / 전체 | 메모 |
|---|---|---|
| Recreate 1~3회 | 515 / 2,923, 462 / 2,923, 469 / 2,922 | 다운타임 12.9, 11.9, 12.1초. 실패 대부분이 2초 타임아웃(`icmp-ratelimit.txt`) |
| 롤링 1~3회 | 20 / 2,929, 12 / 3,001, 9 / 3,001 | 3회는 파드 종료 시각(`term:`)도 기록. 21.5초·32.4초 종료 직후에 실패 |
| 롤링 + preStop 5초 1회, 2회 | 0 / 3,001, 0 / 3,000 | |
| 하이랜더 `scaleDownDelaySeconds: 0` | 0 / 4,501 | 전부 v1. 옛 ReplicaSet 이 줄지 않았다(두 번 다) |
| 하이랜더 `scaleDownDelayRevisionLimit: 0` | 37 / 2,984 | 응답 끝 시각 21.5~24.5초. 2초 타임아웃을 빼면 21.5~22.5초에 보낸 요청 |
| 블루그린 새 연결 | 0 / 5,000 | 승격 → 첫 v2 0.1초, 되돌리기 → 마지막 v2·첫 v1 1.2초 |
| 블루그린 keep-alive | 0 / 5,500 | 승격 60초 뒤(옛 ReplicaSet 축소 시점)에야 v2 |
| 블루그린, 0 이 된 뒤 되돌리기 | 0 / 4,000 | 다시 승격 대기로 멈춤. 명령 → 첫 v1 12.5초 |
| 롤링 `rollout undo`, preStop 5초, 새 연결 | 0 / 3,001 | 명령 → 첫 v1 11.0초, 마지막 v2 22.8초 |
| 롤링 `rollout undo`, preStop 없음, 새 연결 | 34 / 2,998 | 명령 → 첫 v1 11.0초, 마지막 v2 21.9초 |
| 롤링 `rollout undo`, preStop 5초, keep-alive 1회·2회 | 0 / 3,001 | 명령 → 첫 v1 16.3초, 마지막 v2 27.3초. 조건이 달라 블루그린과 직접 비교하지 않는다 |

하이랜더를 처음 다시 돌린 실행은 앞 시나리오의 Rollout 을 지운 뒤 남은 ReplicaSet 을 새 Rollout 이 같은 해시로 입양했고,
같은 시각 컨트롤러 매니저가 재시작해서 버렸다. 그 뒤로 `run.sh` 의 reset 이 ReplicaSet 까지 지우고, Rollout 시나리오는 전부 다시 돌렸다(`highlander-delay0` 은 퇴고 뒤 한 번 더 돌려 결과를 바꿨다).

## 돌리다 만난 함정

- **Argo Rollouts 설치 매니페스트를 `kubectl apply` 로 넣으면 CRD 두 개가 실패한다.**
  `metadata.annotations: Too long: may not be more than 262144 bytes`. 클라이언트 측 apply 가
  `last-applied-configuration` 주석에 CRD 전체를 넣기 때문이다. `--server-side` 로 넣는다. 공식 설치 문서의 표준 명령에는 `--server-side` 가 없고, namespace-install 용 CRD 설치 메모에만 붙어 있다. 이 실습(kind 노드 v1.37.0)에서는 표준 명령이 위 오류로 실패했다
- **`kind create cluster` 는 kubeconfig 의 현재 컨텍스트를 새 클러스터로 바꾼다.** 다른 클러스터를 같이 쓰고 있다면
  명령마다 `--context kind-ds-01` 을 붙인다. 스크립트도 그렇게 썼다
- **Argo Rollouts 에는 Recreate 전략이 없다.** Rollout 의 `strategy` 는 `blueGreen` 과 `canary` 뿐이다. 그래서 재생성과 롤링은
  쿠버네티스 Deployment 로, 블루그린과 하이랜더는 Rollout 으로 돌렸다
- **Docker Desktop 하나에 kind 클러스터 여러 개를 띄우면 숫자가 흔들린다.** 이 실습을 돌린 날은 다른 kind 클러스터 세 개가 같은
  Docker VM(메모리 8GB)에 떠 있었고, VM 부하 평균이 수십에서 백 단위를 오갔다. 첫 시도에서는 컨트롤러 매니저가 리더 선출을
  놓쳐 재시작하면서 Recreate 한 번이 3분 가까이 걸렸다. 그 실행은 버리고 다시 돌렸다. 시간 숫자는 이 조건에서 나온 값이다
- **엔드포인트가 0개인 Service 로 보낸 요청이 대부분 거부가 아니라 타임아웃이 된다.** kube-proxy 는 NodePort 에
  `REJECT --reject-with icmp-port-unreachable` 를 넣지만, 커널이 ICMP 목적지 도달 불가를 대상마다 초당 한 번 정도로
  제한한다(`net.ipv4.icmp_ratelimit = 1000`, `icmp_ratemask = 6168`). 동시에 20개를 보내면 6개만 즉시 거부되고 14개는 타임아웃
- **`scaleDownDelaySeconds: 0` 은 "즉시"가 아니다.** v1.10.0 에서도 옛 ReplicaSet 을 줄이지 않고 남긴다
  (argoproj/argo-rollouts#1992). 곧바로 줄이려면 `scaleDownDelayRevisionLimit: 0`
- **블루그린 전환은 새 연결에만 적용된다.** keep-alive 로 붙어 있는 클라이언트는 옛 ReplicaSet 이 줄어들 때까지 옛 버전과 이야기한다.
  되돌리기도 마찬가지
- **`NOREUSE=1` 실행에는 배포와 무관한 타임아웃이 1분에 몇 건씩 섞였다.** 원인은 확인하지 못했다. 배포 구간 실패와 나눠 셌다
