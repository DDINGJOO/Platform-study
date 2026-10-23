# 사실관계 퇴고 · 1차 패스

- 역할: 독립 code-reviewer, 사실관계 관점만 담당. 작성자·최종 감사자와 별개다.
- 범위: `posts/CS/DevOps/deployment-experiments/02_2편 - A·B 테스트 사용자는 새로고침해도 같은 그룹이어야 한다.html` 및 `labs/devops/deployment-experiments/sticky-ab/`.
- 1편과 3편은 이번 패스 범위가 아니다.
- 판정: **APPROVE · 확정 지적 0건**.
- 저장 증거를 읽기 전용으로 재계산했다. 실험 재실행, 서비스 기동, 인증, Git 변경, 외부 쓰기는 하지 않았다. 이 보고서만 새로 작성했다.

## 대조 결과

| 주장 위치 | 원자료와 독립 확인 | 판정 |
|---|---|---|
| HTML 29, 57, 93, 96행 | `out/events.json`의 할당 400개 및 사용자·종류별 고유 이벤트 803개를 재집계했다. A/B 할당 202/198, 노출 160/160, 전환 46/37, 진입 400·노출 320·전환 83명이 `summary.json` 및 본문과 일치한다. | 확인 |
| HTML 49~59행 | JSON 직렬화 → SHA-256 앞 8바이트 → big-endian → mod 10000을 400명 모두 다시 계산했다. 저장 bucket 및 그룹과 일치한다. 다른 salt의 재계산에서 182명이 달라진다. 실제 기동 거부는 `run.py`의 별도 Compose 기동과 `out/salt-rejection.txt`로 뒷받침된다. | 확인 |
| HTML 62~75행 | `app.py`의 `PRIMARY KEY(experiment_id,user_id)`, `UNIQUE(experiment_id,user_id,event_type)`, `BEGIN IMMEDIATE` 및 응답 후 커밋 흐름을 확인했다. 재시도·새 요청 ID·앱 재시작 전후 export 비교는 `run.py`에서 실제 HTTP 및 `compose restart app`으로 검사한다. 요청 수 1600/640/166은 4회 진입, 2회 노출, 2회 전환 제출과 일치한다. | 확인 |
| HTML 74행 | 누락 식별자/클라이언트 그룹 지정 400, 진입 전 노출/노출 전 전환 409는 실제 처리 분기 및 실행기 기대 응답과 일치한다. 거부 요청은 accepted attempt 카운터에 들어가지 않는다. | 확인 |
| HTML 86~96행 | DB 스냅샷 gauge 및 수락 제출 counter 구현, 사용자 ID 없는 레이블, PromQL 매칭을 확인했다. 저장 Prometheus 증거는 A/B 노출을 각각 160으로 반환한다. Grafana 캡처에도 할당·노출·전환 및 1600/640/166 요청 수가 일치한다. | 확인 |
| HTML 93행 | A는 46/160=28.75%, B는 37/160=23.125%다. Grafana 23.13%와 Python 결과 23.12%가 실제 두 이미지 및 `results.txt`와 일치한다. 본문은 이를 반올림 표시 차이로 설명하며 원래 분자·분모를 보존한다. | 확인 |
| HTML 44, 97행 | 노출 조건부 비율을 미리 정의하고, 할당 전체 분모와 다르며 노출에 처리 효과가 있으면 편향될 수 있음을 명시한다. 합성 전환으로 제품 효과나 통계적 승자를 주장하지 않는다. | 확인 |
| HTML 100~114행 | Python 3.12.15 및 이미지 digest는 `out/runtime-versions.json`과 Compose, Prometheus/Grafana 버전·메모리 설정은 Compose와 일치한다. 호스트 실행기 요구 Python 3.9+는 `removeprefix` 등 사용 API와 부합한다. 이전 결과 보관 및 재기동 시 저장 실험 식별자 사용 설명도 코드와 일치한다. | 확인 |

독립 계산 결과:

```text
PASS saved evidence: 400 allocations, 803 unique events,
exact per-variant denominators/conversions, SHA-256 mapping,
182 salt remaps, Prometheus exposure values
```

## 공식 근거 대조

- [Unleash stickiness](https://docs.getunleash.io/concepts/stickiness): 사용자 문맥과 group ID의 결정적 해시, MurmurHash, 입력 변경 시 재할당 설명이 본문과 일치한다. 실습의 SHA-256과 Unleash 구현을 구분한다.
- [Netflix 실험 플랫폼 소개](https://netflixtechblog.com/its-all-a-bout-testing-the-netflix-experimentation-platform-4e1ca458c15): 실험 할당이 대상 경험 노출을 보장하지 않는다는 설명을 직접 확인했다. 실습은 Netflix 내부 플랫폼을 실행했다고 주장하지 않는다.
- [Prometheus instrumentation](https://prometheus.io/docs/practices/instrumentation/): 사용자별 고유 정보 대신 집계 메트릭을 내보낸다는 설명과 구현을 대조했다.

## 검증 한계

스택은 이미 종료되어 이번 퇴고에서 라이브 HTTP/Prometheus/SQLite를 다시 조회하지 않았다. 저장 이벤트, 실행 코드, 실행 보고서, 실제 캡처 사이의 일치 여부를 확인한 판정이다. 재기동 과정 전체의 재실행은 하지 않았다. LSP 도구가 제공되지 않아 LSP 진단은 수행하지 않았다. 최종 독립 감사와 전체 구조·발행 검증은 리더의 별도 절차다.

## 1·3편 라운드 1 · 독립 사실관계 퇴고

- 검토자: 별도 `code-reviewer` 에이전트. 두 작성자 및 최종 감사자와 분리했다.
- 판정: **1편 APPROVE · 지적 0건 / 3편 APPROVE · 지적 0건**.
- 기존 2편 기록을 유지했다. 저자 HTML·코드·원자료·이미지는 수정하지 않았다.
- 검토 순서: 공통 BRIEF의 실제 도구·A/A′/B·통계 한계 요구 충족을 먼저 확인하고, 원자료와 본문·그림 수치 및 실패 처리 분기를 대조했다. 완료 상태의 대소문자 보정은 분석 결과를 숨기는 대체 경로가 아니며 원응답과 실패 종료를 보존한다.

### 1편 대조

| 본문 위치 | 읽기 전용 독립 확인 | 판정 |
|---|---|---|
| 27~56행 | `service.py`의 실제 캐시 128개, 기본 10~14ms와 miss 추가 65ms, B의 설정 지연 40ms를 확인했다. `summary.json`의 cold 진단 A 13.183ms/A′78.448ms는 본문과 일치한다. 이는 실제 제품 코드 변경이나 운영 A의 재현으로 과장되지 않는다. | 확인 |
| 57~65행 | 두 실행의 컨테이너·시작 메타데이터 및 `run.py`에서 동일 이미지, 각 0.5CPU·96MiB, 3초 미만 시작 차이, 동일 순환 키·4RPS, 캐시 채움 후 46초·동일 120초 관측을 확인했다. | 확인 |
| 66~94행 | 공식 버전 고정 이미지, Kayenta 내장 Orca 분석, 실제 PromQL 범위 조회와 1개 지표 가중치 100을 설정과 대조했다. 효과 크기 설정은 pinned judge 소스의 `meanRatio`/`allowedIncrease`/`criticalIncrease` 경로와 일치한다. 점수 100을 확률로 설명하지 않는다. | 확인 |
| 95~103행 | 각 원 Kayenta 응답의 judge 결과가 summary와 같음을 확인했다. 저장 Prometheus의 양측 61개 값을 judge 입력 61개와 모두 직접 대조하고 평균을 다시 계산했다. v1 13.001/13.005ms·100 Pass, 지연 설정 v2 13.484/53.807ms·0 Fail, High 분류가 일치한다. HTTP 관측 시각으로 각 군 480건을 독립 재집계했다. | 확인 |
| 99~106행 | Deck의 실제 두 보고서 PNG에서 점수·분류·관측 시간, Grafana PNG에서 지연·4RPS·프로세스 나이·캐시 개수를 직접 읽었다. 61개를 독립 사용자 수로 해석하지 않고 겹치는 조회 창의 상관을 명시한다. | 확인 |
| 109~126행 | 소문자 `succeeded` 응답과 대소문자 정규화 종료 조건, 저장 입력 대조 검증기, 외부 배포 Orca·클라우드 배포·승격·롤백 미구현 범위 및 memory 계정 재시작 손실 설명을 코드·설정과 대조했다. 가짜 도구 UI나 가짜 성공 응답으로 대체한 근거는 없다. | 확인 |

Spinnaker 공식 [canary best practices](https://spinnaker.io/docs/guides/user/canary/best-practices/)의 최소 50개 시계열 지점 및 장시간 운영 분석 권고를 직접 확인했다. 글은 61개 지점을 충족하면서도 120초 실습을 운영 안전 보장으로 일반화하지 않는다. [고정 NetflixACAJudge 소스](https://github.com/spinnaker/spinnaker/blob/a59b1887bb66ae3e5d92b98782abbde7e2eef70e/kayenta/kayenta-judge/src/main/scala/com/netflix/kayenta/judge/NetflixACAJudge.scala)의 효과 크기 설정을 직접 대조했다.

### 3편 대조

| 본문 위치 | 읽기 전용 독립 확인 | 판정 |
|---|---|---|
| 32~74행 | `plan.json`, `fixtures.json` 및 summary의 다섯 결과를 대조했다. 노출·전환·시간 창·정책 문턱과 다섯 판정이 일치한다. 2,000명을 계산된 검정력 보장으로 주장하지 않는다. | 확인 |
| 76~111행 | 각 gzip 전체 이벤트를 직접 풀어 event ID 중복을 제거하고 최초 노출·적격 전환·요청 ID를 별도 집계했다. 다섯 시나리오 모두 사용자·전환·요청·오류·p95가 summary와 같다. 2편 연결의 202/198·160/160·46/37 및 28.750%/23.125%는 기존 독립 집계와 일치하며 기술적 연결만 주장한다. | 확인 |
| 115~153행 | 노출 단계 SRM과 할당 단계 검사를 구분하고 선택 편향·인과성 한계를 명시한다. 노출 2,800/1,200의 χ²640 및 `erfc(sqrt(640/2))`의 p≈3.34×10⁻¹⁴¹을 별도 재계산했다. 기대 수가 5 미만일 때 표본 보류, 고정 창 전 보류, 최소 표본·효과 gate 순서가 코드와 일치한다. | 확인 |
| 155~195행 | 다섯 입력을 저자 분석 함수를 호출하지 않고 독립 집계·계산했다. Wilson 및 Newcombe B−A 구간이 모두 허용 오차 내 일치한다. 정상 +4%p 구간 약 [1.99,6.02]%p, 부족 +15%p 구간 약 [5.92,24.33]%p, 가드레일 B 오류5%·p95447ms/A 오류0.5%·p95147ms가 일치한다. | 확인 |
| 185~226행 | 관측 차이 3%p 문턱과 구간 하한>0이 실제 효과≥3%p 보장이 아님을 정확히 명시한다. 명목 95% 근사·독립 이항 가정·다중 검정/순차 분석 미구현·통계적 비열등성 미검증을 설명한다. 저장 테스트 기록의 14개 이름 및 실제 14개 테스트 정의를 확인했다. | 확인 |
| PNG 2개 | 자체 HTTP 보고서와 실행 출력 PNG를 직접 읽었다. 다섯 사용자 수·구간·SRM·판정 및 14개 테스트가 본문·JSON과 일치하고 자체 UI임을 표시한다. | 확인 |

Wilson 공식은 [NIST 원문](https://www.itl.nist.gov/div898/handbook/prc/section2/prc241.htm), 두 비율 차이 구간의 방향과 제곱합은 [statsmodels 공식 구현](https://www.statsmodels.org/stable/_modules/statsmodels/stats/proportion.html#confint_proportions_2indep)의 `newcomb` 분기를 직접 확인했다. 저자 함수 호출 없이 동일 정의를 새로 계산해 전체 원자료 결과와 대조했다.

```text
CANARY same-version / regression: raw judge, 61 points/side, 480 HTTP requests/side PASS
DECISION 5 complete fixtures: users/conversions/requests/errors/p95/Wilson/Newcombe/SRM PASS
AST parse: canary/*.py and decision/*.py PASS
```

이 패스에서는 분석 재실행·스택 재시작·HTTP 쓰기·외부 쓰기를 하지 않았다. LSP/ast-grep 도구는 현재 제공되지 않아 해당 진단을 수행하지 못했다. Python AST 파싱과 원자료 독립 재계산은 수행했다. 라이브 API 재검과 최종 원자료 감사는 별도 감사자의 범위이며 이 보고서를 그 감사로 대체하지 않는다.
