# ts-03-log-templates: 정상 구간과 장애 구간의 로그를 템플릿으로 묶어 비교한다

트러블슈팅 실습-3의 코드입니다. 같은 이미지의 인스턴스 둘이 로그를 찍고, 그중 하나만 뒤쪽 5분 동안 장애 문장을 섞습니다.
로그 10만 줄을 Drain3(기본 설정, 마스킹 설정)와 Loki pattern ingester로 각각 템플릿으로 묶어,
장애 구간에만 나온 템플릿을 고르고, 그 템플릿에서 소스 위치까지 검색을 몇 번 하는지 셉니다.
두 인스턴스의 환경변수와 설정 파일 diff도 함께 뽑습니다.

## 구성

| 서비스·파일 | 하는 일 |
|---|---|
| `app-healthy`, `app-broken` | `app/gen.py`. `shop-src/`의 자바 소스에서 `log.xxx("...")` 문장 29개를 읽어, 형식 문자열에 값(UUID, 사용자 이름, IP, 숫자)을 채워 Spring Boot 기본 형식으로 표준 출력에 찍는다. DEBUG 문장(3개)은 찍지 않는다. 앞 `NORMAL_SECONDS` 동안은 둘 다 평소 비중으로, 뒤 `INCIDENT_SECONDS` 동안은 `FAULT=1`인 `app-broken`만 장애 문장 4종을 섞고 캐시 미스 비중을 올린다. 구간 경계 시각은 `out/phase-<인스턴스>.json`에 남긴다 |
| `config/healthy.yaml`, `config/broken.yaml` | 두 인스턴스에 마운트하는 설정 파일. 풀 크기, 주소 서비스 URL·타임아웃, 캐시 TTL이 다르다. 생성기는 이 파일을 읽지 않는다(diff 대상으로만 쓴다) |
| `alloy` | 도커 소켓으로 이 compose 프로젝트의 앱 컨테이너 로그만 읽어 Loki로 보낸다. 라벨은 `service_name="shop"`, `instance=<서비스 이름>` |
| `loki` | Loki 3.7.8 단일 바이너리. `pattern_ingester.enabled: true` |
| `grafana` | 확인용. Logs Drilldown의 Patterns 탭에서 같은 패턴을 볼 수 있다 |
| `analyze.py` | Loki에서 로그를 꺼내 Drain3로 묶고, Loki 패턴 API 결과와 같은 기준으로 비교하고, 소스 검색 횟수와 env·설정 diff를 센다. 단계는 파일 첫머리 docstring에 있다 |
| `offline.py` | `out/drain-*.tsv`만 읽어 다시 센다(Docker 불필요). 캐시 미스 비중 네 칸, 분모를 고치기 전 방식의 결과, 기본 설정 템플릿과 마스킹 템플릿으로 한 소스 검색 비교 |

호스트 포트: Loki 35100, Grafana 35000 (`LOKI_PORT`, `GRAFANA_PORT`로 바꾼다).

## 돌리기

```bash
cd labs/observability/ts-03-log-templates
python3 -m venv .venv && .venv/bin/pip install drain3==0.9.11   # .venv 는 .gitignore
docker compose up -d --build
# 10분(정상 300초 + 장애 300초) 기다린다. 끝나면 out/phase-*.json 에 "lines" 가 생긴다
caffeinate -i sleep 630
.venv/bin/python analyze.py        # 스택이 떠 있을 때. 2초 안팎
.venv/bin/python offline.py        # 보조 계산. out/offline.txt
docker compose down -v
```

생성 속도와 구간 길이는 환경변수로 바꾼다: `RATE`(인스턴스당 초당 줄 수, 기본 85), `NORMAL_SECONDS`, `INCIDENT_SECONDS`(기본 각 300).
Loki 패턴은 최근 3시간 로그에서만 나오므로, 생성이 끝나고 3시간 안에 `analyze.py`를 돌린다.

## 결과 파일 (`out/`)

- `analysis.txt` 요약(아래 숫자는 전부 여기서 나온다)
- `drain-default.tsv`, `drain-masked.tsv` 템플릿별 줄 수(구간 x 인스턴스)와 그 템플릿에 들어간 소스 문장
- `loki-patterns.tsv` 인스턴스별 패턴과 정상 구간 / 경계 칸 / 장애 구간 줄 수
- `search.tsv` 장애 구간 템플릿마다 시도한 검색과 결과(마스킹 설정 템플릿 기준)
- `offline.txt` `offline.py` 결과
- `loki-metrics.txt` pattern ingester 지표(학습한 줄, 버린 줄, 질의에서 잘린 패턴). 이 기능을 넣은 뒤 실행부터 생긴다. 글의 지표 값은 첫 번째 실행 직후 `/metrics`를 손으로 열어 본 값이다
- `env-diff.txt` 두 컨테이너의 환경변수 diff와 설정 파일 diff
- `run1/` 첫 번째 실행의 같은 파일들(두 번째 실행과 비교용). `analysis-v1.txt`, `analysis-v2.txt`는 분석 스크립트를 고치기 전 출력이다(아래 함정 참고. v2는 끝에서 예외로 멈췄다)

유닉스 시각이 든 `phase-*.json`은 `.gitignore`로 뺐다.

## 버전

Loki 3.7.8, Alloy v1.20.1, Grafana 13.2.3, Drain3 0.9.11, Python 3.9.6(분석), python:3.12-slim(생성기), Docker 29.5.3, macOS(Apple M5 Pro).

## 돌리다 만난 함정

- 처음 분석 스크립트는 Loki 패턴의 10초 표본을 표본 시각만 보고 정상·장애로 나눴다. 경계가 10초 칸 한가운데 있어서 장애 문장 수십 줄이 "정상 구간"으로 들어갔고, 고장 인스턴스에서 "장애 구간에만 나온 패턴"이 0개로 나왔다. 경계가 걸친 칸을 따로 빼자 4개가 됐다
- 패턴과 소스 문장의 대응을 처음에는 문장마다 앞 세 줄만 표본으로 골라 맞췄다. 세 줄이 한 인스턴스에서만 나오거나 특정 주 이름이 든 패턴과 안 맞아 "어떤 문장에도 맞지 않는 패턴"이 58개로 부풀었다. 모든 줄을 패턴에 맞춰 보도록 바꿨다
- Loki 패턴 API는 질의 범위 안에서 합계가 30줄 미만인 패턴을 응답에서 뺀다(`pkg/pattern/ingester_querier.go`의 `minClusterSize = 30`). 메서드·경로마다 패턴이 따로 생긴 `Rejected request` 문장 566줄과 드문 `Error loading State Index` 15줄이 이 때문에 어떤 패턴에도 들어가지 않았다
- 생성기가 끝날 때 표준 에러로 찍는 `done: N lines`도 Alloy가 도커 로그로 가져간다. 장애 구간 끝에 한 번 찍히니 "장애 구간에만 나온 템플릿"으로 잡힌다. 같은 시각의 정상 인스턴스에도 있다는 것으로 걸렀다. 지우지 않고 남겨 둔 건 실제 서비스의 종료·재시작 문장도 같은 식으로 끼기 때문이다
- 생성기가 초당 줄 수를 고정하므로, 장애 문장이 끼면 나머지 문장의 비중이 고르게 줄어든다. 처음에는 거의 모든 템플릿이 "비중이 1.5배 넘게 바뀐 템플릿"으로 나왔다. 비중의 분모를 정상 구간에도 있던 템플릿의 줄로만 잡도록 바꿨다
- 소스 검색을 기본 설정 템플릿으로 하면 `5000 ms (endpoint http://address-legacy:8080` 같은 실제 값이 고정 조각에 섞여 네 개 중 두 개가 0건이다. `analyze.py`의 검색은 마스킹 템플릿 기준이고, 두 설정 비교는 `offline.py`가 한다
