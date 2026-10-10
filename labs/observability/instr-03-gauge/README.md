# 계측 라이브러리 실습-3: 게이지가 NaN이 되는 순간을 만든다

글: `posts/CS/Observability/instrumentation/07_실습-3 - 게이지가 NaN이 되는 순간을 만든다.html`

같은 값(42)을 내는 게이지 다섯 개를 기동 때 등록한다. 다른 점은 관측 대상 `AtomicInteger` 를 누가 쥐고 있느냐다.

| case | 코드 |
|---|---|
| `local` | `Gauge.builder(name, local, AtomicInteger::get)` 지역 객체 |
| (`queue.size.shortcut`) | `registry.gauge(name, new AtomicInteger(42))` 반환값을 버림 |
| `field` | 빈의 필드로 보관 |
| `strong` | 지역 객체 + `.strongReference(true)` |
| `supplier` | `Gauge.builder(name, captured::get)` |
| `late-local` | 기동 뒤 `POST /register` 로 지역 객체 게이지 등록 |

`POST /gc` 는 `System.gc()`, `POST /alloc?mb=N` 은 쓰레기만 만든다. 둘 다 GC 횟수를 돌려준다.

## 돌리기

```bash
cd labs/observability/instr-03-gauge
docker compose up -d --build
curl -s localhost:22280/actuator/prometheus | grep ^queue_size
curl -s -XPOST localhost:22280/register
curl -s -XPOST 'localhost:22280/alloc?mb=0'       # GC 횟수 확인
curl -s -XPOST localhost:22280/gc                 # 전체 GC 부탁
docker compose logs otel-collector --no-log-prefix | python3 show-otlp.py queue.size
# Prometheus http://localhost:22290, Grafana http://localhost:22230 (Explore)
docker compose down -v
```

## 버전

Spring Boot 4.1.1 (Micrometer 1.17.1), OTel Collector contrib 0.162.0, Prometheus 3.15.0, Grafana 13.2.3

## 돌리다 만난 것

- 컨테이너 메모리 한도 512MB 에서 JVM 은 Serial GC 를 골랐다(`UseSerialGC ... {ergonomic}`, MXBean 이름 `Copy`/`MarkSweepCompact`).
- 기동 때 등록한 `local` 게이지는 실행마다 달랐다. 한 번은 첫 스크레이프부터 NaN, 다른 한 번은 젊은 GC 두 번을 버티고 전체 GC 에서 NaN.
- 죽은 게이지는 같은 이름·태그로 다시 등록해도 살아나지 않는다. `This Gauge has been already registered ... the registration will be ignored.`
- NaN 하나가 `sum(queue_size)` 를 통째로 NaN 으로 만든다. `queue_size == queue_size` 로 NaN 을 걸러 낼 수 있다.
- Grafana 를 `mem_limit: 256m` 로 띄웠더니 Explore 를 여는 순간 OOM(137)으로 죽었다. 512m 로 올렸다.
