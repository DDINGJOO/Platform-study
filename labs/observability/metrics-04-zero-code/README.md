# 메트릭 수집 실습-4: 코드 없이 프로파일과 지표를 얻는다

글: `posts/CS/Observability/metrics-pipeline/09_실습-4 - 코드 없이 프로파일과 지표를 얻는다.html`

의존성이 `spring-boot-starter-webmvc` 하나뿐인 앱에 Pyroscope 자바 에이전트(CPU·할당 프로파일)와
Grafana Beyla(eBPF, HTTP RED 지표)를 붙인다.

## 구성

| 경로 | 내용 |
|---|---|
| `app/` | 스프링 부트 4.1.1. `/price/{sku}`(BigDecimal), `/report`(문자열 2,000줄), `/checkout`(10% 503). `REPORT_IMPL=builder` 면 고친 보고서 구현 |
| `compose.yaml` | app(+Pyroscope 에이전트), beyla(profile `ebpf`), pyroscope, prometheus, grafana, load(k6, profile `load`) |
| `run-load.sh` | k6 를 `DURATION`(기본 3m) 돌리고, 앱 cgroup CPU 초와 거절된 업로드 수를 찍는다 |
| `top-frames.py` | Pyroscope render API 로 self 상위 함수와 특정 프레임의 total 을 찍는다 |
| `grafana/` | 데이터소스(Pyroscope, Prometheus), 대시보드 "Beyla RED (코드 수정 없음)" |

호스트 포트: Grafana 21400, Prometheus 21490, Pyroscope 21440, 앱 21480.

## 돌리기

```bash
cd labs/observability/metrics-04-zero-code
docker compose --profile ebpf up -d --build
./run-load.sh                                    # A: 서버 한도 4MiB(기본값). 업로드 대부분이 422

PYROSCOPE_MAX_PROFILE_BYTES=16777216 docker compose --profile ebpf up -d
PYROSCOPE_MAX_PROFILE_BYTES=16777216 ./run-load.sh                  # B

PYROSCOPE_MAX_PROFILE_BYTES=16777216 REPORT_IMPL=builder docker compose --profile ebpf up -d app beyla
REPORT_IMPL=builder PYROSCOPE_MAX_PROFILE_BYTES=16777216 ./run-load.sh   # C

python3 top-frames.py http://localhost:21440 'process_cpu:cpu:nanoseconds:cpu:nanoseconds{service_name="shop"}' now-4m now 15 lab/zc

# Beyla 의 자바 에이전트 주입을 끄고 보기
OBI_JAVAAGENT=false docker compose --profile ebpf up -d app beyla

docker compose --profile ebpf --profile load down -v
```

Grafana → Explore → Pyroscope, 프로파일 타입 `process_cpu - cpu` 또는 `memory - alloc_in_new_tlab_bytes`.

## 버전

| 부품 | 버전 | 비고 |
|---|---|---|
| Spring Boot | 4.1.1 | Java 21 (Temurin 21.0.12) |
| Pyroscope 자바 에이전트 | 2.9.2 | `app/Dockerfile` 의 `PYROSCOPE_AGENT_VERSION` |
| Pyroscope 서버 | 2.3.2 | 실습 전날 나온 2.4.0 대신 2.3 라인 최신 패치 |
| Grafana Beyla | 3.38.0 | |
| Prometheus | 3.15.0 | |
| Grafana | 13.2.3 | |
| k6 | 2.3.0 | VU 10, 3분 |

실행 환경: Docker Desktop for Mac (linuxkit 6.12, arm64). `/sys/kernel/btf/vmlinux` 있음. Beyla 가 그대로 동작했다.

## 돌려서 확인한 것 (2026-10-10)

| 실행 | k6 처리량 | 앱 CPU(cgroup) | 프로파일 CPU 합계 | 업로드 거절 |
|---|---|---|---|---|
| A 한도 4MiB, String.format | 4,036 req/s | 744.3초 | 105.8초 (14%) | 14 |
| B 한도 16MiB, String.format | 4,494 req/s | 768.4초 | 658.0초 (86%) | 0 |
| C 한도 16MiB, StringBuilder | 15,384 req/s | 733.6초 | 709.0초 (97%) | 0 |

## 함정 (돌리다 만난 것)

- Pyroscope 서버의 `-validation.max-profile-size-bytes` 기본값(4MiB, 압축 푼 크기)에 10초치 JFR 이 걸려
  `422 ... decompressed size exceeds maximum allowed size of 4194304 bytes` 로 거절된다. 에이전트 로그에만 ERROR 가 남는다.
  플레임 그래프 모양은 멀쩡해 보여서 cgroup CPU 와 맞춰 보기 전에는 몰랐다.
- Beyla 는 `pid: service:app` 으로 앱의 PID 네임스페이스를 빌린다. 앱 컨테이너를 다시 만들면 Beyla 가 `Exited (137)` 로 죽는다.
  앱을 바꿀 때는 `up -d app beyla` 로 같이 띄운다.
- Beyla 3.38.0 은 기본값으로 JVM 에 `/tmp/obi-java-agent.jar` 를 동적 attach 한다(TLS·가상 스레드·런타임 지표용).
  `OTEL_EBPF_JAVAAGENT_ENABLED=false` 로 꺼도 HTTP RED 와 라우트 템플릿은 그대로 나왔다.
- 라우트 템플릿(`/price/{sku}`)은 OBI 가 jar 의 클래스 파일에서 스프링 애노테이션을 읽어 얻는다
  (`pkg/internal/transform/route/harvest/java`).
- `/sys/fs/bpf` 가 없어 `bpffs ... no such file or directory` 경고가 난다. 고정 맵을 쓰는 기능(프로파일 연계 등)만 꺼진다.
- Grafana 를 `mem_limit: 400m` 으로 두면 큰 프로파일 쿼리 중 OOM(137)으로 죽었다. 768m 로 올렸다.
- Beyla 기본 지연 버킷(0.005, 0.01, 0.025…)이 거칠어서 밀리초 단위 p99 가 버킷 경계(5ms, 10ms)로만 나온다.
- 첫 탐색 실행에서 73만 건 중 1건의 라우트가 `/peport` 로 찍혔다(원인 미확인).
- `PYROSCOPE_PROFILER_EVENT=cpu`(perf_events)도 오류 없이 떴지만 커널 프레임이 안 보여 실제로 perf 를 썼는지 확인하지 못했다. 글은 기본값 itimer 로 썼다.
