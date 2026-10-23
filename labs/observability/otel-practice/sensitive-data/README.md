# Collector 마스킹과 HTTP 전파 경계 실습

회사 자료·실제 개인정보를 사용하지 않는다. `PRIVATE_CUSTOMER_ALPHA`는 사람이 아닌 인위적인 표식이다. 이메일/전화번호 탐지 성능을 측정하지 않는다. `.mask-allow` 변경도 없다.

## 실행

Docker Desktop과 Python 3.9+가 필요하다. 저장소 루트에서:

```sh
python3 labs/observability/otel-practice/sensitive-data/run.py
cat labs/observability/otel-practice/sensitive-data/out/results.txt
```

스크립트는 **이 실습의 `otel-practice-04` 프로젝트만** 내리고 다시 시작한다. 기존 out은 `out-history/실행시각`에 보관한다. Tempo/Loki는 컨테이너 안 임시 저장소를 사용하므로 새 실행에 과거 자료가 혼입되지 않는다. 다른 프로젝트나 Docker 전역 자원은 건드리지 않는다.

- front: http://localhost:27480/health
- Grafana: http://localhost:27400/d/privacy-boundaries
- Tempo: http://localhost:27420/ready
- Loki: http://localhost:27410/ready
- 정리: `docker compose -f labs/observability/otel-practice/sensitive-data/compose.yaml down`

모든 호스트 포트는 127.0.0.1에만 바인딩한다. Grafana 익명 Admin은 로컬 실습용이다. 공개 배포 설정이 아니다.

## 버전과 계측

Python 3.12, OpenTelemetry Python SDK 및 OTLP gRPC exporter 1.39.1, Collector contrib 0.162.0, Tempo 2.10.8, Loki 3.7.8, Grafana 13.2.3. 직접 SDK로 HTTP server/client span과 Python logging OTLP export를 작성한다. Java agent 자동 계측과 비교하는 실습은 3편이다.

`SimpleSpanProcessor`와 `SimpleLogRecordProcessor`를 쓰므로 전송이 요청 경로를 지연시킨다. 재현을 단순하게 하기 위한 선택이며 운영 처리량이나 큐 성능은 측정하지 않는다. 로그는 동일 Python logger의 OTel handler와 console handler 양쪽으로 보낸다.

## 모드와 관찰

각 모드에 동일 baggage를 단 HTTP 요청 3개를 보내고 9개 고유 span / 3개 trace / 3개 exception event / 6개 log를 검증한다. `lab.run`과 `lab.mode`로 구분한다.

| 모드 | Producer | Collector traces | Collector logs |
|---|---|---|---|
| raw | 표식 생성·전파 | 그대로 | 그대로 |
| narrow | 표식 생성·전파 | `synthetic.customer` span 속성만 삭제 | 그대로 |
| scrubbed | 표식 생성·전파 | span 속성 삭제, status.message 및 exception.message 표식 치환, exception.stacktrace 삭제 | 속성 삭제·string body 표식 치환 |
| minimized | source에서 표식 기록 생략, baggage는 tier만 허용 | scrubbed와 동일 | scrubbed와 동일 |

예외 이벤트의 `exception.stacktrace`는 통째로 지우므로 디버깅 정보가 줄어든다. 예외 종류와 치환한 message는 남긴다. 이 선택이 모든 서비스에 맞는다는 주장이 아니다. `error_mode: propagate`는 변환 실패를 조용히 통과시키지 않으려는 설정이다. 오류 발생 시 해당 payload 전송도 실패할 수 있으므로 운영에서는 손실·재시도·경보 정책을 함께 검토한다.

baggage는 자동으로 span 속성이 되지 않는다. 이 서비스는 `synthetic.customer`를 코드로 직접 만든다. `private.customer`는 별도로 HTTP 헤더 전파 및 downstream 응답으로 확인한다. minimized에서는 허용한 `tier=gold`와 trace context가 계속 전달되는지도 확인한다.

## 증거

- `out/summary.json`, `out/results.txt`: 실행 시각·버전·모드별 검증 수치
- `out/python-packages.txt`: 실행한 컨테이너의 실제 pip freeze 결과
- `out/{raw,narrow,scrubbed}-{traces,logs}.jsonl`: 각 Collector pipeline **처리 후** file exporter 원자료. scrubbed 파일에는 minimized도 들어 있고 resource.lab.mode로 구분한다. raw 파일은 대조군의 원본 표식을 보존한다.
- `out/http-responses.json`: downstream이 받은 실제 HTTP baggage, 요청별 trace ID
- `out/source-console.txt`: Collector를 거치지 않은 source console 출력. scrubbed에서도 표식이 남는 증거
- `out/tempo-traces.json`: 관측한 trace ID로 실제 Tempo API를 조회한 12개 trace. 각 trace span 3개를 polling하여 확인
- `out/loki-*.json`: Loki API로 조회한 모드별 로그 6개

raw·narrow의 기존 데이터는 같은 실행 안에서 Tempo/Loki에 일부러 유지한다. scrubbed 조회 결과가 깨끗하다고 raw의 과거 레코드가 삭제된 것은 아니다. 글의 수치는 모드별 신규 레코드 범위를 뜻한다. 저장소 삭제 API나 historical erasure는 실험하지 않는다.

검증은 기대 record 수와 trace ID 집합으로 polling하며 고정 sleep 후 성공이라고 간주하지 않는다. 모든 log trace ID가 보낸 trace 집합에 속하는지, full Tempo trace의 span 수가 3인지도 assert한다. 이 실습은 알려진 문자열의 정의된 경로만 검사한다. resource/scope 속성, span link, 구조화된 log map/array, URL·DB 문장·메트릭 label 등은 따로 설계해야 한다.

## 화면 캡처

```sh
/Users/dding/.local/share/tistory-uploader/venv/bin/python labs/observability/otel-practice/sensitive-data/capture.py
```

실제 Grafana Loki 패널 네 개를 연다. 각 모드의 로그가 표시되고 오류/no data 문구가 없는지 검사한 뒤 DOM 텍스트를 mask-check와 같은 일반 패턴으로 스캔한다. 합성 trace ID 등의 오탐을 글로벌 허용 목록에 추가하지 않는다. 터미널 이미지는 검증 스크립트가 남긴 `out/results.txt`를 같은 검사 후 렌더링한다. 이미지 경로는 글의 `images/lab-04/`다.

캡처 스크립트는 저장소에서 추적하는 `.claude/skills/blog-post-pipeline/assets/`의 `term-shot.py`와 `mask-check.py`를 사용한다. 로컬 `.codex` 심볼릭 링크가 없어도 캡처 도구를 찾을 수 있다.

## 기술 근거

- [Collector 0.162.0 Transform processor](https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/v0.162.0/processor/transformprocessor/README.md): span/spanevent/log 문맥 분리, error_mode, replace_pattern/delete_key.
- [Collector 0.162.0 attributes processor](https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/v0.162.0/processor/attributesprocessor/README.md): attribute delete의 적용 범위.
- [OpenTelemetry handling sensitive data](https://opentelemetry.io/docs/security/handling-sensitive-data/): 가능한 수집하지 않기와 Collector의 후처리 구분.
- [OpenTelemetry Baggage](https://opentelemetry.io/docs/concepts/signals/baggage/): 전파, 개인정보 위험, span 속성과의 독립성.
- [Python SDK v1.39.1](https://github.com/open-telemetry/opentelemetry-python/tree/v1.39.1): trace/log exporters와 context/baggage API.
- [Loki OTLP ingestion](https://grafana.com/docs/loki/latest/send-data/otel/): OTLP 로그 수신 경로와 기본 service.name label 정규화.

2026-10-23에 문서와 고정 버전 설정을 확인하고 실제 실행했다. 최신 문서가 설명한 전체 기능을 검증했다는 뜻은 아니다.
