# SLO와 경고 실습-2: 모든 자바 서비스에 같은 SLI 대시보드를 깐다

Micrometer 의 HTTP·JVM·톰캣 지표로 만든 공통 SLI 대시보드(`grafana/dashboards/java-sli.json`)를
Grafana 프로비저닝으로 넣고, 서비스 두 개(orders, payments)에 같은 화면을 쓴다.
스레드 풀 포화와 GC 압박을 넣어 어느 패널이 먼저 반응하는지 본다.

앱은 실습-1 과 같은 코드(`../slo-01-burn-rate/app`)다. `APP_NAME` 으로 `application` 태그만 바꾼다.

| 서비스 | 설정 |
|---|---|
| orders | 톰캣 스레드 20개, GC 미지정(메모리 한도 512MB 라 JVM 이 Serial 을 고른다) |
| payments | `-XX:+UseG1GC` |
| 공통 | `-Xmx256m`, `mem_limit: 512m` |

## 돌리기

```bash
cd labs/observability/slo-02-jvm-sli
docker compose up -d --build
docker compose --profile load run -d --rm -e TARGET=orders   -e RATE=30 -e DURATION=90m load
docker compose --profile load run -d --rm -e TARGET=payments -e RATE=30 -e DURATION=90m load
python3 scripts/panel-log.py orders   > orders.csv     # 패널 대표값 5초마다
python3 scripts/panel-log.py payments > payments.csv

# 1) 스레드 풀 포화: orders 요청마다 200ms, 그 위에 45초 동안 초당 90건 추가
curl -X POST 'localhost:24180/chaos?latencyMs=200'
docker compose --profile load run --rm -e TARGET=orders -e RATE=90 -e DURATION=45s -e MAX_VUS=1000 load

# 2) GC 압박 세 단계(payments): 할당만 → 남는 데이터 90MB → 118MB + 초당 600MB → 되돌림
bash scripts/gc-steps.sh

docker compose --profile load down -v
```

- Grafana http://localhost:24130 → SLI / 자바 서비스 공통 SLI (서비스 선택 변수)
- Prometheus http://localhost:24190 (k6 지연은 원격 쓰기 네이티브 히스토그램 `k6_http_req_duration_seconds`)

## 버전

Spring Boot 4.1.1(Micrometer 1.17.1, Java 21.0.12), Prometheus 3.15.0, Grafana 13.2.3, k6 2.3.0

## 함정 (돌리다 만난 것)

- 톰캣 스레드 지표(`tomcat_threads_*`)는 `server.tomcat.mbeanregistry.enabled=true` 가 있어야 나온다.
- GC 를 지정하지 않으면 컨테이너 메모리 한도 1,792MB 미만에서는 Serial GC 가 된다(OpenJDK `os::is_server_class_machine`).
  영역 이름이 `Eden Space`/`Tenured Gen`, GC 이름이 `Copy`/`MarkSweepCompact` 라서 G1 이름을 가정한 쿼리는 빈다.
  G1 은 Eden·Survivor 의 `jvm_memory_max_bytes` 가 -1 이다. 힙 최대값은 `sum(... > 0)` 로 구한다.
- 액추에이터도 같은 톰캣 스레드를 쓴다. 스레드가 다 차면 스크레이프가 5초 타임아웃(간격 5초일 때)을 넘겨 `up=0` 이 된다.
- G1 영역 1MB 에서 1MB 배열은 영역 두 개를 차지한다(거대 객체). 90MB 를 붙잡으면 GC 직후 힙이 약 177MB 늘었다.
- Full GC 가 초당 90번쯤 일어날 때 Micrometer 의 `jvm_gc_pause_seconds_count` 는 그 10분의 1 정도만 늘었고,
  압박을 멈추자 밀린 수가 10초 안에 들어왔다(GC 로그 `-Xlog:gc:stdout` 와 비교해 합계 11,159 로 일치).
- k6 원격 쓰기는 `K6_PROMETHEUS_RW_TREND_AS_NATIVE_HISTOGRAM=true` 로 히스토그램을 보냈다. Prometheus 3.15 는 기능 플래그 없이 받았다.
- 노트북이 덮개를 닫은 채 잠들면(maintenance sleep) 컨테이너와 기록 스크립트가 같이 멈춘다. 한 번 그렇게 끊긴 실행은 버리고 다시 돌렸다.
