# 관측성 실습

`posts/CS/Observability/` 개념 글에 붙는 실습 코드. 글에 실린 화면과 숫자는 전부 여기서 돌린 결과다.

## 구조

| 경로 | 내용 |
|---|---|
| `app/` | 스프링 부트 4 샘플 앱. 프로필(`order`·`inventory`·`payment`)로 서비스 셋을 띄운다. OTel 의존성 없음 |
| `stack/` | 실습이 같이 쓰는 관측 스택: OTel Collector · Tempo · Prometheus · Grafana. 실습 compose 가 `include` 한다 |
| `scripts/` | `show-trace.py`(트레이스를 스팬 표로), `capture.py`(Grafana 화면 캡처), `startup-time.sh`(에이전트 기동 비용) |
| `tracing-01-zero-code/` | 추적과 디버깅 실습-1: 코드 수정 없이 자바 에이전트로 추적 |

## 돌리기

Docker 만 있으면 된다(앱은 이미지 안에서 Gradle 로 빌드한다).

```bash
cd labs/observability/tracing-01-zero-code
docker compose up -d --build
docker compose --profile load run --rm load                 # k6 60초
PAYMENT_FAIL_RATE=0.2 PAYMENT_SLOW_MS=250 docker compose up -d payment   # 실패·지연 주입
python3 ../scripts/show-trace.py                             # 최근 트레이스를 스팬 표로
docker compose down
```

- Grafana http://localhost:3000 (로그인 없음) → Explore → Tempo
- Tempo API http://localhost:3200, Prometheus http://localhost:9090

## 화면 캡처

`capture.py` 는 Playwright(시스템 Chrome)로 Grafana Explore 를 헤드리스로 찍는다.
이미지는 `posts/<시리즈>/images/lab-NN/` 에 두고, 글에서는 jsDelivr
(`https://cdn.jsdelivr.net/gh/DDINGJOO/Platform-study@main/<경로>`)로 부른다.
업로더에 이미지 업로드 기능이 없어서다. **글을 올리기 전에 이미지를 main 에 먼저 푸시해야 한다.**

## 버전

| 부품 | 버전 | 비고 |
|---|---|---|
| Spring Boot | 4.1.1 | Java 21 |
| OTel Java agent | 2.32.0 | `app/Dockerfile` 의 `OTEL_AGENT_VERSION` |
| OTel Collector contrib | 0.162.0 | |
| Tempo | 2.10.8 | 3.x 는 분산 배포에서 Kafka 를 거친다(monolithic 은 Kafka 없이 뜸). 설정 자료가 많은 2.10 을 쓴다 |
| Prometheus | 3.15.0 | remote write 수신·exemplar 저장 켬 |
| Grafana | 13.2.3 | 익명 Admin, 라이트 테마 |
| k6 | 2.3.0 | |

## 함정 (돌리다 만난 것)

- Tempo metrics-generator 의 `local-blocks` 프로세서는 `traces_storage.path` 가 없으면
  `local blocks processor requires traces wal` 로 생성기 전체가 안 뜬다.
- 모든 서비스가 기동 때 스키마 SQL 을 돌리면 서비스 그래프에 그 서비스 → DB 간선이 생긴다.
  초기화는 `application-inventory.yml` 에서만 켠다.
- Tempo 검색 API 는 trace ID 의 앞자리 0 을 떼고 돌려준다(31자). 조회할 때는 32자로 채운다.
- Grafana Explore 는 `networkidle` 에 도달하지 않는다. 캡처는 `load` 후 몇 초 기다린다.
