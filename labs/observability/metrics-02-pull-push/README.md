# 메트릭 수집 실습-2: 앱이 죽으면 pull과 push는 다르게 조용해진다

글: `posts/CS/Observability/metrics-pipeline/07_실습-2 - 앱이 죽으면 pull과 push는 다르게 조용해진다.html`

kind 클러스터에 같은 앱을 두 번 띄운다. pull-app 은 Prometheus 가 파드 서비스 디스커버리로 긁고,
push-app 은 OTLP 로 OTel Collector 에 민다. Collector 는 Prometheus OTLP 수신 엔드포인트로 밀고(경로 1),
자기 `:8889` 에도 Prometheus 형식으로 내놓는다(경로 2). 앱을 멈추고(SIGSTOP), 없애고(replicas=0),
재배포하면서 알람 규칙 네 개가 언제 울리는지 잰다.

## 구성

| 경로 | 내용 |
|---|---|
| `app/` | 스프링 부트 4.1.1. 0.1초마다 `shop.orders` +1. Prometheus·OTLP 레지스트리 둘 다 들어 있고 환경변수로 고른다 |
| `kind.yaml` | 클러스터 `obs-lab-metrics-02`, NodePort → 호스트 21290(Prometheus), 21200(Grafana) |
| `k8s/prometheus.yaml` | RBAC, 설정(10초 스크레이프, 규칙 5초), 알람 규칙 4개, `--web.enable-otlp-receiver` |
| `k8s/otel-collector.yaml` | OTLP 수신 → `otlp_http`(Prometheus) + `prometheus`(:8889) |
| `k8s/apps.yaml` | pull-app(애노테이션), push-app(OTLP, `service.instance.id`=파드 이름) |
| `k8s/grafana.yaml`, `k8s/dashboard.json` | 대시보드 "pull과 push가 조용해지는 방식" |
| `up.sh` / `down.sh` | 클러스터 생성·이미지 적재·배포 / 클러스터 삭제 |
| `freeze.sh` | kind 노드 안에서 두 앱 java 에 SIGSTOP, `HOLD`초(기본 400) 뒤 SIGCONT |
| `scale-zero.sh` | 두 Deployment 를 0 으로, `HOLD`초 뒤 1 로 |
| `timeline.py` | 구간 안에서 식 값과 알람이 언제 바뀌었는지 1초 단위로 찍는다 |

kubectl 은 전부 `--context kind-obs-lab-metrics-02` 로 부른다. `up.sh` 는 kind 가 바꾼 현재 컨텍스트를 원래대로 돌려놓는다.

## 돌리기

```bash
cd labs/observability/metrics-02-pull-push
./up.sh
./freeze.sh            # 시작·끝 유닉스초를 찍는다
python3 timeline.py <시작-20> <끝+60>
./scale-zero.sh
python3 timeline.py <시작-20> <끝+60>
kubectl --context kind-obs-lab-metrics-02 -n obs rollout restart deploy/pull-app deploy/push-app
./down.sh
```

## 버전

| 부품 | 버전 |
|---|---|
| kind | 0.33.0 |
| Spring Boot | 4.1.1 (Micrometer 1.17.1) |
| Prometheus | 3.15.0 |
| OTel Collector contrib | 0.162.0 |
| Grafana | 13.2.3 |

## 돌려서 확인한 것 (2026-10-10)

| 사건 | pull | push(OTLP) | push(Collector :8889) |
|---|---|---|---|
| 프로세스 멈춤 | +7초 up=0, +10초 PullTargetDown | +25초 absent_over_time[30s], +295초 absent() | 값 787 이 +296초까지 새 샘플로 저장 |
| replicas=0 | up=0 없이 대상에서 빠짐, +15초 absent(up) | +35초 absent_over_time, +305초 absent() | 종료 때 마지막 값 5052 를 한 번 더 밀고 5분 유지 |
| 재배포 | 옛 파드 up=0 이 한 번 찍힌 실행도, 안 찍힌 실행도 있었다 | 옛 인스턴스 시계열이 4분 52초 겹침 | 같음 |

## 함정 (돌리다 만난 것)

- 스프링 부트 4.1.1 에서 `micrometer-registry-otlp` 만 넣으면 OTLP 내보내기가 켜지지 않는다. 오류·경고 없음.
  `OtlpMetricsExportAutoConfiguration` 이 `OpenTelemetryProperties`(모듈 `spring-boot-opentelemetry`)를 조건으로 건다.
- Docker Desktop 의 containerd 이미지 저장소에서는 `kind load docker-image` 가 공개 이미지(prom/prometheus 등)에 대해
  `ctr: content digest ... not found` 로 실패했다. 직접 빌드한 앱 이미지는 됐다. 공개 이미지는 노드가 직접 받게 둔다.
- `kind create cluster` 는 현재 kubectl 컨텍스트를 새 클러스터로 바꾼다. 다른 클러스터를 쓰는 중이면 되돌린다(up.sh 가 한다).
- Collector 0.162.0 에서 `otlphttp` 이름은 deprecated 경고가 난다. `otlp_http` 로 쓴다.
- 맥이 잠들면 Docker VM 도 멈춰서 실험 시간이 엉킨다(첫 freeze 실행이 이 때문에 망가졌다). `caffeinate -s -i` 로 감싸서 돌렸다.
- 앱의 `@Scheduled(fixedRate)` 는 SIGCONT 뒤에 멈춘 동안 못 한 실행을 몰아서 해서, push 카운터가 787 → 4887 로 한 번에 뛰었다.
  멈춤 시나리오 뒤의 rate() 는 이 앱의 인공물이다.
