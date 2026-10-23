# 배포 관측과 A/B 실험 독립 원자료 감사

작성자 및 네 관점 퇴고자와 분리된 감사자가 코드·설정·원시 이벤트·저장된 실행 결과·실제 PNG를 직접 대조했다. 원자료와 글은 수정하지 않았으며 실습을 재실행하거나 데이터를 추가하지 않았다.

## 현재 판정

**전체 3편 PASS: 확인 38건 / 불일치 0건 / 확인 불가 0건 / 과장 0건.**

편별 확인: 1편 12건, 2편 12건, 3편 14건. 기존 2편 감사 기록은 보존했고, 추가된 125자 lead도 같은 합성 HTTP·저장·재시도·재기동·Grafana 근거 범위 안에 있음을 재확인했다.

## 2편: 고정 할당과 사용자 분모

대상 글: `posts/CS/DevOps/deployment-experiments/02_2편 - A·B 테스트 사용자는 새로고침해도 같은 그룹이어야 한다.html`

아래 상대 경로는 `labs/devops/deployment-experiments/sticky-ab/` 기준이다.

| ID | 판정 | 검증한 주장 | 직접 대조한 근거 |
|---|---|---|---|
| 02-01 | 확인 | SHA-256의 앞 8바이트를 big-endian으로 읽어 10000으로 나누고 5000 미만을 A로 배정한다. | `app.py:bucket`의 UTF-8 JSON 배열 직렬화와 서버의 임계값을 확인했다. 저장된 실험 ID·salt·400개 사용자 입력으로 감사자가 독립 재계산해 `out/events.json.assignments`의 bucket·variant 전부와 대조했다. |
| 02-02 | 확인 | 50:50 설정의 실제 할당은 A 202명/B 198명이다. | 고유 사용자 400명과 할당 레코드 400개를 확인하고 variant별 직접 집계했다. `out/summary.json.variants` 및 실제 PNG와 일치한다. 정확히 반반이 된다고 주장하지 않는다. |
| 02-03 | 확인 | 할당 400명, 노출 320명, 전환 83명을 구분한다. | `out/events.json`의 803개 이벤트를 사용자·유형별로 재집계했다. A/B 노출은 각각 160명, 전환은 46명/37명이다. 모든 전환 사용자에게 먼저 기록된 진입·노출이 있고 event ID 및 시각 순서도 일치한다. |
| 02-04 | 확인 | 같은 사용자의 반복 이벤트는 사용자·실험·이벤트 종류로 한 번만 센다. | `app.py`의 UNIQUE 제약, `BEGIN IMMEDIATE`, `INSERT OR IGNORE`를 확인했다. 실제 저장 이벤트의 `(experiment_id,user_id,event_type)` 조합 803개가 모두 고유하며 variant는 저장 할당과 일치한다. request ID를 중복 제거 키로 사용하지 않는다. |
| 02-05 | 확인 | 진입 제출 1600회·노출 제출 640회·전환 제출 166회는 각각 고유 사용자 400명·320명·83명이다. | `run.py`에서 사용자당 네 번의 진입, 대상 사용자당 두 번의 노출·전환 제출과 응답 assert를 확인했다. `out/summary.json.accepted_event_attempts`, `out/results.txt`, Grafana 및 출력 PNG가 일치한다. |
| 02-06 | 확인 | 새로고침과 앱 재기동 후 400명의 그룹과 사용자 이벤트가 유지됐다. | `run.py`가 실제 `compose restart app` 전후 전체 export를 비교하고 이후 400명 재진입의 variant 및 export 동일성을 assert한다. `out/summary.json.checks`와 저장된 실제 실행 출력이 통과를 기록한다. 최종 400개 할당도 고정 입력의 해시 결과와 일치한다. |
| 02-07 | 확인 | salt 변경 시 182명의 그룹이 바뀌며 기존 실험의 설정 변경 기동을 거부한다. | 감사자가 동일 400명과 변경 salt로 독립 계산해 182명 재확인. `app.py:initialize`의 설정 저장·비교 및 실제 별도 기동을 수행한 `run.py`를 대조했다. `out/salt-rejection.txt`에 예상 RuntimeError와 비정상 종료가 남아 있다. |
| 02-08 | 확인 | 식별자 누락·클라이언트 그룹 지정은 400, 선행 진입 없는 노출·선행 노출 없는 전환은 409다. | `app.py`의 실제 입력·순서 검사 분기와 `run.py`의 네 실제 HTTP 요청/상태 assert, `summary.checks`, 결과 출력이 일치한다. 거절 경로는 accepted attempts 증가 전에 반환한다. |
| 02-09 | 확인 | 사용자 집합은 gauge, 수락 제출은 counter이며 사용자/요청 ID를 레이블에 넣지 않는다. | `app.py:/metrics`의 출력 타입과 레이블, `run.py`의 실제 응답 검사, `prometheus.yaml`의 1초 수집 설정을 직접 확인했다. 실험 식별자의 장기 cardinality 문제도 본문이 별도로 한정한다. |
| 02-10 | 확인 | 노출 사용자 분모의 비율은 46/160=28.75%, 37/160=23.125%다. | 원시 이벤트로 분자·분모를 재계산했다. 대시보드 PromQL은 `conversion / ignoring(stage) exposure`이며 실제 PNG는 B 23.13%, Python 결과 PNG는 B 23.12%로 표시한다. 본문이 반올림 표시 차이를 명시한다. |
| 02-11 | 확인 | 실제 Grafana 수집 화면이며 그룹별 노출 160명을 강제로 맞추지 않았다. | `run.py`의 노출 조건은 사용자 번호에만 의존한다. `out/summary.json.prometheus_evidence`의 A/B 160과 대시보드 설정·`out/grafana-dom.txt`·실제 `grafana-users.png` 및 출력 PNG의 동일 실험 ID/집계가 일치한다. |
| 02-12 | 확인 | 이 수치는 제품 효과·통계적 승자 증거가 아니며 노출 조건부 집계의 편향 가능성을 남긴다. | `run.py`에서 그룹에 따라 다른 사용자 번호 조건으로 합성 전환을 생성한다. 글은 실사용자 반응, 실제 브라우저 노출 검증, SRM·표본 계획·보호 지표 판정을 수행했다고 주장하지 않는다. 노출 사용자 집계와 할당 전체 분석이 다르고, 처리에 영향을 받는 노출로 조건화하면 편향될 수 있음을 명시한다. |

### 공식 자료 직접 확인

- [Unleash stickiness](https://docs.getunleash.io/concepts/stickiness): 문맥 입력과 group ID를 사용하는 결정적 할당, MurmurHash 및 입력 변경 시 재할당 설명을 확인했다. 글은 자체 SHA-256 실습과 Unleash 실행을 구분한다.
- [Netflix 실험 플랫폼 소개](https://netflixtechblog.com/its-all-a-bout-testing-the-netflix-experimentation-platform-4e1ca458c15): 할당된 구성원 모두가 대상 경험을 접하는 것은 아니라는 설명을 확인했다. 글은 당시 공개 설명을 인용하며 Netflix 내부 플랫폼을 실행했다고 주장하지 않는다.
- [Prometheus 레이블 지침](https://prometheus.io/docs/practices/naming/): 사용자 ID 등 높은 cardinality 레이블을 피하라는 지침이 본문 인용과 일치한다.

### 검증의 범위와 증거 한계

현재 감사에서는 보존된 이벤트와 실행 프로그램의 assert 및 실제 저장 출력·화면을 대조했다. 원 실행의 재기동 전 export 별도 사본이나 HTTP 응답 전체가 보존된 것은 아니므로 과거 실행을 새로 관측했다고 표현하지 않는다. 스택을 재기동해 이벤트를 다시 전송하지 않았으며, 기존 저장 증거를 교체하지 않았다.

고정 할당 400개와 변경 salt의 재할당 수, 이벤트 고유성·순서·집계·분모는 원시 데이터에서 독립 재계산했다. 재기동 및 HTTP 거절의 원 실행 주장은 실제 실행기의 검증 코드와 저장된 통과 결과·기동 실패 로그에 근거한다. 단일 노드의 합성 이벤트 실습이라는 범위에서 추가 수정 요구는 없다.


## 1편: 실제 Kayenta와 새 베이스라인

대상 글: `posts/CS/DevOps/deployment-experiments/01_1편 - 오래된 A 대신 새 베이스라인 A′와 B를 비교한다.html`. 상대 경로는 `canary/` 기준이다.

| ID | 판정 | 검증한 주장 | 직접 대조한 원자료·코드 근거 |
|---|---|---|---|
| 01-01 | 확인 | A는 먼저 띄운 로컬 v1이며 A′/B는 새 복제본이다. | `run.py:main`, 두 `out/*-start-metadata.json`에서 old 캐시 128, 새 두 프로세스 캐시 0, 버전 및 시작 시각을 확인했다. 장기 운영 서비스로 주장하지 않는다. |
| 01-02 | 확인 | 같은 코드도 초기 캐시 상태로 약 13ms/78ms 차이를 보인다. | `service.py`는 실제 set 캐시 miss에 65ms를 더 sleep하고 perf_counter로 실측한다. 동일 버전 cold diagnostic 11지점의 평균 old 13.1834087 / baseline 78.4482048ms를 원시 series에서 대조했다. 외부 DB·Kayenta 오탐 재현이라고 주장하지 않는다. |
| 01-03 | 확인 | B v2는 같은 이미지에 실제 40ms 지연을 주입했다. | `service.py`의 REGRESSION_MS, `compose.yaml`, 저장된 containers의 image_id·환경 및 metadata와 실제 HTTP duration을 확인했다. 버전 라벨과 지연 설정만 변경한 합성 회귀다. |
| 01-04 | 확인 | 두 새 복제본의 자원·시작·키·부하를 맞췄다. | 두 containers에서 동일 이미지·0.5 CPU·96MiB, 시작 차이 0.013744/0.018017초. Load는 같은 128키를 각 0.25초 간격으로 요청한다. 두 측정 창 각각 양쪽 HTTP 관측 480건, cache_miss 0을 재확인했다. |
| 01-05 | 확인 | warmup 46초 후 같은 절대 120초 창을 사용한다. | `run.py`의 캐시 128 확인·46초 대기·시작/종료 선택, 두 analysis-request의 control/experiment start/end/step 동일성. Prom 수집 및 조회 간격 2초, 양쪽 61지점이다. |
| 01-06 | 확인 | 실제 official Deck/Gate/Kayenta/Front50와 Prom/Grafana를 실행했다. | digest 고정 Compose와 runtime 기록, 저장된 browser responses/DOM 및 4개 PNG 직접 시각 대조. 감사 시 28100~28105 각각 HTTP 200. Gate의 두 run ID 결과 점수도 저장 judge와 일치했다. |
| 01-07 | 확인 | Compose가 배포하고 embedded Orca가 분석한다. | `run.py`의 compose up/recreate와 Kayenta /canary POST, local 설정의 Redis·memory·Prom 계정. 외부 Orca/Echo/Clouddriver 배포 경로가 없으며 본문은 클라우드 배포·승격·자동 롤백을 수행했다고 주장하지 않는다. |
| 01-08 | 확인 | Kayenta가 실제 Prom 입력을 조회하고 NetflixACAJudge로 판정했다. | 저장된 query log에서 Kayenta container IP의 실제 PromQL/start/end/step을 확인. 4개 metric-pair 입력 배열 각각 61값이 저장 Prom 원시값과 일치하고 live Gate 결과도 일치했다. Python 판정 모조 구현이 없다. |
| 01-09 | 확인 | 20% 기준과 critical 설정은 점수·통계 유의성과 구분된다. | `config/canary-config.json` meanRatio allowedIncrease/criticalIncrease 1.20, critical=true, latency weight100. 고정 소스와 공식 judge 문서의 통계 분류+effect gate+critical score0 규칙을 대조했다. score100을 신뢰도100%로 해석하지 않는다. |
| 01-10 | 확인 | 같은 v1은 100/Pass, +40ms는 0/Fail이다. | 원시 61개씩 평균으로 same 13.000992/13.005005, regression 13.483824/53.807055ms를 확인. saved judge 및 live Gate 점수·Pass/HighCritical와 실제 두 Deck PNG의 시간·비율·점수가 일치한다. |
| 01-11 | 확인 | 지연은 서버 내부 평균이며 61지점은 독립 사용자 수가 아니다. | service 타이머의 범위와 PromQL sum(rate(sum[10s]))/sum(rate(count[10s])) 직접 확인. 겹치는 10초 창, 단일 복제본, 짧은 관측, p99/제품 안전성 보장 부재를 본문이 명시한다. |
| 01-12 | 확인 | 첫 실행 소문자 상태 처리 문제와 현재 수정·보존 증거가 있다. | `history/*/same-version-completed-before-retry.json` complete=true/status=succeeded, 현재 run.py 종료 처리의 .upper(), 이후 확정 두 결과를 대조했다. history는 읽기만 했고 교체하지 않았다. |

### 새로 실행한 읽기 검증과 반례

`verify.py`는 마지막에 results.txt를 쓰므로 원문을 직접 실행하지 않고, 메모리에서 그 쓰기 호출만 제거해 나머지 전체 assert 및 live Gate GET을 실행했다. 네 입력 배열·쿼리 출처·HTTP 건수·이미지/자원·실제 판정 검증이 모두 통과했다. 저장 파일과 실험 상태는 바꾸지 않았다.

반례로 '비율이 1.20만 넘으면 반드시 실패', '50지점이면 독립성 확보', '100점이면 안전 확률100%', '같은 시작이면 모든 운영 조건 동일', '전체 Spinnaker 배포 수행'을 찾았다. 본문은 통계 분류와 effect 조건을 함께 설명하고 겹치는 지점·짧은 단일 복제본·관측 지표 한계를 남기므로 해당 과장에 해당하지 않는다. warmup 중 기존 A와 새 A′의 차이는 진단 창이지 Kayenta의 잘못된 판정을 실제 실행한 증거가 아니다.

공식 자료: [Netflix A/새 baseline/canary 설명](https://netflixtechblog.com/automated-canary-analysis-at-netflix-with-kayenta-3260bc7acc69), [Spinnaker 비교 조건과 최소 지점 권고](https://spinnaker.io/docs/guides/user/canary/best-practices/), [judge 분류·effect·가중 점수](https://spinnaker.io/docs/guides/user/canary/judge/), [고정 standalone/embedded Orca 문서](https://github.com/spinnaker/spinnaker/blob/a59b1887bb66ae3e5d92b98782abbde7e2eef70e/kayenta/docs/kayenta-standalone.md), [고정 NetflixACAJudge 소스](https://github.com/spinnaker/spinnaker/blob/a59b1887bb66ae3e5d92b98782abbde7e2eef70e/kayenta/kayenta-judge/src/main/scala/com/netflix/kayenta/judge/NetflixACAJudge.scala)를 직접 조회했다. 공식 장시간·다중 지표 권고 전체를 재현한 것으로 판정하지 않는다.

## 3편: 고정 창과 사용자 단위 판정

대상 글: `posts/CS/DevOps/deployment-experiments/03_3편 - 전환율이 높아도 표본과 가드레일부터 확인한다.html`. 상대 경로는 `decision/` 기준이다.

| ID | 판정 | 검증한 주장 | 직접 대조한 원자료·코드 근거 |
|---|---|---|---|
| 03-01 | 확인 | 다섯 사례는 결정적 합성 fixture이며 실제 일주일 제품 실험이 아니다. | `fixtures.json`, `generate.py`, `plan.json`, saved events의 synthetic 플래그와 생성 사용자·날짜를 확인. 실행 시각은 10/23이고 10/1~10/8은 이벤트 입력/분석 계획이다. |
| 03-02 | 확인 | 각 군 2000명은 검정력 계산 결과가 아닌 사전 예시 최소치다. | plan의 minimum_users_per_variant=2000과 sample_plan_scope, 본문의 baseline/MDE/alpha/power 별도 설계 한정이 일치한다. 100명 사례의 큰 효과에도 HOLD_SAMPLE이다. |
| 03-03 | 확인 | 분모는 첫 적격 노출 사용자, 전환은 그 뒤 24시간 내 고유 사용자다. | 5개 gzip 원시 이벤트를 해제해 event_id를 제거하고 첫 노출/시간 창/사용자 집합을 감사자가 별도 구현해 재집계했다. 모든 군의 노출·전환·비율이 summary와 일치한다. 요청/trace를 분모로 사용하지 않는다. |
| 03-04 | 확인 | 20 event retry·20 반복 노출·10 반복 전환·4 시간 부적격 전환을 제외한다. | 원시 5개 각각 독립 집계 일치. request ID 반복 10개도 별도 제거된다. conflicting event_id/request_id는 ValueError, 교차 variant 사용자는 INVALID_ASSIGNMENT인 실제 코드·fresh test를 확인했다. |
| 03-05 | 확인 | 분석 창과 사용자 전환 창의 성숙을 확인한 후 한 번 판정한다. | `analysis.py`의 end+24h<=analysis_at 및 as_of<analysis_at HOLD_WINDOW, 시간 경계 및 충분한 표본에도 미성숙 보류 테스트. 순차검정·다중비교를 제공한다고 주장하지 않는다. |
| 03-06 | 확인 | SRM은 노출/enrollment 집계 단계이며 할당 SRM과 다르다. | `analysis.py:srm` 입력은 exposed_users. `source-integration.json`은 allocation/exposure 진단을 별도 저장. 본문도 노출 조건화 편향·ITT를 남기고 50:50이 적절한 노출 기대인지 확인하도록 한정한다. |
| 03-07 | 확인 | A2800/B1200이면 기대2000/2000, chi²640, p≈3.34e−141이다. | 원시 노출 수와 Pearson 공식·df1 erfc를 독립 재계산. 작은 기대 수<5는 valid_approximation=false/HOLD_SAMPLE이며 p1도 무작위성 증명으로 해석하지 않는다. |
| 03-08 | 확인 | 효과는 A200/2000→B280/2000로 +4%p다. | raw 재집계와 별도 Wilson/Newcombe 수식으로 CI [1.9883766,6.0156583]%p 확인. 기준은 점추정≥3%p 및 CI하한>0이며 실제 효과≥3%p의 입증이 아니다. |
| 03-09 | 확인 | Wilson과 연속성 보정 없는 Newcombe 독립 두 비율 근사 구간이다. | NIST Wilson 공식과 statsmodels 공식 newcomb 구현을 직접 대조하고 5개 raw 결과 CI 독립 재계산. exact coverage/사후확률로 설명하지 않는다. |
| 03-10 | 확인 | 가드레일 오류율은 요청 분모이며 p95는 nearest-rank다. | raw request ID 중복 제거 후 오류 수·정렬 ceil(.95N) 위치를 별도 계산. bad B100/2000=5%, p95447ms; A10/2000=.5%,147ms. error≤1%, p95≤250ms, B/A≤1.2 규칙과 일치한다. |
| 03-11 | 확인 | 누락 가드레일은 통과가 아니며 관측 정책은 통계적 비열등성 증명이 아니다. | zero-request HOLD_GUARDRAILS 테스트, observed 및 세 정책 분기 확인. 본문과 자체 보고서가 같은 한정을 표시한다. |
| 03-12 | 확인 | 5개 최종 판정과 실제 보고서가 일치한다. | 원시·summary·report-visible.txt·실제 decision-report/results PNG를 직접 대조. HOLD_EFFECT/PASS_FIXED_RULES/HOLD_SAMPLE/INVALID_SRM/STOP_GUARDRAIL, CI·SRM·guardrail 수치 일치. HTTP28300 summary와 페이지도200 및 5판정 assert통과. |
| 03-13 | 확인 | 2편 이벤트는 DESCRIPTIVE_ONLY로 연계한다. | source-events.json.gz 해제 bytes가 sticky-ab/out/events.json과 완전히 같고 SHA256도 source-integration과 일치. 할당202/198, 노출160씩, 전환46/37, 비율28.750/23.125%를 대조. 사후 표본계획·가드레일·제품효과를 만들지 않는다. |
| 03-14 | 확인 | 의미 있는 회귀 테스트14개가 실행됐다. | 저장 tests.txt 및 실행 결과 Python3.12.15를 확인하고 별도로 `python3 -B -m unittest discover`를 실행해14개 모두 통과. 테스트는 분모·중복·충돌·표본·시간·SRM·CI·가드레일 경계에 대응한다. |

### 독립 재계산과 한계

다섯 이벤트 gzip의 해제 원문 SHA256이 summary의 source_sha256와 일치했다. 요약 값만 재인용하지 않고 원시 이벤트에서 노출·적격 전환·오류·p95·중복을 재집계하고 Wilson/Newcombe를 별도 수식으로 계산했다. insufficient의 +15%p와 양수 CI는 표본 게이트를 우회하지 못하고, srm 사례는 효과·다른 게이트보다 SRM 무효 판정을 우선하며, guardrail_bad는 +4%p에도 중단된다. 모두 저장된 결과와 일치한다.

[NIST Wilson](https://www.itl.nist.gov/div898/handbook/prc/section2/prc241.htm), [statsmodels 공식 Newcombe 구현](https://www.statsmodels.org/stable/_modules/statsmodels/stats/proportion.html#confint_proportions_2indep), [NIST chi² 표](https://www.itl.nist.gov/div898/handbook/eda/section3/eda3674.htm), [Microsoft SRM 진단](https://www.microsoft.com/en-us/research/articles/diagnosing-sample-ratio-mismatch-in-a-b-testing/), [ASA 성명](https://www.amstat.org/asa/files/pdfs/p-valuestatement.pdf)을 직접 조회했다. PubMed 링크는 이번 조회에서 본문 초록을 반환하지 않았으므로 원논문 전문까지 읽었다고 하지 않는다. 수식의 확인은 공개 공식 구현과 독립 재계산에 근거한다.

실습은 합성 입력에서 정해 둔 분기와 수식의 구현을 확인한다. 통계 모델의 실제 제품 적용, 표본의 독립성, 무작위 할당 품질, 최적 표본 수·검정력, 노출 조건화의 인과 타당성, 실제 제품 승자를 입증하지 않는다. 해당 한계는 본문에도 명시돼 있어 추가 수정 요구는 없다. 이번 감사에서 스택 재기동·실험 재생성·이벤트 전송·화면 재캡처는 수행하지 않았다.
