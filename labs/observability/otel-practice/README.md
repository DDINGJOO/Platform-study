# OpenTelemetry 운영 실습

작은 로컬 HTTP 서비스에서 텔레메트리를 만들고, Collector를 거쳐 실제 Tempo/Loki에 저장한 결과를 Grafana에서 확인한다. 모든 요청·식별자·민감정보 표식은 가상의 실험 데이터다.

| 편 | 실습 | 확인하는 경계 | 실행 결과 |
|---|---|---|---|
| 1 | [Collector 수락과 저장](collector-loss/README.md) | 큐 수락, 재시도, 재시작, 백엔드 조회 | [수치](collector-loss/out/results.txt) |
| 2 | [Head/tail sampling](tail-sampling/README.md) | SDK에서 버린 트레이스, 늦게 도착한 에러 스팬 | [수치](tail-sampling/out/results.txt) |
| 3 | [Java agent와 Micrometer](dual-instrumentation/README.md) | 중복 계측, 부모 관계, 로그의 trace/span ID | [수치](dual-instrumentation/out/results.txt) |
| 4 | [마스킹과 전파](sensitive-data/README.md) | 스팬·이벤트·로그 처리와 source console·HTTP baggage | [수치](sensitive-data/out/results.txt) |

글과 실제 화면 캡처는 [OpenTelemetry 운영 실습](../../../posts/CS/Observability/otel-practice/ROADMAP.md)에 있다. 각 디렉터리의 `out/summary.json`과 원시 응답이 본문 숫자의 근거다. 화면은 실제 Grafana와 저장한 실행 출력에서 캡처했다.

## 실행

Docker Engine/Desktop, Compose v2, 호스트 Python 3.10 이상이 필요하다. Java 실습은 컨테이너에서 빌드한다. 최초 실행에는 각 이미지와 패키지를 내려받을 수 있어야 한다. 한 실습씩 실행하면 공유 Docker 메모리 사용량을 줄일 수 있다.

```sh
# 저장소 루트에서, 원하는 실습 하나를 선택한다.
python3 labs/observability/otel-practice/collector-loss/run.py
python3 labs/observability/otel-practice/tail-sampling/run.py --build
python3 labs/observability/otel-practice/dual-instrumentation/run.py
python3 labs/observability/otel-practice/sensitive-data/run.py
```

`run.py`는 새 요청을 생성하고 해당 실습의 `out/`을 갱신한다. 스택 초기화 여부와 이전 증거의 보존 방법은 각 README에 적혀 있다. 기존 결과와 캡처를 함께 보존하려면 재실행 전에 해당 `out/`과 `images/lab-NN/`을 별도 복사한다. 다른 Compose 프로젝트나 전역 Docker 자원을 정리하지 않는다.

| 실습 | Compose 프로젝트 | Grafana | Tempo |
|---|---|---|---|
| 1 | `otel-practice-01` | http://localhost:27120 | http://localhost:27110 |
| 2 | `otel-practice-02` | http://localhost:27200 | http://localhost:27201 |
| 3 | `otel-practice-03` | http://localhost:27300 | http://localhost:27320 |
| 4 | `otel-practice-04` | http://localhost:27400 | http://localhost:27420 |

호스트에 공개하는 포트는 loopback으로 제한한다. Grafana 익명 접근은 로컬 실습용이다. 확인을 마치면 해당 디렉터리에서 `docker compose down`으로 종료한다. `--volumes`를 추가하면 그 실습의 볼륨도 삭제한다.

실험 실행에는 호스트 Python 외 별도 Python 패키지가 필요하지 않다. 화면 재캡처에는 기존 Playwright 및 Chrome 환경이 필요하며 실험 실행과 분리되어 있다. `capture.py`는 원자료가 저장된 해당 스택을 켠 상태에서 실행한다. 재실행한 결과를 글에 사용할 때는 숫자와 캡처도 함께 갱신한다.

## 해석 범위

1편은 SDK 없이 OTLP를 직접 만드는 생성기로 Collector 경계를 격리한다. 2·4편은 Python SDK, 3편은 실제 Java agent와 Spring Boot/Micrometer를 사용한다. 동일 서비스의 네 가지 운영 배포를 비교한 실험은 아니다.

단일 로컬 실행의 관찰을 운영 내구성, 전체 에러 보존, 성능 비용, 모든 개인정보 경로의 제거로 일반화하지 않는다. 각 실습은 원자료의 ID 집합과 기대 레코드 수를 확인하며, 관찰하지 않은 경계와 실패 조건을 README 및 본문에 적는다.

## 글 검증

```sh
python3 labs/observability/otel-practice/validation/validate.py
# Playwright와 Chrome이 있는 Python 환경에서:
python3 labs/observability/otel-practice/validation/validate.py --browser
```

`validation/`에는 구조·레이아웃·이미지 검사, 기존 발행 메타데이터 비교, 독립 퇴고와 원자료 감사 보고서를 둔다. 형식 검사는 기술적 사실 감사를 대신하지 않는다.
