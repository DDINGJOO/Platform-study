# 전환율을 판정하기 전에 확인할 것

Python 표준 라이브러리로 저장된 합성 이벤트를 독립 분석한다. 실제 제품·사람·개인정보는 사용하지 않는다. 자체 HTTP 보고서이며 Netflix/Spinnaker/Grafana 화면을 흉내 낸 것이 아니다. 제품 개선이나 무작위 할당 시스템의 정확성을 증명하지 않는다.

## 실행

Docker Desktop, Python 3.9+가 있으면 저장소 루트에서:

```sh
docker compose -f labs/devops/deployment-experiments/decision/compose.yaml up -d --force-recreate
python3 labs/devops/deployment-experiments/decision/verify.py
cat labs/devops/deployment-experiments/decision/out/results.txt
open http://localhost:28300
```

Docker의 Python 3.12.15에서 실제 분석·14개 회귀 테스트를 실행하고, 저장된 보고서를 HTTP로 제공한다. compose는 실제 실행 이미지 ID와 대조한 `python:3.12.15-slim@sha256:...` digest에 고정했다. 실제 실행 버전은 `out/summary.json`에 기록한다. 추가 pip 패키지는 없다. 컨테이너 192MB 제한이며 이 실습의 `deployment-experiments-03` 프로젝트만 관리한다. 포트는 127.0.0.1:28300이다.

재실행 전의 out은 이 실습 안 `history/시각/`로 이동한다. 이전 결과를 조용히 덮거나 이전 실행을 새 데이터에 합치지 않는다. 고정 fixture를 다시 검증하는 것은 새로운 제품 실험 반복이 아니다. 유리한 fixture만 선택하거나 승자가 나올 때까지 데이터 생성과 분석을 반복하지 않는다.

```sh
# 컨테이너 없이 동일 계산·테스트만 수행할 수도 있다.
python3 labs/devops/deployment-experiments/decision/run.py
# 별도 계산 코드의 테스트만 실행한다.
python3 -m unittest discover -s labs/devops/deployment-experiments/decision -p 'test_*.py'
# 이 실습만 종료한다.
docker compose -f labs/devops/deployment-experiments/decision/compose.yaml down
```

## 사전 계획과 판정 범위

`plan.json`을 fixture 분석 전에 고정한다. 50:50 예정 비율, 각 군 최소 2,000명, 고정 모집 기간 10/1~10/7 미만, 최초 노출 후 24시간의 전환 창, 10/8 이후 1회 분석을 명시한다. 모든 적격 노출 사용자를 포함하며 군별 2,000명을 넘었다고 데이터를 잘라 SRM을 감추지 않는다.

이 2,000명은 판정 경로를 보여 주려는 **사전 최소 표본 예시**다. 검정력 계산으로 정한 수가 아니고, 어떤 효과 크기에 대해서도 80% 검정력을 보장하지 않는다. 실제 표본 계획은 기존 전환율, 탐지하려는 차이, 유의수준, 검정력과 선택한 분석 방법을 함께 고려해야 한다. fixture의 10월 날짜는 합성 사건 시각이며 실험을 일주일간 실제 운영했다는 뜻이 아니다.

판정은 아래 순서다. 모든 gate를 결과에 보존하되 decision은 가장 앞에서 막힌 이유를 표시한다.

1. 한 사용자에게 서로 다른 variant가 기록되면 `INVALID_ASSIGNMENT`.
2. 사전 종료·전환 성숙 시각 전이면 `HOLD_WINDOW`.
3. SRM 근사의 기대 수가 5명 미만이면 `HOLD_SAMPLE`; SRM p<.001이면 `INVALID_SRM`.
4. 각 군의 노출 사용자가 2,000명 미만이면 `HOLD_SAMPLE`.
5. 요청 가드레일 원자료가 없으면 `HOLD_GUARDRAILS`.
6. 오류율·p95 문턱에 걸리면 `STOP_GUARDRAIL`.
7. 관측 전환율 차이가 3pp 미만이거나 Newcombe95 하한이 0 이하면 `HOLD_EFFECT`.
8. 나머지는 `PASS_FIXED_RULES`다. 합성 데이터에서 이 고정 규칙을 통과했다는 뜻이며 실제 제품 승리 선언이 아니다.

3pp는 **관측 점추정치 문턱**이다. 구간 하한>0을 더했다고 실제 효과가 3pp 이상이라고 보장하지 않는다. 예를 들어 +4pp의 구간은 약 +1.99~+6.02pp이므로 실제 효과가 3pp보다 작은 가능성도 배제하지 않는다.

## 사용자 분모와 데이터 품질

분모는 기간 안 최초 `exposure`가 있는 고유 user_id다. 분자는 그 최초 노출 이후 24시간 안에 `conversion`이 한 번 이상 있는 고유 user_id다. 같은 사용자의 여러 전환은 한 번만 센다. event_id가 같은 재시도, 새 event_id로 반복된 노출·전환도 각각 제거한다. 진입(entry)만 한 사용자, 스팬·로그·요청 개수는 전환율 분모가 아니다.

가드레일은 같은 적격 사용자의 전환 관찰 창 안 `request` 이벤트를 request_id로 dedup하여 집계한다. 오류율≤1%, 각 군 p95≤250ms, B p95≤A p95×1.2가 이 실습의 정책이다. p95는 정렬 후 ceil(.95*n)번째인 nearest-rank다. 요청별 가드레일은 사용자별 전환율과 분모가 다르다. 가드레일 통과는 **관측값 정책 충족**이며 통계적 비열등성이나 무해성을 증명하지 않는다.

2편 기본 export 계약을 따른다: schema_version=1, experiment_id, events[]. 각 event는 event_id(문자열/정수), experiment_id, user_id, variant(A/B), event_type, request_id, occurred_at(UTC ISO8601)을 갖는다. 이 실습 fixture는 event_type=request일 때 boolean `error`와 수치 `latency_ms`를 추가한다. 2편 서비스에 이 확장을 요구하지 않는다.

## SRM은 어느 단계의 비율인가

기본 fixture의 SRM은 **분석 대상 최초 노출 사용자의 모집 비율 검사**다. 기대 수는 전체 노출 사용자×사전 비율(.5)이다. Pearson χ²=Σ(O−E)²/E와 자유도1의 상측 확률 `erfc(sqrt(χ²/2))`를 사용한다. 연속성 보정은 하지 않는다. 기대 수가 5 미만이면 이 근사로 판정하지 않는다. 임계값 .001은 이 실습의 사전 정책이지 모든 회사에 같은 기준이 있다는 뜻이 아니다.

이는 무작위 배정 사용자 수를 검사한 **할당 단계 SRM**과 다르다. 노출 누락·후속 선택도 불균형을 만들 수 있다. 실무에서는 할당과 노출의 비율을 따로 보고, B가 노출 여부를 바꾸는 처치 후 선택이 있다면 노출 사용자만의 분석이 선택 편향을 만들 수 있다. ITT(배정된 전체 사용자 기준)와 적격 노출의 정의를 사전에 정해야 한다. 노출 수가 같다는 사실만으로 무작위 할당이나 인과 추론의 전제를 확인할 수 없다.

## 공식과 불확실성

각 군의 Wilson95는 `analysis.wilson()`으로 계산한다. Newcombe95는 독립 두 이항 표본의 Wilson 구간을 조합하는 연속성 보정 없는 hybrid score 방법이다. 차이는 B−A이며, A의 Wilson 구간을 [LA,UA], B를 [LB,UB]라고 하면:

```text
L = (pB-pA) - sqrt((pB-LB)^2 + (UA-pA)^2)
U = (pB-pA) + sqrt((UB-pB)^2 + (pA-LA)^2)
```

실험·사용자 간 독립성 같은 전제를 요구하는 **명목 95% 근사 구간**이다. 유한 표본에서 정확히 95% coverage를 보장한다고 쓰지 않는다. 한 번 계산한 두 군의 전환율을 비교하는 것이며, 여러 지표·여러 variant·중간 시점 반복 확인에 대한 다중 검정/순차 분석은 구현하지 않는다. 중간 결과가 유리할 때 멈추려면 사전 설계한 순차 분석 등이 필요하다.

## 원자료와 재검

- `fixtures.json`: 다섯 고정 입력 조건과 기대 gate 경로.
- `out/events/*.json.gz`: 실제 생성·분석한 전체 이벤트 원자료. deterministic gzip(mtime=0).
- `out/summary.json`: 실행 버전·시각·사전 계획·observed/expected·효과·구간·gate·dedup·원자료 SHA256. 통계 소수는 실제 계산 정밀도를 보존하며 화면에서만 읽기 쉽게 반올림한다.
- `out/tests.txt`, `out/results.txt`: 실제 회귀 테스트와 사람이 읽는 실행 결과.
- `out/index.html`: 저장된 summary를 렌더링한 자체 보고서.

각 fixture에 의도적으로 event-id 재시도20개, 반복 노출20개, 반복 전환10개, request-id 중복10개, 시간 조건을 벗어난 전환4개를 포함했다. 독립 계산이 이를 제외하고 의도한 사용자 수와 전환 수를 반환하는지 assert한다. 테스트는 Wilson 수치·0/100% 경계·SRM NIST 표 기준값·차이 구간의 방향·종료 전 보류·표본 부족·동일 사용자 교차 할당·가드레일 결측·ID 충돌 등을 확인한다.

## 2편 실제 HTTP 이벤트 연결 (선택)

2편을 실행한 뒤 아래 명령으로 export를 **읽기 전용** 대조할 수 있다. 기본 fixture 실행에는 필요하지 않다.

```sh
python3 labs/devops/deployment-experiments/decision/integrate.py labs/devops/deployment-experiments/sticky-ab/out/events.json
```

복사한 원자료는 `out/source-events.json.gz`, 독립 집계는 `out/source-integration.json`에 보존한다. 할당 단계 SRM과 노출 단계 SRM 진단을 각각 기록한다. 실제 확인한 소스는 A202/B198명 배정, 노출160/160명, 전환46/37명이었다. 전환율은 46/160=28.750%, 37/160=23.125%다. 소수 둘째 자리에서는 화면별 반올림 규칙으로 23.12% 또는 23.13%가 보일 수 있다. 이 노출 부분집합은 2편 실습 스크립트가 선택했다. 이를 무작위 제품 실험의 인과 효과로 해석하지 않는다. 이 소스에 대한 사전 분석 계획·성숙한 결과 창·가드레일이 없으므로 `DESCRIPTIVE_ONLY`이며 합성 fixture의 날짜를 사후에 바꿔 통과시키지 않는다.

## 실제 화면 캡처

```sh
/Users/dding/.local/share/tistory-uploader/venv/bin/python labs/devops/deployment-experiments/decision/capture.py
```

Playwright와 Chrome이 있는 Python에서 실행한다. HTTP 자체 보고서에 실제 다섯 결과가 표시되는지 확인한 뒤 DOM 전체를 마스킹 검사하고 캡처한다. stdout 이미지도 추적된 `.claude/skills/blog-post-pipeline/assets/term-shot.py`에서 텍스트를 먼저 검사한다. 저장 위치는 `posts/CS/DevOps/deployment-experiments/images/lab-03/`다. `.codex` 로컬 스킬 심볼릭 링크를 실행 의존성으로 사용하지 않는다.

## 확인한 1차 자료

2026-10-23 확인. 인용문을 길게 복사하지 않고 설명과 수식 구현을 대조했다.

- [Microsoft Research: Diagnosing SRM](https://www.microsoft.com/en-us/research/articles/diagnosing-sample-ratio-mismatch-in-a-b-testing/): SRM을 효과 해석 전 데이터 품질 문제로 다루는 원칙.
- [Microsoft PlayFab: Experimentation best practices](https://learn.microsoft.com/en-us/xbox/playfab/live-service-management/game-configuration/experiments/experimentation-keys): 예정 비율 대비 observed 차이, 누락·중복과 SRM.
- [NIST χ² 임계값 표](https://www.itl.nist.gov/div898/handbook/eda/section3/eda3674.htm): df1, 3.841에서 상측 약 .05를 테스트 기준으로 사용.
- [NIST Wilson 설명](https://www.itl.nist.gov/div898/handbook/prc/section2/prc241.htm), [영국 OHID 공식 수식](https://fingertips.phe.org.uk/static-reports/public-health-technical-guidance/Basic_statistics/Proportions.html): 단일 비율 Wilson score 수식.
- [Newcombe 1998 원논문 초록](https://pubmed.ncbi.nlm.nih.gov/9595617/): 독립 비율 차이에 Wilson 구간을 조합하는 방법.
- [statsmodels 0.15.0 공식 구현](https://www.statsmodels.org/stable/_modules/statsmodels/stats/proportion.html#confint_proportions_2indep): `method=newcomb, compare=diff` 수식을 실제 대조. 라이브러리를 런타임 의존성으로 추가하지 않음.
- [ASA 공식 성명](https://www.amstat.org/asa/files/pdfs/p-valuestatement.pdf): p값 하나로 의사 결정하거나 효과 크기로 해석하지 않기.
