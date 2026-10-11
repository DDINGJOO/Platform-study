# 트래픽 관리 실습-6: 같은 장애에 비율 제한, 벌크헤드, 서킷 브레이커를 걸어 본다

하위 서비스(`downstream`) 하나를 호출하는 쪽(`order-*`)을 네 대 띄우고, 하위 호출을 감싸는 방법만 다르게 한다.
같은 부하를 주면서 하위 서비스를 느리게, 그다음 빨리 실패하게 만들고 각 패턴이 무엇을 세고 언제 거절하는지 본다.

| 컨테이너 | 하위 `/recommend` 호출을 감싸는 것 | 설정 |
|---|---|---|
| `order-rl` | RateLimiter | 1초마다 허가 30개, 기다리지 않음(`timeoutDuration` 0) |
| `order-bh` | Bulkhead(세마포어) | 동시 10개, 기다리지 않음(`maxWaitDuration` 0) |
| `order-cb` | CircuitBreaker | 개수 기준 창 20, 최소 호출 10, 실패율 50%, OPEN 10초, HALF_OPEN 시험 5건 |
| `order-cbbh` | CircuitBreaker( Bulkhead( 호출 ) ) | 위 두 설정을 겹친다. 애너테이션 기본 순서처럼 서킷이 바깥 |

- 네 대 모두 요청 처리 스레드는 25개(`server.tomcat.threads.max`)이고 `/recommend` 와 `/pay` 가 나눠 쓴다.
  `/pay` 는 아무것도 감싸지 않은 하위 호출(늘 5ms)이다. 한 의존성의 장애가 다른 호출로 번지는지 본다.
- 응답 코드로 거절 이유를 구분한다: 429 = 비율 제한·벌크헤드, 503 = 서킷 OPEN, 502 = 하위 실패.
- 하위 호출 읽기 타임아웃은 3초, k6 는 5초까지 기다린다.

## 돌리기

```bash
cd labs/traffic/tm-06-resilience4j
docker compose up -d --build
./scripts/phases.sh            # k6 11분(대마다 /recommend 초당 40, /pay 초당 20) + 시간에 맞춘 장애 주입
python3 scripts/summarize.py   # 구간별 숫자를 Prometheus 에서 뽑는다
docker compose --profile load down -v
```

`phases.sh` 가 하는 장애 주입은 이것뿐이다. 따로 넣어 보려면 같은 명령을 직접 친다.

```bash
curl -X POST 'localhost:28082/admin/fault?delayMs=1000&errorRate=0'   # 느려짐
curl -X POST 'localhost:28082/admin/fault?delayMs=50&errorRate=1.0'   # 빨리 실패
curl -X POST 'localhost:28082/admin/fault?delayMs=50&errorRate=0'     # 정상
```

| 구간 | 하위 `/recommend` |
|---|---|
| 0~2분 | 50ms, 실패 0 |
| 2~5분 | 1000ms, 실패 0 |
| 5~6분 | 50ms, 실패 0 |
| 6~9분 | 50ms, 실패 100% |
| 9~11분 | 50ms, 실패 0 |

- Grafana http://localhost:28000 → 대시보드 「실습-6 비율 제한 · 벌크헤드 · 서킷 브레이커」
- Prometheus http://localhost:28090
- 호출자 http://localhost:28181~28184 (rl, bh, cb, cbbh), 하위 http://localhost:28082
- 지표(actuator)는 컨테이너 안 9090 포트로 따로 연다(아래 함정 1). 호스트로는 열지 않았다.

## 버전

| 부품 | 버전 |
|---|---|
| Spring Boot | 4.1.1 (Java 21, Tomcat 11.0.24) |
| Resilience4j | 2.4.0 (2026-03-14 릴리스, Maven Central 최신). 코어 모듈만 |
| Prometheus | 3.15.0 |
| Grafana | 13.2.3 |
| k6 | 2.3.0 |

## 왜 스프링 부트 스타터를 안 쓰나

`resilience4j-spring-boot3` 는 스프링 부트 4 에서 **일부러 뜨지 않는다.** 2.4.0 에는 부트 버전을 확인하는
`SpringBoot3Verifier` 가 들어 있고, 메이저 버전이 4 면 예외를 던진다. `compat/` 에서 실제로 띄운 결과:

```
APPLICATION FAILED TO START
Description:
Module 'io.github.resilience4j:resilience4j-spring-boot3' is only compatible with Spring Boot 3.x
Action:
Update your project to use 'io.github.resilience4j:resilience4j-spring-boot4'
```

같은 2.4.0 에 `resilience4j-spring-boot4` 가 새로 생겼다(릴리스 노트 "Add support for Spring Boot 4 / Spring Cloud 5", PR #2384).
`compat/` 에서 이 모듈로 바꾸면 스프링 부트 4.1.1 에서 뜨고, `@CircuitBreaker` 애너테이션이 걸린 엔드포인트와
`/actuator/circuitbreakers`, `resilience4j_*` 지표 22줄이 나왔다. 모듈 자체는 스프링 부트 4.0.0 에 맞춰 빌드돼 있다(POM 의존성).

그래도 이 실습은 코어 모듈(`resilience4j-ratelimiter`, `-bulkhead`, `-circuitbreaker`, `-micrometer`)을 직접 쓴다.
패턴마다 무엇을 세는지 보려는 실습이라, 설정과 감싸는 순서가 YAML 과 애스펙트 순서 뒤에 숨지 않고 `Guards.java` 한 파일에 보이는 편이 낫다고 봤다.

```bash
cd compat
docker build --build-arg MODULE=spring-boot3 -t compat:b3 . && docker run --rm compat:b3   # 기동 실패
docker build --build-arg MODULE=spring-boot4 -t compat:b4 . && docker run --rm -p 28901:8080 compat:b4
```

## 결과 (2026-10-11 실행, `scripts/summarize.py` 출력. 서버가 센 응답(`http_server_requests`), 단위는 초당 건수, 구간 앞뒤 20초 제외)

```
== 정상
              200    429    502    503  스레드max  /pay p99(서버)
order-rl     30.0   10.0    0.0    0.0       2        8ms
order-bh     40.0    0.0    0.0    0.0       2        8ms
order-cb     40.0    0.0    0.0    0.0       2        8ms
order-cbbh   40.0    0.0    0.0    0.0       4        8ms
== 느려짐(1000ms)
order-rl     24.9    0.0    0.0    0.0      25        9ms
order-bh      9.8   30.2    0.0    0.0      10        9ms
order-cb     24.9    0.0    0.0    0.0      25        9ms
order-cbbh    1.3    0.9    0.0   37.8      11        9ms
== 빨리 실패(100%)
order-rl      0.0   10.0   30.0    0.0       2       10ms
order-bh      0.0    0.0   40.0    0.0       2       10ms
order-cb      0.0    0.0    0.5   39.5       0       10ms
order-cbbh    0.0    0.0    0.5   39.5       1       10ms
```

k6 가 센 5초 무응답(11분 전체): `order-rl` /pay 3,134건·/recommend 6,397건, `order-cb` /pay 3,247건·/recommend 6,619건,
`order-bh`·`order-cbbh` 0건. 스레드가 25개 다 찬 것은 느려짐 구간뿐이었다.

위 표의 느려짐 구간 200(초당 24.9)은 서버가 끝낸 응답이고, 클라이언트가 받은 성공은 훨씬 적다. k6 는 11분 합계만 남기므로
정상 구간 5분 몫(초당 30 또는 40 × 300초)을 빼고 180초로 나눠 어림하면 `order-rl` 약 2.3/s(9,419 − 9,000), `order-cb` 약 1.5/s(12,269 − 12,000),
`order-bh` 약 9.7/s(13,750 − 12,000)다. 벌크헤드만 서버와 클라이언트 숫자가 맞는다.

## 덧붙인 확인: 서킷이 벌크헤드 거절을 무시하면

`order-cbbh-ign` 은 `order-cbbh` 와 같고 서킷 설정에 `ignoreExceptions(BulkheadFullException.class)` 만 더했다.
기본 실행에는 없고 `ignore` 프로필로 띄운다(그래서 기본 실행 중 Prometheus 대상 `order-cbbh-ign:9090` 은 down 으로 보인다).

```bash
docker compose --profile ignore up -d --build
./scripts/ignore-check.sh      # 4분: 정상 1분, 느려짐 2분, 정상 1분. 두 호출자만 부하
```

같은 장비에서 다른 부하가 함께 돌던 때라 잡음이 크다. `order-cbbh` 의 서킷은 지연 주입(14:37:57) 18초 전인 14:37:39 에 이미 한 번 열렸고,
실행 끝 무렵 Docker 데몬이 몇 분간 응답하지 않아 k6 가 10분 넘게 끝나지 못했다. 서버 쪽 숫자, 느려짐 구간 뒤쪽 100초:

```
                               200/s   429/s   503/s   서킷 OPEN
order-cbbh     (기본)           1.4     0.9    38.8      9번
order-cbbh-ign (벌크헤드 무시)   8.8    32.8     0        0번
```

같은 실행의 k6 는 `order-cbbh-ign` 에서도 `/recommend` 1,160건, `/pay` 644건을 5초 무응답으로 셌다(`order-cbbh` 는 837건, 465건).
Docker 가 멈춘 시간을 포함한 합계라 구간을 나눌 수 없다. 본 실행의 `order-bh` 는 0건이었으니, 이 확인은 "서킷이 열리지 않는다"까지만 보여 준다.

## 돌리다 만난 함정

1. **스레드가 다 차면 지표도 못 긁는다.** 첫 실행은 actuator 를 앱과 같은 8080 에 뒀다. 느려짐 구간에서
   `order-rl`, `order-cb` 의 스크레이프가 `context deadline exceeded` 로 실패했고(`up` = 0, 느려짐 시작 후 1분이 안 되는 사이에 대마다 22~23회),
   장애가 한창일 때 그 두 대의 지표가 비었다. `management.server.port` 로 지표를 다른 커넥터(9090)로 빼자 해결됐다.
   다른 커넥터는 스레드 풀도 따로 쓴다. 첫 실행처럼 보려면 `LAB_MGMT_PORT=8080` 을 주고 `prometheus.yml` 포트를 8080 으로 바꾼다.
2. **서버가 잰 지연에는 스레드를 기다린 시간이 없다.** 느려짐 구간에 `/pay` 의 서버 p99(`http_server_requests`)는 9ms 였지만
   k6 는 `order-rl`·`order-cb` 의 `/pay` 를 수천 건 5초 타임아웃으로 셌다. 스프링의 관측 필터는 요청이 스레드를 잡은 뒤에야 시작한다.
   Tomcat 은 연결을 최대 8192개(`maxConnections` 기본값)까지 받아 두고 스레드를 기다리게 한다.
3. **RateLimiter 와 Bulkhead 지표에는 거절 수가 없다.** `resilience4j-micrometer` 2.4.0 은 RateLimiter 에
   `available_permissions`, `waiting_threads` 게이지 둘, Bulkhead(세마포어)에 `available_concurrent_calls`,
   `max_allowed_concurrent_calls` 게이지 둘만 등록한다. 거절은 호출하는 쪽에서 직접 세야 한다(여기서는 응답 코드 429).
4. **서킷 브레이커 `failure_rate` 는 판정 전 -1 이다.** 기동 직후, 그리고 HALF_OPEN 으로 넘어간 직후 로그에 -1.0 이 찍혔다.
5. **2초 스크레이프로는 서킷 상태 전이를 다 못 본다.** `order-cbbh` 는 느려짐 3분 동안 CLOSED→OPEN 전이가
   16번 있었는데(로그 `circuit State transition …`), CLOSED·HALF_OPEN 이 1초 남짓이라 그래프에는 몇 번만 보인다.
   상태 전이는 이벤트(로그, `onStateTransition`)로 본다.
6. 느려짐이 끝나는 순간 `order-rl` 은 429 를, `order-cb` 는 200 을 순간 초당 270~330건(10초 rate)씩 냈다. Tomcat 이 받아 두었던
   요청이 스레드가 풀리자 한꺼번에 처리된 것이다. 5초 넘게 기다린 요청이라면 k6 는 이미 연결을 끊은 뒤였다.
