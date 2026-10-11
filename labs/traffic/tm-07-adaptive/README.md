# 트래픽 관리 실습-7: 동시성 한계를 스스로 찾는 리미터를 돌려 본다

같은 스프링 부트 앱을 여러 대 띄우고 `/work` 앞에 두는 리미터만 바꾼다. `/work` 는 앱 안의
"하위 자원 40칸"(공정 세마포어) 중 하나를 잡고 `delayMs` 동안 쓴다. 그래서 처리 상한은 `40 / delayMs` 다.
부하는 대마다 초당 200건으로 고정하고 하위 지연만 50ms → 500ms → 50ms 로 바꾼다.

| 컨테이너 | `/work` 앞의 리미터 | 비고 |
|---|---|---|
| `app-fixed` | `SimpleLimiter` + `FixedLimit.of(100)` | 사람이 정한 고정 한계. 세마포어 벌크헤드와 같은 동작 |
| `app-gradient2-windowed` | `SimpleLimiter` + `WindowedLimit(Gradient2Limit)` | 저장소 README 의 gRPC 서버 예시와 같은 조합. 1초 창의 평균으로 한계를 고친다 |
| `app-vegas` | `SimpleLimiter` + `VegasLimit` | 리미터에 알고리즘을 안 주면 쓰이는 기본값 |
| `app-gradient2` (프로필 `per-request`) | `SimpleLimiter` + `Gradient2Limit` | 창 없이 요청마다 한계를 고친다. 기본 실행에서 뺐다(결과 2) |

알고리즘 설정은 전부 라이브러리 기본값이다. 한계를 넘으면 라이브러리 서블릿 필터(`ConcurrencyLimitServletFilter`)가 기다리지 않고 429 를 돌려준다.

## 돌리기

```bash
cd labs/traffic/tm-07-adaptive
docker compose up -d --build
./scripts/phases.sh            # k6 13분(대마다 초당 200) + 하위 지연 바꾸기
python3 scripts/summarize.py   # 구간별 숫자를 Prometheus 에서 뽑는다
docker compose --profile load down -v
```

| 구간 | 하위 지연 | 처리 상한 | 부하 |
|---|---|---|---|
| 0~3분 | 50ms | 초당 800 | 초당 200 (여유) |
| 3~10분 | 500ms | 초당 80 | 초당 200 (2.5배 과부하) |
| 10~13분 | 50ms | 초당 800 | 초당 200 (회복) |

지연은 대마다 `curl -X POST 'localhost:<포트>/admin/delay?ms=500'` 로 바꾼다.
포트: fixed 28282, gradient2-windowed 28285, vegas 28284, gradient2 28283. Grafana http://localhost:28200, Prometheus http://localhost:28290.

창 없는 Gradient2 까지 같이 보려면:

```bash
docker compose --profile per-request up -d --build
PORTS="28282 28283 28285 28284" TARGETS=app-fixed,app-gradient2,app-gradient2-windowed,app-vegas ./scripts/phases.sh
APPS=fixed,gradient2,gradient2-windowed,vegas python3 scripts/summarize.py
```

## 버전

| 부품 | 버전 |
|---|---|
| Spring Boot | 4.1.1 (Java 21, Tomcat 11.0.24) |
| Netflix concurrency-limits | 0.5.4 (`-core`, `-servlet-jakarta`) |
| Prometheus | 3.15.0 |
| Grafana | 13.2.3 |
| k6 | 2.3.0 |

concurrency-limits 유지보수 상태(2026-10-11 확인): 마지막 릴리스는 0.5.4(2025-12-08), 그 전은 0.5.3(2024-11-20).
main 의 마지막 커밋은 2026-01-12 이고, 그 뒤 열린 PR(#233~#240)은 아직 병합되지 않았다. 저장소의 `OSSMETADATA` 는
`osslifecycle=active`. 버전은 아직 0.x 다. Micrometer 연동 모듈은 없고 Spectator 모듈만 있어서 `MicrometerMetricRegistry` 를 직접 만들었다.

## 결과 (2026-10-11 14:48~15:01 실행, `scripts/summarize.py`, 구간 앞 30초 제외)

```
== 하위 50ms
                      200/s  429/s     p50     p99   limit 평균(최소~최대)  in-flight  자원 대기
fixed                 200.0      -    53ms    56ms     100 (100~100)       10.0      0.0
gradient2-windowed    200.0    0.0    53ms    56ms      26 (24~28)         10.2      0.0
vegas                 200.0      -    53ms    56ms      39 (32~63)         10.1      0.0
== 하위 500ms (과부하, 390초)
fixed                  79.9  120.1  1173ms  1427ms     100 (100~100)       98.4     58.3
gradient2-windowed     56.5  143.3   514ms   866ms      32 (20~55)         31.3      3.0
vegas                  63.6  136.5   593ms  1297ms      46 (9~111)         43.5     11.8
== 하위 50ms (회복)
fixed                 200.0    0.0    53ms    56ms     100 (100~100)       10.0      0.0
gradient2-windowed    200.0    0.0    53ms    56ms      56 (56~56)         10.3      0.0
vegas                 200.0    0.0    53ms    56ms      61 (61~61)         10.2      0.0
```

- 위 표는 서버가 센 응답이다. 이 실행에서는 k6 5초 무응답이 세 대 모두 0건이라 서버와 클라이언트 숫자가 어긋나지 않는다.
- `gradient2-windowed` 는 과부하가 시작되자 한계가 20(Gradient2 기본 `minLimit`)으로 내려가 14:51:20~14:54:40(3분 20초) 동안 그대로였고,
  그동안 성공은 초당 40건(처리 상한의 절반)이었다. 긴 창 평균 RTT 가 51ms 에서 278ms 까지 올라온 14:55 무렵부터
  한계가 오르기 시작해 14:56:20 에 성공 초당 80건에 닿았고, 과부하가 끝날 때 한계 55, 긴 창 평균 423ms 였다.
- `vegas` 는 한계가 9~111 사이를 계속 오갔다. 최소 RTT 를 주기적으로 다시 재는(probe) 순간마다 기준이 바뀐다.
- 회복 뒤 두 적응형 리미터의 한계는 56, 61 에서 멈췄다. 인플라이트(10)가 한계의 절반보다 작으면 한계를 고치지 않기 때문이다.
  `WindowedLimit` 은 창 안의 최대 인플라이트를 넘긴다.
- Vegas 는 바닥 1, 천장 1000(기본값)이라 Gradient2 의 20·200 같은 바닥과 천장이 사실상 없다. 이 실행에서는 9까지 내려갔다.

## 함정과 예상과 다른 결과

1. **[결과 2] Gradient2 를 창 없이 걸면 과부하에서 한계가 올라간다.** 두 번째 실행에서 14:07:21 지연 주입 뒤 27초 만인
   14:07:48 에 한계가 `maxConcurrency` 기본값 200 에 닿았다(세션에서 본 출력은 `out/run2/notes.txt`). Gradient2 의 "긴 창"
   `longWindow` 600 은 시간이 아니라 표본 수이고(`ExpAvgMeasurement`, 계수 2/(600+1)), 창 없이 걸면 요청 하나가 표본 하나라
   초당 80~200건이면 몇 초 분량이다. 긴 창 평균이 지금 RTT 를 금방 따라잡으니 기울기가 1 로 남고 한계는 `queueSize`(4)씩 계속 자란다.
   in-flight 200, 자원 대기 160, 과부하 p99 2.8초. 2분 반 뒤(14:09:56) 힙 `OutOfMemoryError` 로 Tomcat Acceptor 스레드가 죽었고
   (줄 선 요청과 연결이 힙을 채웠다고 보지만 힙 덤프로 확인하지는 않았다),
   지연을 50ms 로 되돌린 뒤에도 응답하지 않았다(k6 5초 타임아웃 76,526건). JVM 은 살아 있고 `OOMKilled` 는 false 였다.
   힙은 `-Xmx160m`, 컨테이너 메모리 상한은 384MiB 로 작게 잡았다.
   저장소 README 의 gRPC 서버 리미터 예시는 `WindowedLimit.newBuilder().build(Gradient2Limit...)` 로 감싼다. 감싸면 1초 창마다 표본 하나라 600개는 10분어치이고, 지수 평균 계수 2/601 의 시간 상수로는 약 300표본(5분쯤)이다.
2. **스레드가 다 차면 지표도 못 긁는다.** 첫 실행은 actuator 를 8080 에 둬서 과부하 동안 리미터 없는 앱과 창 없는 Gradient2 의
   스크레이프가 실패했다. `management.server.port: 9090` 으로 뺐다. 그래도 힙이 바닥난 앱은 9090 도 응답하지 못했다.
3. **거절(429)은 `uri="UNKNOWN"` 으로 기록된다.** 필터가 디스패처 서블릿 앞에서 응답을 끝내서 경로 템플릿이 정해지지 않는다.
   `http_server_requests_seconds_count{uri="/work"}` 로 거절을 세면 0 이 나온다. 라이브러리 카운터
   `concurrency_limits_call_total{status="rejected"}` 와는 일치했다.
4. **라이브러리가 넘기는 게이지는 메서드 참조다.** `AbstractLimiter` 는 `registry.gauge("limit", this::getLimit)` 를 부른다.
   Micrometer `Gauge` 는 기본이 약한 참조라 람다가 GC 되면 값이 `NaN` 이 됐다. `strongReference(true)` 로 해결.
   또 `limit` 게이지에는 리미터 이름 태그가 없다(이름 태그를 붙이자는 PR #235 가 열려 있다). 한 앱에 리미터가 둘이면 겹친다.
5. **`min_rtt` 라는 이름의 지표가 최소값이 아니다.** Gradient2 는 `MetricIds.MIN_RTT_NAME` 으로 긴 창 지수 평균을,
   `MIN_WINDOW_RTT_NAME` 으로 방금 들어온 표본을 기록한다. Vegas 의 `min_rtt` 는 실제 최소 RTT(`rtt_noload`)다.
6. 같은 장비에서 다른 부하가 함께 돈 세 번째 실행은 정상 구간부터 성공이 초당 120건에 그쳐 버렸다(`out/` 는 커밋하지 않는다).
   지연 바꾸기 `curl` 이 멈춘 앱에서 기다리다 다음 앱으로 못 넘어간 일도 있어 `-m 3 --retry 5` 를 붙였다.
