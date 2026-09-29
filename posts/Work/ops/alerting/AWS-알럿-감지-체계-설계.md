# AWS 알럿 감지 체계 설계

> 최종 수정: 2026-08-04 (v2 — 패널 리뷰 반영)
> 상태: 1주차 진행 중 (7/31 ~ 8/5)

---

# 1. 요약

> **온콜 도구는 전달 계층일 뿐이다. 감지는 앞단에 별도로 만들어야 하며, 페이지(전화)는 원인이 아니라 증상에 건다.**

1. 호출 계층은 **Datadog On-Call** 2시트로 시작한다.
2. 감지 항목을 P1/P2/P3 세 티어로 분류하고, **티어별 SNS 토픽**으로 라우팅한다.
3. **P1 경로에는 우리가 작성한 코드가 없다.** Lambda는 자동 복구에만 쓰고, 그것도 별도 경로로 분리한다.
4. **P1은 "알람 개수"가 아니라 "전화가 울리는 경로 수"로 센다.** 목표 12개. 같은 사건은 복합 알람으로 묶어 전화 1통으로 만든다.
5. AWS 리소스뿐 아니라 **애플리케이션 계층(기관 연동, 커넥션 풀)도 감지한다.** 이미 수집 중인 커스텀 메트릭을 쓰므로 추가 비용이 없다.
6. 알람·토픽·KMS·EventBridge 룰은 **Terraform으로 관리한다.** 나머지 인프라는 기존 수동 관리를 유지한다.
7. AWS 인프라 비용은 월 **약 $25**. 실제 변수는 Datadog 시트와 기존 폴링 비용이다.

## 핵심 결정 사항

| # | 결정 | 근거 |
| --- | --- | --- |
| D1 | AWS 메트릭 감지는 CloudWatch/EventBridge, 전달만 Datadog | Datadog AWS 인테그레이션 폴링은 10~20분 지연. P1에 사용 불가 |
| D2 | **앱 메트릭 감지는 Datadog 모니터** | DogStatsD 직접 수집이므로 지연 1~2분. 폴링과 다르다 |
| D3 | P1 경로에 자체 컴포넌트 없음 | 감시 대상이 전달 수단이 되는 순환 의존 회피 |
| D4 | **P1 = 페이지 경로 12개.** 개별 알람은 복합 알람으로 묶음 | 알람 31개가 각각 전화하면 장애 1건에 전화 8통 |
| D5 | 알람은 Terraform, 그 외 인프라는 수동 유지 | 알람은 리소스를 참조만 하므로 기존 인프라 import 불필요 |
| D6 | Datadog SNS 구독만 수동 생성 | API 키가 Terraform state에 평문 저장되는 것을 회피 |
| D7 | 티어는 알람 태그로 표현 (이름 아님) | 티어 승격 시 알람 재생성·히스토리 소실 방지 |
| D8 | `treat_missing_data`를 메트릭 성격별로 분기 | 일괄 `breaching` 적용 시 야간 트래픽 0 구간에서 오탐 발생 |
| D9 | **런북 없는 P1은 만들지 않는다** | 전화를 받은 사람이 할 일이 없으면 P1 자격이 없다 |

---

# 2. 배경

현재 인프라 장애를 사람이 인지하는 경로가 정형화되어 있지 않다. 특히 다음 성격의 장애는 자체 지표(CPU, 5xx)로 전혀 드러나지 않는다.

| 장애 유형 | 현재 인지 방법 | 문제 | 1차 구축 |
| --- | --- | --- | --- |
| VPN 터널 단절 | 외부 기관 연동 실패 문의 | 사용자가 먼저 발견 | ✅ #1 |
| **기관 API 인증 실패 (터널은 정상)** | **외부 기관 연동 실패 문의** | **터널 상태로는 드러나지 않음** | ✅ #7 |
| DLQ 적재 | 주기적 수동 확인 | 처리 누락 건이 방치됨 | ✅ #2 |
| NAT 포트 고갈 | 간헐적 타임아웃 조사 | 원인 규명에 반나절 소요 | ✅ #4 |
| ECS 태스크 배치 실패 | 배포 후 확인 | 야간 발생 시 인지 불가 | ✅ #5 |
| Redis 축출 / 연결 거부 | 인지 못 함 | 세션 소실이 "가끔 로그아웃됨" 문의로만 드러남 | ✅ #6 |
| **커넥션 풀 고갈 (DB는 정상)** | **간헐적 지연 조사** | **RDS 지표 전부 정상으로 나옴** | ✅ #8 |

보험금 청구 대행 서비스 특성상 외부 기관 연동 단절은 서비스 전면 중단과 동일하다. 이를 자동 감지하고 담당자를 호출하는 체계가 필요하다.

> ⚠️ **v1 대비 중요한 인식 변경**
>
> v1은 "외부 기관 연동 단절"의 감지 수단으로 VPN `TunnelState`만 두었다. 그런데 **`TunnelState`는 L3 터널 상태이고, 연동 실패의 대부분은 그 위 애플리케이션 레이어에서 발생한다.**
>
> - 기관 API 인증서/토큰 만료
> - 기관 측 응답 포맷 변경
> - 기관 측 정기 점검 (터널 유지, API만 거부)
> - 기관 측 rate limit
> - 우리 쪽 파싱 로직이 새 응답을 처리 못 함
>
> 이 경우 **터널은 UP이고 모든 AWS 지표가 정상이다.** 6.9(애플리케이션 계층)를 신설한 이유다.

---

# 3. 설계 원칙

## 3.1 P1 경로에는 커스텀 코드가 없다

`CloudWatch 알람 → SNS → Datadog On-Call` 구간에 Lambda, 페이로드 변환, 인리치먼트를 넣지 않는다. 우리가 배포한 컴포넌트는 새로운 장애 지점이며, 하필 필요한 순간에 함께 죽는다.

예를 들어 Lambda 동시성 고갈은 P1 감지 대상인데, 그 알람을 전달하는 수단이 Lambda라면 해당 상황에서 알림 자체가 전달되지 않는다.

**허용되는 것** — 설정으로만 동작하는 것

- CloudWatch Metric Math (알람 정의 내부의 식)
- CloudWatch Composite Alarm (알람 조합)
- EventBridge Input Transformer (선언적 페이로드 성형)
- SNS 팬아웃 / 필터 정책

**금지되는 것**

- Lambda 경유 전달
- API Gateway / 자체 릴레이 서비스
- 조건 분기 코드

## 3.2 감지 수단은 지연 특성으로 나눈다

| 성격 | 담당 | 지연 |
| --- | --- | --- |
| 이진 조건 (터널 down, DLQ 적재, HealthyHost 0) | CloudWatch 알람 | 1~2분 |
| AWS 서비스 이벤트 (ECS, ASG, GuardDuty, Config, Health) | EventBridge 룰 | 1~2분 |
| **앱 메트릭 (DogStatsD로 Datadog에 직접 수집)** | **Datadog 모니터** | **1~2분** |
| AWS 메트릭 추세·이상탐지·no-data | Datadog 모니터 (인테그레이션 폴링) | 10~20분 |

> ⚠️ **3번 행이 v1에서 누락되어 있었다.**
>
> "Datadog = 느림"으로 뭉뚱그린 결과 애플리케이션 계층 감지가 문서 전체에서 빠졌다. **커스텀 메트릭은 AWS 인테그레이션 폴링을 거치지 않고 DogStatsD로 직접 들어오므로 지연이 1~2분이다.** P1에 쓸 수 있다.

이 분리에는 비용 측면의 부수 효과가 있다. P1 호출이 Datadog **AWS 폴링**에 의존하지 않으므로 폴링 주기를 늘리거나 대상을 축소해도 안전하다.

> 근거 보강: AWS 인테그레이션 폴링은 Datadog이 AWS API를 호출하는 pull 구조다. 리전 장애나 API 스로틀링이 발생하면 메트릭 자체가 들어오지 않는다. CloudWatch 알람 → SNS는 AWS가 밀어주는 push 구조이므로 그 상황에서도 도달한다.

## 3.3 라우팅은 토픽으로만 결정한다

티어별 SNS 토픽 3개를 두고, 알람이 어느 토픽을 바라보는지가 곧 티어다. 매핑 테이블이나 조건 분기 코드를 만들지 않는다.

티어는 **알람 태그**(`tier=p1`)로 표기한다. 알람 이름에 넣지 않는 이유는 5.3 참조.

## 3.4 페이지는 복합 알람 단위로 발생시킨다

**개별 알람이 각각 전화하면 장애 1건에 전화 8통이 온다.** 따라서 P1 알람은 개별로 액션을 걸지 않고, 레이어별 복합 알람이 대표로 발화한다.

```
개별 알람    → 액션 없음 (상태만 기록, 대시보드·조사용)
복합 알람    → SNS p1 토픽 → 전화
```

상위 원인 레이어가 ALARM일 때 하위 레이어 복합 알람의 액션을 억제한다(actions suppressor). 13장 참조.

## 3.5 알럿 파이프라인 자체를 감시한다

알럿 시스템이 감시 대상과 같은 AWS 안에 있다. SNS가 죽거나, EventBridge 룰이 실패하거나, On-Call 스케줄이 비면 **알럿은 조용히 사라지고 아무도 모른다.** 8장 참조.

## 3.6 런북 없는 P1은 만들지 않는다

전화를 받은 사람이 **할 수 있는 일**이 런북에 없으면 그 항목은 P1이 아니다.

```
할 수 있는 일이 없음        → P2 (업무시간 처리)
할 수 있는 일이 정의됨      → P1
```

특히 외부 의존(VPN 상대측, 기관 API)은 "우리가 복구할 수 없는 것"이 되기 쉽다. 이 경우 **야간 연락 채널**이 런북에 있어야 P1 자격이 생긴다.

---

# 4. 아키텍처

## 4.1 전체 구조

```
CloudWatch 알람 (개별) ──→ Composite 알람 ──┐
RDS 이벤트 구독 ───────────────────────────┼──→ SNS(P1) ─┬──→ Datadog HTTPS → Event → Monitor → 전화
EventBridge 룰 (P1 이벤트) ────────────────┘             ├──→ ChatBot → #infra-alert
                                                          └──→ (배달 실패) SQS DLQ

CloudWatch 알람 ─────────┐
EventBridge 룰 ──────────┼──→ SNS(P2) ─┬──→ ChatBot → #infra-alert
                                        └──→ (배달 실패) SQS DLQ

EventBridge 룰 ──────────────────────────→ CloudWatch Logs      [P3 — SNS 경유 안 함]

EventBridge 룰 ──────────────────────────→ (별도 경로) 복구 Lambda

Datadog 모니터 (앱 메트릭) ───────────────→ 동일 On-Call        [1~2분]
Datadog 모니터 (AWS 추세) ────────────────→ 동일 On-Call        [10~20분 허용]

EventBridge Scheduler(15분) ──────────────→ SNS(P3) → Datadew   [하트비트]
```

각 소스는 자신의 티어 토픽 하나에만 발행한다. SNS 앞에 분기 컴포넌트는 존재하지 않는다.

> ⚠️ **v1 오류 정정 — SNS는 CloudWatch Logs를 구독할 수 없다**
>
> SNS가 지원하는 구독 프로토콜은 HTTP/HTTPS, Email, Email-JSON, SMS, SQS, Lambda, 플랫폼 엔드포인트, Data Firehose다. **CloudWatch Logs는 포함되지 않는다.** v1 다이어그램의 `SNS → CloudWatch Logs` 3곳은 구현 불가였다.
>
> **정정: 별도 기록 구독을 두지 않는다.**
> - P1/P2 기록 사본은 이미 2개다 — Datadog Event + Slack(ChatBot)
> - P3는 애초에 SNS를 경유하지 않고 EventBridge → CloudWatch Logs 직접 타겟으로 보낸다 (EventBridge는 Logs를 타겟으로 지원)
>
> 원문 문장으로 대체 근거를 이미 갖고 있었다 — 7.2: "Datadog이 이벤트 생성과 팀 호출을 한 번에 처리하므로 기록용 별도 구독은 필요하지 않다."

## 4.2 호출 경로와 복구 경로의 분리

하나의 알람이 두 경로로 나가되, 서로를 모르는 상태로 나간다.

- **호출 경로**: 복합 알람의 `AlarmActions`에 티어 토픽 ARN 지정
- **복구 경로**: EventBridge가 `CloudWatch Alarm State Change` 이벤트를 독립 수신

복구 Lambda를 배포하다 깨뜨려도 전화는 정상 발신된다. SNS 팬아웃으로 같은 토픽에 Lambda를 매달면 구독 목록을 공유하게 되어, 설정 실수 하나가 호출 경로에 영향을 줄 수 있다.

## 4.3 Datadog 측 구조 (Q1 검증 필요)

```
SNS → /intake/webhook/sns → Datadog Event 생성
                                  ↓
                          Event Monitor
                                  ↓
                          @oncall-<team> / Escalation Policy → 전화
```

⚠️ **이벤트 생성과 페이지 발생은 다른 일이다.** SNS intake는 이벤트를 만들고, 전화는 모니터가 발생시킨다. 즉 P1 경로에 Datadog 모니터가 하나 개입한다. 이는 3.1 위반은 아니지만(우리 코드가 아니므로) 설정 실수 지점이 하나 늘어난다. **8.1 검증 절차에서 반드시 확인한다.**

---

# 5. 티어 정의

| 티어 | 정의 | 경로 | 대응 | 목표 |
| --- | --- | --- | --- | --- |
| **P1** | 사용자 영향이 지금 발생 중이고, 사람이 개입하지 않으면 복구되지 않으며, **런북에 할 수 있는 일이 있다** | SNS `p1` → 전화 | 즉시 | **페이지 경로 12개** |
| **P2** | 열화 진행 중 / 곧 P1이 됨 / 복구는 가능하나 급하지 않음 | SNS `p2` → 슬랙 멘션 | 업무시간. 15분 미확인 시 P1 승격 | 제한 없음 |
| **P3** | 사후 분석·추세 | EventBridge → CloudWatch Logs | 주간 리뷰 | 제한 없음 |

## 5.1 P1은 "알람 개수"가 아니라 "페이지 경로 수"다

v1의 결함: P1 목표를 8~10개로 선언했지만 6장에서 **31개**를 만들었다. 원안(25개)보다 늘었다.

원인은 두 가지였다.

1. **각 항목만 보면 다 P1처럼 보인다.** 포화 경고(80~90%)와 실제 영향 발생을 구분하지 않았다.
2. **같은 사건의 여러 증상을 각각 P1으로 셌다.** RDS 페일오버 1건에 P1 알람 5개가 걸려 있었다.

**해법: 알람은 그대로 두고, 페이지 단위를 복합 알람으로 정의한다.**

```
개별 알람  →  액션 없음 (상태 기록, 조사용)
복합 알람  →  전화 1통
```

## 5.2 P1 페이지 경로 12개 (확정)

| # | 페이지 경로 (복합 알람) | 레이어 | 포함 알람 | 런북 |
| --- | --- | --- | --- | --- |
| **PG-01** | `composite-l1-vpn-down` | L1 | #19, #20, #21 ({기관A}/{기관B}/{기관C} 양쪽 터널 down) | 부록 C-1 |
| **PG-02** | `composite-l1-nat-exhaustion` | L1 | #23 `ErrorPortAllocation > 0` | 부록 C-2 |
| **PG-03** | `composite-l2-rds-incident` | L2 | #30 커넥션 95%, #31 failover/failure, #32 FreeLocalStorage, #35e EngineUptime 급락 | 부록 C-3 |
| **PG-04** | `composite-l2-redis-incident` | L2 | #39 RejectedConnections (+ 조건부 #40) | 부록 C-4 |
| **PG-05** | `composite-l3-capacity` | L3 | #1 running<desired, #10b ASG 전멸 | 부록 C-5 |
| **PG-06** | `composite-l4-alb-down` | L4 | #25 HealthyHostCount == 0 | 부록 C-6 |
| **PG-07** | `composite-l4-app-5xx` | L4 | #26 ELB 5xx, #26b Target 5xx 비율 | 부록 C-7 |
| **PG-08** | `composite-l4-sqs-dlq` | L4 | #36 DLQ 적재 | 부록 C-8 |
| **PG-09** | **`dd-app-institution-failure`** | APP | #61 기관 실패율, #62 기관 호출 침묵, #63 `integration.status.issue` | 부록 C-9 |
| **PG-10** | **`dd-app-resource-exhaustion`** | APP | #65 커넥션 풀 대기, #66 스레드 WAITING 급증 | 부록 C-10 |
| **PG-11** | `composite-security-critical` | SEC | #45 GuardDuty High/Critical, #46 루트 로그인, #48 루트 키 생성, #49b CloudTrail 무력화, #49c KMS 무력화 | 부록 C-11 |
| **PG-12** | `composite-meta-pipeline` | META | #51a SNS 배달 실패, #51b DLQ 적재, #51h 하트비트 no-data | 부록 C-12 |
| (PG-13) | `dd-aws-health-issue` | L0 | #52 `eventTypeCategory: issue` | 부록 C-13 |

**PG-09, PG-10은 Datadog 모니터**이므로 복합 알람이 아니라 Datadog composite monitor로 구성한다.

## 5.3 P1 → P2 강등 목록 (v1 대비)

| # | 항목 | v1 | v2 | 근거 |
| --- | --- | --- | --- | --- |
| #10b | ASG InService == 0 | P1 단독 | **PG-05에 포함** | ECS 용량 문제와 같은 사건 |
| #13b | Lambda Throttles 10분 연속 | P1 | **P2** (동기 호출 함수만 P1) | 비동기 함수는 재시도로 흡수. 6.4 참조 |
| #29b | ACM `DaysToExpiry < 14` | P1 | **P2** | 14일은 업무시간에 처리 가능. 예측 가능한 만료 |
| #29c | ACM 갱신 실패 이벤트 | P1 | **P2** | 동일. 단 `< 3일` 신설(#29d)은 P1 |
| #40 | Redis `Evictions > 0` | P1 | **P2 (조건부)** | `maxmemory-policy`가 `allkeys-lru`면 설계된 정상 동작. `noeviction`이면 P1 — **Q2 확인 필요** |
| #41 | Redis `EngineCPU > 90` | P1 | **P2** | 90%는 포화 경고. `> 99` 5분 지속(#41b)이 P1이며 PG-04에 포함 |
| #42 | Redis `MasterLinkHealthStatus < 1` | P1 | **P2** | 리더 읽기를 서비스에 쓰지 않으면 즉시 영향 없음 |
| #43 | Redis `CurrConnections` 90% | P1 | **P2** | 90%는 경고. 실제 거부(#39)가 영향 |
| #44h | Redis 페일오버 이벤트 | P1 | **P2** | 자동 복구됨. 기록이 중요하고 전화는 과함 |
| #48 | `CreateAccessKey` (일반 계정) | P1 | **P2** | 정상 운영에서도 발생. 루트 대상만 P1 |
| #30b | RDS 커넥션 80% | P2 | P2 유지 | — |

## 5.4 환경별 티어 규칙

v1에 없던 항목. `prod`만 예시로 써놓으면 나중에 누군가 `stg` 알람에 `tier = "p1"`을 넣고, 새벽에 stg VPN 터널 down으로 전화가 온다.

| 환경 | 허용 티어 |
| --- | --- |
| `prod` | P1 / P2 / P3 |
| `stg` | **P2 이하. P1 금지** |
| `dev` | **P3만** |

Terraform validation으로 강제한다 (9.8 참조). 규칙을 문서가 아니라 코드로 둔다.

## 5.5 티어를 알람 이름에 넣지 않는 이유

CloudWatch 알람 이름은 식별자이므로 **이름 변경 = 삭제 후 재생성 = 알람 히스토리 소실**이다.

도입 계획에는 "노이즈 실측 후 티어 승격" 단계가 있는데, 승격할 때마다 그 판단 근거인 히스토리를 날리게 된다. 따라서 티어는 태그로 표기한다.

```bash
# 티어 검증 (태그 기반)
aws resourcegroupstaggingapi get-resources \
  --tag-filters Key=tier,Values=p1 \
  --resource-type-filters cloudwatch:alarm

# 페이지 경로만 추출 (액션이 있는 알람 = 복합 알람이어야 함)
aws cloudwatch describe-alarms --alarm-types CompositeAlarm \
  --query "CompositeAlarms[?AlarmActions[0]!=null].AlarmName"

# 개별 알람에 액션이 잘못 걸린 것 찾기 (3.4 위반 탐지)
aws cloudwatch describe-alarms --alarm-types MetricAlarm \
  --query "MetricAlarms[?contains(AlarmActions[0],'p1')].AlarmName"
```

마지막 명령의 결과는 **비어 있어야 한다.** P1은 복합 알람만 발화한다.

---

# 6. 감지 항목

정량 조건은 `임계값 / 평가주기 / M of N` 형태로 명시한다. `"급증"`, `"임계 초과"` 같은 정성 표현은 알람으로 만들 수 없다.

**티어 열의 의미**

- `P1(PG-nn)` — 개별 알람은 액션 없음. 해당 복합 알람이 전화를 발생시킴
- `P2` — SNS p2 토픽으로 직접 발화
- `P3` — EventBridge → CloudWatch Logs

## 6.1 `treat_missing_data` 분기 규칙 ⚠️ 중요

일괄 `breaching` 적용은 야간 오탐을 만든다.

| 메트릭 성격 | 데이터 없을 때 | 설정 | 예시 |
| --- | --- | --- | --- |
| **상태 게이지** | 값이 계속 보고됨. 없어지면 진짜 이상 | `breaching` | `TunnelState`, `HealthyHostCount`, `DatabaseConnections`, `GroupInServiceInstances`, `EngineCPUUtilization` |
| **이벤트 카운터** | 호출이 없으면 데이터포인트 자체가 없음 | `notBreaching` | `Throttles`, `Errors`, `HTTPCode_ELB_5XX_Count`, `DeadLetterErrors`, `Evictions`, `RejectedConnections` |

**터지는 시나리오**

```
새벽 3시, 트래픽 0
  → Lambda 호출 없음 → Throttles 메트릭 미발행
  → treat_missing_data: breaching → ALARM
  → P1 전화

실제로는 아무 문제 없음. 장애가 없어서 알람이 울린 것.
```

## 6.2 ECS

| # | 소스 | 조건 | 티어 | missing |
| --- | --- | --- | --- | --- |
| 1 | CW Alarm (Math) | `desired - running > 0`, 60s, 5 of 5 | **P1(PG-05)** | breaching |
| 2 | EB `ECS Deployment State Change` | `eventName: SERVICE_DEPLOYMENT_FAILED` | P2 | — |
| 2b | EB `ECS Deployment State Change` | Circuit breaker 자동 롤백 발생 | P2 | — |
| 3 | EB `ECS Service Action` | `SERVICE_TASK_START_IMPAIRED` | P2 | — |
| 4 | EB `ECS Service Action` | `SERVICE_TASK_CONFIGURATION_FAILURE` | P2 | — |
| 5 | EB `ECS Service Action` | `SERVICE_DISCOVERY_INSTANCE_UNHEALTHY` | P2 | — |
| 6 | EB `ECS Service Action` | `ECS_OPERATION_THROTTLED` | P2 | — |
| 7 | EB `ECS Service Action` | `SERVICE_TASK_PLACEMENT_FAILURE` (`RESOURCE:*`), 5분 내 3회 이상 | P2 | — |
| 8 | EB `ECS Task State Change` | `lastStatus: STOPPED`, `stopCode != ServiceSchedulerInitiated` | P3 | — |
| 8b | EB `ECS Task State Change` | `stoppedReason`에 `OutOfMemory` 포함 | P2 | — |
| 9 | EB `ECS Task State Change` | `stopCode: TerminationNotice` (Fargate Spot) | P3 | — |

**주의**

- 1번은 `ECS/ContainerInsights` 네임스페이스의 `RunningTaskCount` / `DesiredTaskCount`를 쓴다. **Container Insights가 꺼져 있으면 이 메트릭이 없다 (Q3).** 없으면 2·3·7번 이벤트로만 감지.
- 2번의 detail-type은 `ECS Deployment State Change`다. `ECS Service Action`이 아니다.
- 9번(Spot 중단)은 **설계된 정상 이벤트**다. P2로 두면 매일 슬랙이 울리고 채널이 뮤트된다.

## 6.3 ASG / EC2

| # | 소스 | 조건 | 티어 | missing |
| --- | --- | --- | --- | --- |
| 10 | CW Alarm (Math) | `GroupDesiredCapacity - GroupInServiceInstances > 0`, 60s, 10 of 10 | P2 | breaching |
| 10b | CW Alarm | `GroupInServiceInstances == 0` | **P1(PG-05)** | breaching |
| 11 | EB `aws.autoscaling` | `EC2 Instance Launch Unsuccessful` | P2 | — |
| 12 | CW Alarm | `StatusCheckFailed >= 1`, 60s, 3 of 3 | P2 | notBreaching |
| 12b | EB `aws.ec2` | `EC2 Spot Instance Interruption Warning` | P3 | — |

## 6.4 Lambda — 감축 (120개 → 약 15개)

v1은 함수 20개 × 6항목 = **120개 알람**으로 전체의 40%를 차지했다. 그런데 Lambda는 대부분 비동기 + 재시도 + DLQ 구조라 개별 함수의 `Errors`/`Duration`보다 **DLQ 알람 하나가 더 정확하다.**

**함수를 두 부류로 나눈다.**

| 부류 | 정의 | 알람 |
| --- | --- | --- |
| **동기 호출** | API Gateway / ALB 타겟 / 사용자 요청 경로에 있음 | 개별 알람 (Errors율, Throttles, Duration) |
| **비동기 / 이벤트 소스** | SQS, EventBridge, S3, 스트림 트리거 | DLQ 알람 + IteratorAge만 |

| # | 소스 | 조건 | 대상 | 티어 | missing |
| --- | --- | --- | --- | --- | --- |
| 13 | CW Alarm | `Throttles > 0`, 60s, 3 of 5 | **동기 함수만** | P2 | notBreaching |
| 14 | `AWS/Usage` | `ConcurrentExecutions` / 계정 한도 > 80% | 계정 단위 1개 | P2 | breaching |
| 15 | CW Alarm (Math) | `Errors / Invocations > 0.05`, 300s, 2 of 2 | **동기 함수만** | P2 | notBreaching |
| 16 | CW Alarm | DLQ `ApproximateNumberOfMessagesVisible > 0` | **DLQ 전부** | P2 | notBreaching |
| 17 | CW Alarm | `Duration` p95 > 타임아웃 × 0.8 | **동기 함수만** | P2 | notBreaching |
| 18 | CW Alarm | `IteratorAge > 60000`(ms), 300s, 3 of 3 | **스트림 소스 함수만** | P2 | notBreaching |

**예상 알람 수**

```
동기 함수 N개 × 3항목 (13, 15, 17)   = 3N
DLQ M개 × 1항목 (16)                 = M
스트림 소스 K개 × 1항목 (18)         = K
계정 단위 (14)                       = 1
                                     ─────
N=4, M=6, K=2 가정 시                 = 21개   (v1: 120개)
```

⚠️ **Q4 확인 필요**: Lambda 함수 중 **동기 호출**이 몇 개인가? 그 수만큼만 개별 알람을 만든다.

17번의 타임아웃 값은 CloudWatch 메트릭이 아니므로 Terraform 변수로 하드코딩한다. 함수 설정 변경 시 알람도 함께 수정해야 하는 부채로 기록.

## 6.5 네트워크

| # | 소스 | 조건 | 티어 | missing |
| --- | --- | --- | --- | --- |
| 19~21 | CW Alarm (Math) | `SUM([tunnel1, tunnel2]) <= 0`, 60s, 3 of 3 — {기관A} / {기관B} / {기관C} 각 1개 | **P1(PG-01)** | breaching |
| 22 | CW Alarm (Math) | `SUM([t1,t2]) <= 1`, 300s, 3 of 3 (이중화 소진) — 3세트 각각 | P2 | breaching |
| 23 | CW Alarm | `ErrorPortAllocation > 0`, 60s, 2 of 3 | **P1(PG-02)** | notBreaching |
| 24 | CW Alarm | `PacketsDropCount > 100`, 300s, 3 of 3 | P2 | notBreaching |
| 25 | CW Alarm | `HealthyHostCount == 0`, `Minimum`, 60s, 2 of 2 | **P1(PG-06)** | breaching |
| 25b | CW Alarm | `UnHealthyHostCount >= 1`, 60s, 5 of 5 (부분 장애) | P2 | breaching |
| 26 | CW Alarm | `HTTPCode_ELB_5XX_Count > 50`, 60s, 3 of 5 | **P1(PG-07)** | notBreaching |
| 26b | CW Alarm (Math) | `HTTPCode_Target_5XX / RequestCount > 0.05` (앱 5xx) | **P1(PG-07)** | notBreaching |
| 27 | CW Alarm | `TargetResponseTime` p95 > 1s, 300s, 3 of 3 | P2 | notBreaching |
| 28 | CW Alarm | `RejectedConnectionCount > 0` | P2 | notBreaching |
| 28b | CW Alarm | `TargetConnectionErrorCount > 10`, 60s, 3 of 5 | P2 | notBreaching |
| 29 | CW Alarm | `DaysToExpiry < 45` | P3 | breaching |
| 29b | CW Alarm | `DaysToExpiry < 14` | P2 | breaching |
| 29c | EB `aws.acm` | `ACM Certificate Renewal Action Required` | P2 | — |
| 29d | CW Alarm | `DaysToExpiry < 3` | **P1(PG-06)** | breaching |

**26 vs 26b**: 26번은 ELB 자체가 반환한 5xx(타깃 연결 실패 등), 26b는 애플리케이션이 반환한 5xx다. **둘은 다른 장애다.**

**29 시리즈**: v1은 `< 21일` 단일 P2였다. 갱신 실패를 늦게 감지하고, 반대로 임박(3일 미만)을 놓친다. 4단계로 분할했다.

## 6.6 데이터 — RDS

| # | 소스 | 조건 | 티어 | missing |
| --- | --- | --- | --- | --- |
| 30 | CW Alarm (Math) | `DatabaseConnections / <max_connections> > 0.95` | **P1(PG-03)** | breaching |
| 30b | CW Alarm (Math) | 동일 > 0.80 | P2 | breaching |
| 31 | RDS 이벤트 구독 | 카테고리: `failover`, `failure`, `availability` | **P1(PG-03)** | — |
| 32 | CW Alarm | `FreeLocalStorage < 2GB` | **P1(PG-03)** | breaching |
| 33 | CW Alarm | `AuroraReplicaLag > 1000`(ms), 300s, 3 of 3 | P2 | breaching |
| 34 | CW Alarm | `Deadlocks > 5`, 300s, 2 of 2 | P2 | notBreaching |
| 35 | CW Alarm | `DiskQueueDepth > 20`, 300s, 3 of 3 | P2 | breaching |
| 35b | CW Alarm | `CPUUtilization > 85`, 300s, 3 of 3 | P2 | breaching |
| 35c | CW Alarm | `FreeableMemory` < 인스턴스 메모리의 10% | P2 | breaching |
| 35d | CW Alarm | `SwapUsage > 500MB` | P2 | breaching |
| 35e | CW Alarm | `EngineUptime < 300`(초) — 재시작 감지 | **P1(PG-03)** | breaching |
| 35f | **Datadog 모니터** | `aws.rds.queries` 평시 대비 급락 (anomaly) | P2 | — |

**주의**

- `max_connections`는 CloudWatch 메트릭이 아니다. 인스턴스 클래스에 따라 동적이므로 Terraform 변수로 하드코딩한다 (**Q5**). **인스턴스 클래스 변경 시 알람도 수정해야 한다.**
- 31번 RDS 이벤트 구독은 **카테고리 전체를 구독하면 백업 완료 등 노이즈가 섞인다.** 위 3개만 선택.
- 35f는 정상 지표가 아니라 **침묵**을 감지한다. 이상탐지가 필요하므로 Datadog 담당. AWS 폴링 기반이라 10~20분 지연 → P2가 적절.

## 6.7 데이터 — ElastiCache

ElastiCache를 운영 중이고 `aws.elasticache.*` 메트릭이 이미 Datadog에 수집되고 있으나 v1(원안)에 알럿이 0건이었다.

**왜 치명적인가**

```
Redis 축출(Evictions) 발생
  → 세션이 조용히 사라짐 → 사용자가 로그아웃됨
  → 앱 CPU 정상, ALB 5xx 정상, RDS 정상 → 아무 알람도 안 울림
  → "가끔 로그아웃된다"는 문의로만 인지

Redis RejectedConnections 발생
  → 커넥션 획득 실패 → 앱이 캐시 미스로 처리하고 DB 폴백
  → DB 부하 급증 → RDS 알람이 울림
  → 원인을 DB에서 찾다가 반나절 소요   ← NAT 포트 고갈과 동일한 패턴
```

| # | 조건 | 티어 | missing |
| --- | --- | --- | --- |
| 39 | `RejectedConnections > 0`, `Sum`, 300s, 1 of 1 | **P1(PG-04)** | notBreaching |
| 40 | `Evictions > 0`, `Sum`, 600s, 3 of 3 | **P2 (조건부 P1)** | notBreaching |
| 41 | `EngineCPUUtilization > 90`, 60s, 3 of 5 | P2 | breaching |
| 41b | `EngineCPUUtilization > 99`, 60s, 5 of 5 | **P1(PG-04)** | breaching |
| 42 | `MasterLinkHealthStatus < 1`, `Minimum`, 300s | P2 | breaching |
| 43 | `CurrConnections` > 노드 한도 × 0.9 | P2 | breaching |
| 44 | `DatabaseMemoryUsagePercentage > 85` | P2 | breaching |
| 44b | `SwapUsage > 50MB` | P2 | breaching |
| 44c | `ReplicationLag > 5`(초) | P2 | breaching |
| 44d | `NetworkBandwidthOutAllowanceExceeded > 0` | P2 | notBreaching |
| 44e | `NetworkConntrackAllowanceExceeded > 0` | P2 | notBreaching |
| 44f | `MemoryFragmentationRatio > 1.5`, 1800s | P2 | breaching |
| 44g | **Datadog 모니터** — `CacheHitRate` 급락 (anomaly) | P2 | — |
| 44h | EB `aws.elasticache` — 페일오버 / 노드 교체 | P2 | — |

> ⚠️ **#40 Evictions 의 티어는 `maxmemory-policy` 값에 달려 있다 (Q2)**
>
> | 정책 | Evictions 의 의미 | 티어 |
> | --- | --- | --- |
> | `noeviction` | **쓰기 실패 발생.** 사용자 영향 즉시 | **P1(PG-04)** |
> | `allkeys-lru` / `volatile-lru` 등 | 설계된 정상 동작. 다만 세션 저장소면 로그아웃 발생 | P2 |
>
> **현재 기본값은 P2로 두었다.** 정책이 `noeviction`이면 6.7 표와 13.2 복합 알람 정의를 P1으로 변경한다.

⚠️ **`CPUUtilization`(전체)이 아니라 `EngineCPUUtilization`을 봐야 한다.** Redis는 명령 처리가 싱글 스레드이므로 전체 CPU가 30%여도 엔진 CPU가 100%면 이미 포화다.

⚠️ **44d/44e는 놓치기 쉬운 항목이다.** ElastiCache는 인스턴스 타입별 네트워크 한도가 있고, 이를 넘으면 CPU·메모리는 정상인데 지연이 튄다.

## 6.8 데이터 — SQS / 백업

| # | 소스 | 조건 | 티어 | missing |
| --- | --- | --- | --- | --- |
| 36 | CW Alarm | DLQ `ApproximateNumberOfMessagesVisible > 0`, 300s, 1 of 1 | **P1(PG-08)** | notBreaching |
| 37 | CW Alarm | `ApproximateAgeOfOldestMessage > 900`(초) | P2 | notBreaching |
| 38 | EB `aws.secretsmanager` | 로테이션 실패 | P2 | — |
| 38b | EB AWS Backup | 백업 작업 실패 | P2 | — |
| 38c | RDS 이벤트 구독 | 스냅샷 실패 | P2 | — |

## 6.9 애플리케이션 계층 — 신설 ⭐

> **v1의 가장 큰 공백이었다.** 1,351줄 전부가 AWS 리소스였고, 2장이 문제로 든 "외부 기관 연동 단절"의 실제 원인 대부분을 감지하지 못했다.

## 6.9.1 왜 필요한가

```
VPN TunnelState = L3 터널 상태

터널이 UP인데도 연동이 실패하는 경우:
  · 기관 API 인증서/토큰 만료
  · 기관 측 응답 포맷 변경
  · 기관 측 정기 점검 (터널 유지, API만 거부)
  · 기관 측 rate limit
  · 우리 쪽 파싱 로직이 새 응답을 못 읽음
```

이 경우 **모든 AWS 지표가 정상이다.** PG-01(VPN)은 울리지 않는다.

## 6.9.2 이미 수집 중인 메트릭

커스텀 메트릭 148개 중 다음이 이미 Datadog에 들어와 있다.

```
auth.dozen.count / auth.dozen.error / auth.dozen.latency.*
auth.institution.count / auth.institution.latency.*
auth.lock.error
banksalad.hira.dozen.auth.count
banksalad.hometax.dozen.auth.count
dozen.octover.api.count / dozen.octover.api.error
cms.consent.abnormal_errors
integration.status.issue
flathiddenbenefit.generate.count / .error
reward.grant.count / reward.grant.skipped.count
health.carenote.page.serve / .report.build / .report.create
hikaricp.connections.pending / .active / .max
jvm.threads.states
executor.queued / auth.executor.queue.size
logback.events
```

> ⚠️ **그런데 커스텀 메트릭 148개 중 어떤 대시보드·모니터·SLO에도 쓰이는 것이 3개뿐이다.** 145개가 방치되어 있다.
>
> `cms.consent.abnormal_errors`는 27일 전에 추가됐다. 누군가 문제를 겪고 "다음엔 알아야지"라며 계측을 넣었는데, **알럿을 걸지 않았으면 다음에도 못 알아챈다.**

## 6.9.3 감지 항목

**비용 0.** 메트릭이 이미 수집 중이고 Datadog 모니터만 걸면 된다. 그리고 DogStatsD 직접 수집이므로 **지연 1~2분**으로 P1에 쓸 수 있다 (3.2 참조).

### 기관 연동 (PG-09)

| # | 조건 | 티어 |
| --- | --- | --- |
| 61 | 기관별 인증 실패율 > 20%, 10분 | **P1(PG-09)** |
| 62 | **기관별 호출 침묵** — 15분간 호출 0건 | **P1(PG-09)** |
| 63 | `integration.status.issue > 0` | **P1(PG-09)** |
| 64 | 기관별 인증 지연 `auth.institution.latency.max > 30s` | P2 |
| 64b | `cms.consent.abnormal_errors > 0`, 10분 | P2 |
| 64c | `auth.lock.error` 급증 (anomaly) | P2 |
| 64d | `dozen.octover.api.error` 비율 > 10% | P2 |
| 64e | `flathiddenbenefit.generate.error > 0` | P2 |

```python
# 61 — 기관별 인증 실패율
sum(last_10m):
  sum:auth.dozen.error{*} by {institution}.as_count() /
  sum:auth.dozen.count{*} by {institution}.as_count() > 0.2

# 62 — 기관 호출 침묵 (터널 UP인데 API 레이어 단절)
sum(last_15m):sum:auth.institution.count{*} by {institution}.as_count() < 1
# notify_no_data: true, no_data_timeframe: 20

# 63 — 연동 이슈 지표
sum(last_5m):sum:integration.status.issue{*} by {institution} > 0

# 64 — 기관별 인증 지연
max(last_10m):max:auth.institution.latency.max{*} by {institution} > 30000

# 64b — 동의 이상
sum(last_10m):sum:cms.consent.abnormal_errors{*} > 0
```

> **#62가 핵심이다.** PG-01(터널 상태)의 보완물이며, 「번외 1편 — 프로메테우스는 왜 긁어가는가」의 **"침묵이 정보가 된다"** 를 그대로 적용한 것이다.
>
> 문서 전체가 "나쁜 값이 나왔다"만 잡고 있었고, **"아무 일도 안 일어나고 있다"** 를 잡는 항목이 #35f 하나뿐이었다.

### 리소스 포화 (PG-10)

| # | 조건 | 티어 |
| --- | --- | --- |
| 65 | `hikaricp.connections.pending > 10`, 5분 | **P1(PG-10)** |
| 66 | `jvm.threads.states{state:waiting}` 평시 × 3 초과 | **P1(PG-10)** |
| 67 | `executor.queued` 임계 초과 | P2 |
| 67b | `auth.executor.queue.size` 임계 초과 | P2 |
| 67c | `logback.events{level:error}` 급증 (anomaly) | P2 |
| 67d | `jvm.gc.pause.max > 1s`, 5분 | P2 |
| 67e | `process.files.open / process.files.max > 0.8` | P2 |
| **68** | **`datadog.dogstatsd.client.packets_dropped > 0`** | **P2** |

> ⚠️ **#68이 6.9 전체의 신뢰도를 결정한다**
>
> 앱 메트릭은 **DogStatsD(UDP)** 로 나간다. UDP는 "쏘고 잊는다"는 설계이므로 **유실되면 조용히 사라진다.** 즉 PG-09·PG-10이 침묵하는 이유가 두 가지다.
>
> ```
> ① 정말 아무 문제가 없다
> ② 메트릭이 유실되고 있다   ← 구분 불가
> ```
>
> 관련 메트릭이 이미 수집되고 있다.
>
> ```
> datadog.dogstatsd.client.packets_dropped
> datadog.dogstatsd.client.packets_dropped_queue
> datadog.dogstatsd.client.packets_dropped_writer
> datadog.dogstatsd.client.bytes_dropped
> datadog.dogstatsd.client.metric_dropped_on_receive
> ```
>
> **무과금이고, 6.9의 모든 항목이 이것에 의존한다.** 1차에 함께 건다.
>
> ```python
> sum(last_10m):sum:datadog.dogstatsd.client.packets_dropped{*} by {host}.as_count() > 0
> ```

```python
# 65 — 커넥션 풀 대기
avg(last_5m):avg:hikaricp.connections.pending{*} by {service} > 10

# 66 — 스레드가 멈춰서 기다림
avg(last_5m):avg:jvm.threads.states{state:waiting} by {service} > 30

# 67 — 스레드풀 큐 적재
avg(last_5m):avg:executor.queued{*} by {service} > 50

# 67c — 에러 로그 급증 (가장 값싼 조기 경보)
avg(last_15m):anomalies(sum:logback.events{level:error} by {service}.as_count(), 'basic', 3) > 0
```

> **PG-10이 잡는 시나리오**
>
> ```
> 증상: 요청 8초, 커넥션 풀 30/30 사용, 대기 47
>       DB: CPU 15%, 커넥션 평시, 데드락 0
> 원인: 트랜잭션 안에서 외부 기관 API 호출 → 응답 대기 중 커넥션 점유
> ```
>
> **6.6의 RDS 알람 12개 전부 정상으로 나온다.** ALB `TargetResponseTime`(#27, P2)만 울리고, 그건 원인을 가리키지 못한다. `jvm.threads.states{state:waiting}` 하나가 병목 위치를 특정한다.

## 6.9.4 방치된 메트릭 정리

145개 미사용 메트릭 중 **지울 것과 알럿을 걸 것을 구분해야 한다.**

| 분류 | 처리 |
| --- | --- |
| 비즈니스 에러 메트릭 | **알럿을 건다** (위 표) |
| 장애 대응용 (평시 조회 0회, 장애 시 결정적) | **보호 목록에 넣고 유지** — `jvm.threads.states`, `hikaricp.connections.pending`, `executor.queued`, `process.files.open` |
| 인테그레이션과 중복 | 삭제 검토 — 별도 과제 |

⚠️ **"30일 조회 0회"를 삭제 근거로 쓰면 안 된다.** 메트릭은 소급 수집이 불가능하므로, 장애 대응용 메트릭을 지우면 필요한 순간에 데이터가 없다.

## 6.10 보안 / 거버넌스

> **원칙: 전 항목을 P3(로그 적재)로 먼저 걸고 1~2주 발생량을 실측한 뒤, 일 0~2건인 것만 승격한다.** 하루 10건 넘는 항목은 조건을 좁히거나 P3로 유지한다.

| # | 소스 | 조건 | 티어 |
| --- | --- | --- | --- |
| 45 | EB `aws.guardduty` | `detail.severity >= 7` (numeric 매처) | **P1(PG-11)** |
| 45b | EB `aws.guardduty` | `4 <= severity < 7` | P3 |
| 46 | CloudTrail → EB | `ConsoleLogin` + `userIdentity.type: Root` | **P1(PG-11)** |
| 48 | CloudTrail → EB | `CreateAccessKey` (루트 대상) | **P1(PG-11)** |
| 48b | CloudTrail → EB | `CreateAccessKey` (일반) | P2 |
| 49 | AWS Config | SG 인바운드에 `0.0.0.0/0` 신규 추가 | P2 |
| 49b | CloudTrail → EB | `DeleteTrail` / `StopLogging` / `PutEventSelectors` | **P1(PG-11)** |
| 49c | CloudTrail → EB | KMS `DisableKey` / `ScheduleKeyDeletion` | **P1(PG-11)** |
| 49d | EB `aws.config` | Config rule NON_COMPLIANT 전환 | P3 |
| 50 | CW Alarm | WAF `BlockedRequests` — 먼저 count 모드로 관찰 | P3 → 실측 후 판단 |

**주의**

- 45번 `severity`는 **숫자**다. `"High"` 문자열 매칭은 동작하지 않는다.
- 46번 콘솔 로그인 CloudTrail 이벤트는 **us-east-1에만 기록된다.** 룰을 us-east-1에 만들어야 한다.
- 49b는 감사 로그 자체를 끄는 행위다. 침해 대응에서 1순위 신호.

## 6.11 메타 / 비용

| # | 소스 | 조건 | 티어 |
| --- | --- | --- | --- |
| 52 | EB `aws.health` | `eventTypeCategory: issue` | **P1(PG-13)** |
| 52b | EB `aws.health` | `scheduledChange` | P2 |
| 52c | EB `aws.health` | `accountNotification` | P3 |
| 53 | `AWS/Usage` | ENI / EIP / ECS 태스크 / Fargate vCPU 한도 > 80% | P2 |
| 53b | AWS Budgets | 월 예산 초과 예측 | P2 |

> ⚠️ **#14, #53의 실현 가능성 확인 필요 (Q6)**
>
> `AWS/Usage` 네임스페이스는 일부 리소스만 커버하고, **한도 값 자체를 메트릭으로 제공하지 않는 경우가 많다.** Service Quotas에서 CloudWatch 알람을 지원하는 쿼터도 제한적이다.
>
> 감시하려는 쿼터별로 개별 확인이 필요하다. 지원되지 않으면 Trusted Advisor나 별도 조회가 필요하고, 그건 3.1(커스텀 코드 없음)과 충돌한다. 그 경우 **해당 항목은 P3로 두고 주간 수동 확인**으로 대체한다.

## 6.12 1차 구축 대상

투자 대비 효과가 가장 큰 항목만 우선 구축한다. 2장 배경 표의 7개 문제와 1:1 대응한다.

| # | 항목 | 구현 | 알람 수 |
| --- | --- | --- | --- |
| 1 | **VPN TunnelState** (3세트 × 양방향) + PG-01 | CW Math + Composite | 6 + 1 |
| 2 | **SQS DLQ 메시지 수 > 0** + PG-08 | CW Alarm + Composite | DLQ 수 + 1 |
| 3 | **Aurora 커넥션 95% + RDS 이벤트 구독** + PG-03 | CW Math + 이벤트 구독 + Composite | 인스턴스 수 + 1 + 1 |
| 4 | **NAT ErrorPortAllocation > 0** + PG-02 | CW Alarm + Composite | NAT GW 수 + 1 |
| 5 | **ECS 배치 실패 EventBridge 룰** | EB 룰 | 1 |
| 6 | **ElastiCache** #39, #41b + PG-04 | CW Alarm + Composite | 2 × 노드 수 + 1 |
| 7 | ⭐ **기관 연동 3항목 + PG-09** | **Datadog 모니터** | 3 (비용 0) |
| 8 | ⭐ **커넥션 풀·스레드 2항목 + PG-10** | **Datadog 모니터** | 2 (비용 0) |

> **7·8번을 1차에 넣은 이유**: 비용 0, 소요 1시간, 그리고 2장 배경의 근본 원인을 잡는다. CloudWatch 알람 145개를 만드는 작업보다 가치가 크다.

---

# 7. 구성 요소

## 7.1 SNS 토픽

| 토픽 | 리전 | 구독 |
| --- | --- | --- |
| `{알림토픽-P1}` | ap-northeast-2 | Datadog HTTPS, ChatBot |
| `{알림토픽-P2}` | ap-northeast-2 | ChatBot |
| `{알림토픽-P3}` | ap-northeast-2 | Datadog HTTPS (하트비트 전용) |
| `{알림토픽-P1-버지니아}` | us-east-1 | Datadog HTTPS, ChatBot |
| `{알림토픽-P2-버지니아}` | us-east-1 | ChatBot |

> ⚠️ **v1 정정 — 구독 목록에서 `Logs` 를 제거했다.** SNS는 CloudWatch Logs를 구독할 수 없다 (4.1 참조). 기록 사본은 Datadog Event + Slack으로 충분하다.

> ⚠️ **us-east-1 세트가 필요한 이유**
>
> CloudWatch 알람은 **같은 리전의 SNS 토픽만** 액션으로 지정할 수 있다. 그리고 다음은 us-east-1에만 존재한다.
> - ACM 인증서 만료 (CloudFront용)
> - Cost Anomaly / Budgets
> - Route 53 헬스체크 메트릭
> - **루트 계정 콘솔 로그인 CloudTrail 이벤트** (6.10 #46)
> - AWS Health 글로벌 서비스 이벤트

토픽 정책에는 `AWS:SourceAccount` 조건을 반드시 넣는다. 없으면 다른 계정이 발행할 수 있다.

## 7.2 Datadog 구독 URL

```
https://<SITE>/intake/webhook/sns?api_key=<API_KEY>&oncall_team=<TEAM_HANDLE>
```

| 항목 | 지침 |
| --- | --- |
| `SITE` | Datadog 접속 시 주소창 호스트를 그대로. **추측 금지** (`datadoghq.com` / `datadoghq.eu` / `ap1.datadoghq.com` 등) |
| `API_KEY` | Organization Settings → API Keys. **이 용도 전용 키 발급** |
| `TEAM_HANDLE` | On-Call 팀 핸들. 팀 생성이 선행되어야 함 |
| 프로토콜 | HTTPS |
| Raw message delivery | **체크 해제** (Datadog intake는 SNS 봉투를 파싱하도록 설계됨) |

Datadog이 SNS 메시지를 받으면 이벤트를 생성하므로 기록용 별도 구독은 필요하지 않다. **단 이벤트 생성이 곧 페이지 발생은 아니다 — 4.3 및 8.1 참조.**

> 🔒 **보안 주의**
>
> API 키가 구독 엔드포인트 URL에 평문으로 저장된다. `sns:GetSubscriptionAttributes` 권한 보유자는 이 키를 조회할 수 있다.
>
> 조치: 해당 권한을 인프라 담당으로 제한, 전용 API 키 발급, CloudTrail 감시, **그리고 이 구독은 Terraform으로 만들지 않는다**(9.11 #2 참조).

**구독 존재 확인**

```bash
aws sns list-subscriptions-by-topic --topic-arn <p1-arn> \
  --query "Subscriptions[?Protocol=='https'].[Endpoint]" --output text \
  | sed 's/api_key=[^&]*/api_key=***/'
```

## 7.3 암호화 — AWS 관리형 키를 쓰면 조용히 실패한다

`alias/aws/sns`(AWS 관리형 키)로 토픽을 암호화하면 **CloudWatch 알람이 조용히 실패한다.** 서비스 프린시펄이 관리형 키를 사용할 권한을 얻을 수 없기 때문이다. 알람 상태는 정상적으로 ALARM으로 바뀌지만 **알림만 전달되지 않는다.**

고객 관리형 키(CMK)를 생성하고 키 정책에 다음을 허용한다.

| 프린시펄 | 용도 |
| --- | --- |
| `cloudwatch.amazonaws.com` | CloudWatch 알람 (복합 알람 포함) |
| `events.amazonaws.com` | EventBridge 룰, EventBridge Scheduler |
| `rds.amazonaws.com` | RDS 이벤트 구독 |

액션: `kms:GenerateDataKey*`, `kms:Decrypt`

⚠️ **소스를 추가할 때마다 프린시펄을 추가해야 한다.** 예: Budgets 알림을 붙이면 `budgets.amazonaws.com`. 잊으면 같은 방식으로 조용히 실패한다.

⚠️ **KMS 키는 리전 리소스다.** us-east-1 토픽에는 us-east-1 CMK가 별도로 필요하다 (9.6 참조). v1은 키를 1개만 정의해서 us-east-1 세트가 apply되지 않았다.

## 7.4 EventBridge Input Transformer

룰의 타겟으로 SNS를 지정하면 이벤트 JSON 원본이 그대로 전달되어 알림 제목이 판독 불가능해진다. Lambda 대신 Input Transformer로 해결한다.

```json
{
  "InputPathsMap": {
    "eventName": "$.detail.eventName",
    "cluster": "$.detail.clusterArn",
    "reason": "$.detail.reason",
    "time": "$.time"
  },
  "InputTemplate": "\"[P2] ECS <eventName> | cluster=<cluster> | reason=<reason> | at=<time> | #env:prod #source:ecs #tier:p2\""
}
```

⚠️ **JSONPath가 이벤트 구조와 맞지 않으면 변환에 실패하고 이벤트가 조용히 드롭된다.** GuardDuty(PG-11), `aws.health`(PG-13)가 이 경로이므로 8.2의 `FailedInvocations` 알람이 필수다.

## 7.5 전달 실패 대비

SNS는 메시지를 보관하지 않으므로 구독자가 응답하지 않으면 재시도 후 폐기한다. P1/P2 구독에는 두 가지를 적용한다.

1. **재시도 정책** — 지수 백오프로 최대 1시간까지 재시도
2. **구독 DLQ** — 실패 메시지를 SQS로 적재하고, 이 DLQ에 다시 알람을 건다

> 🔁 **P1 전달 실패 알람은 p2 토픽으로 보낸다.** p1으로 보내면 무한 루프가 발생한다.

## 7.6 알람 필수 설정

| 설정 | 값 | 이유 |
| --- | --- | --- |
| `treat_missing_data` | **6.1 분기 규칙에 따라** | 일괄 `breaching`은 야간 오탐 발생 |
| `alarm_actions` (개별 알람) | **비워둠** | P1은 복합 알람만 발화 (3.4) |
| `alarm_actions` (복합 알람) | 티어 토픽 ARN | — |
| `ok_actions` | **P1이면 p2 토픽**, 그 외 동일 티어 | 복구 시 전화 재발신 방지 |
| `insufficient_data_actions` | 비워둠 | `treat_missing_data`와 중복 |
| `alarm_description` | **런북 링크 (필수)** | 새벽에 깬 사람이 판단할 근거 |
| `datapoints_to_alarm` | 명시 | 미지정 시 스파이크 1회에 발동 |
| tags | `tier`, `env`, `service`, `layer` | 라우팅 검증, 티어 승격, 억제 계층 구성 |

## 7.7 알람 네이밍

```
개별 알람:  {env}-{service}-{resource}-{condition}
복합 알람:  composite-{layer}-{incident}

prod-claim-vpn-{기관A}-tunnel-down
prod-claim-sqs-dlq-not-empty
prod-core-aurora-connections-critical
prod-core-nat-port-exhaustion
prod-core-redis-001-rejected-conn

composite-l1-vpn-down
composite-l2-rds-incident
composite-l4-app-5xx
```

`env`, `service`는 확정된 태그 스키마 값을 재사용한다(lowercase-kebab). **티어는 이름에 넣지 않는다** (5.5 참조).

## 7.8 해제(resolve) 처리 — Q1 검증 후 확정

```
03:00  ALARM → SNS → Datadog Event → 페이지 발생
03:15  자동 복구 → OK → SNS → Datadog Event ("OK" 이벤트)
         ↓
       이 OK 이벤트가 열려있는 페이지를 닫아주는가?
```

Datadog이 ALARM 이벤트와 OK 이벤트를 같은 사건으로 인식해야 자동 종료된다. **SNS intake 경로에서 이것이 어떻게 처리되는지 검증이 필요하다** (8.1 ④번).

| 검증 결과 | 정책 |
| --- | --- |
| 자동 종료됨 | `ok_actions`를 p1 토픽으로 두고 자동 종료에 의존 |
| 자동 종료 안 됨 | `ok_actions`는 **p2 토픽만**. 페이지 종료는 온콜이 수동으로 처리하며, 이를 런북에 명시 |

**기본값은 후자(p2 토픽)로 설정해두었다.** 검증 결과가 전자면 완화할 수 있지만, 반대 방향은 새벽에 전화가 두 번 오는 사고가 된다.

---

# 8. 알럿 파이프라인 자기 감시

알럿 시스템이 감시 대상과 같은 AWS 안에 있다. Datadog은 외부 SaaS였기 때문에 AWS가 죽어도 "데이터가 안 온다"고 알려줄 수 있었다. **감지를 AWS로 옮기면 그 안전망이 사라진다.**

## 8.1 P1 경로 검증 절차 (최우선)

알람을 대량 생성하기 **전에** 반드시 수행한다.

```bash
# 테스트용 더미 알람 1개를 콘솔로 만들고 사용. 검증 후 삭제.
aws cloudwatch set-alarm-state \
  --alarm-name delivery-test-dummy \
  --state-value ALARM --state-reason "delivery test"
```

| # | 확인 항목 | 실패 시 의미 |
| --- | --- | --- |
| ① | Datadog **Events Explorer**에 이벤트가 뜨는가 | SNS→Datadog 구간 문제 (URL, API 키, SITE, raw delivery, KMS 정책) |
| ② | **전화가 실제로 오는가** | 이벤트는 생성되지만 페이지가 안 됨 → **Event Monitor 구성 필요** |
| ③ | On-Call 스케줄상 **맞는 사람**에게 오는가 | 팀 핸들 / 에스컬레이션 폴리시 문제 |
| ④ | `--state-value OK` 후 **페이지가 자동 종료되는가** | 7.8 정책 결정 근거 |

⚠️ **①만 확인하고 넘어가면 안 된다.** "이벤트가 잘 뜨네" 하고 배포했는데 실제 장애에서 전화가 오지 않는 것이 이 설계의 가장 조용한 실패 모드다.

②가 실패하면 Datadog 측에 Event Monitor를 하나 만들어야 한다.

```python
# Datadog Event Monitor (②가 실패할 경우)
events("tags:tier:p1 source:amazon_sns").rollup("count").last("5m") > 0
# 통보: @oncall-<team-handle>
```

## 8.2 상시 감시 항목

| # | 항목 | 방법 | 티어 |
| --- | --- | --- | --- |
| 51a | SNS 배달 실패 | `AWS/SNS` `NumberOfNotificationsFailed > 0` | **P1(PG-12)** |
| 51b | 구독 DLQ 적재 | DLQ `ApproximateNumberOfMessagesVisible > 0` | **P1(PG-12)** |
| 51c | **EventBridge 룰 실패** | `AWS/Events` `FailedInvocations > 0` | P2 |
| 51d | EventBridge 스로틀 | `AWS/Events` `ThrottledRules > 0` | P2 |
| 51e | 룰 타겟 DLQ | EventBridge 타겟 단위 DLQ 설정 + 깊이 알람 | P2 |
| 51f | Datadog 모니터 no-data | 전 Datadog 모니터에 `notify_no_data: true` | P2 |
| 51g | AWS 인테그레이션 장애 | Datadog 인테그레이션 상태 모니터 | P2 |
| 51h | **하트비트 단절** | 8.3 (a) | **P1(PG-12)** |

⚠️ **51a/51c/51d는 `AWS/SNS`, `AWS/Events` 네임스페이스가 필요하다.** CloudWatch 알람으로 만들면 인테그레이션과 무관하게 동작하지만, Datadog에서 보려면 10.2의 네임스페이스 활성화가 필요하다.

## 8.3 Dead man's switch (필수)

51a~51e는 **AWS 측 감지가 동작한다는 전제**에 의존한다. 다음 실패 모드는 어느 것도 잡지 못한다.

- Datadog API 키 로테이션 → 401 (DLQ로는 잡힘)
- **On-Call 스케줄이 비어 있음** (담당자 퇴사, 로테이션 만료) → **200 OK로 응답되고 아무도 안 받음. DLQ에 안 잡힘**
- 팀 핸들 변경 → 동일
- EventBridge 룰 삭제 → 아무 신호 없음

두 가지를 함께 넣는다.

### (a) 자동 하트비트

```
EventBridge Scheduler (15분마다)
  → 합성 이벤트 → p3 토픽 → Datadog
  → Datadog Event Monitor 에 notify_no_data: 45m
  → 경로 단절 감지 → PG-12
```

**판단 주체가 AWS 밖(Datadog)에 있으므로 리전 장애에도 동작한다.**

```
ap-northeast-2 리전 장애
  → EventBridge Scheduler 죽음 → 하트비트 발행 중단
  → Datadog(외부)이 45분 no-data 감지 → 전화 ✅

  그런데 "무슨 장애인지"는 모른다
  → 7.1 us-east-1 세트의 aws.health (eventTypeCategory: issue, PG-13) 가 그것을 알려준다 ✅
```

> **7.1의 us-east-1 세트와 8.3의 하트비트는 서로를 보완한다.**
> 하트비트는 "알럿 경로가 죽었다"를 알려주고, us-east-1의 `aws.health`는 "무엇 때문인지"를 알려준다. 둘 중 하나만 있으면 리전 장애에 대응할 수 없다.

⚠️ **EventBridge Scheduler 자체가 단일 장애점이다.** Scheduler만 죽어도 하트비트가 멈추고 PG-12가 발화한다. **허용해야 하는 오탐**이며, 판단 절차를 부록 C-12에 명시했다.

### (b) 월 1회 실제 페이지 훈련

```
캘린더 반복 등록. set-alarm-state 로 P1 발생 → 전화 수신 확인
→ (a)가 못 잡는 "200 OK인데 아무도 안 받음" 을 잡는 유일한 방법
```

**한 번 하고 끝나면 3개월 뒤 경로가 끊긴 걸 모른다.** 반복 일정으로 등록한다.

## 8.4 에스컬레이션 폴리시 — 최종 단계 필수

2시트는 온콜 1명 + 백업 1명이다. **둘 다 부재(휴가·비행기·수면)면 페이지가 갈 곳이 없다.**

```
1단계  온콜        전화, 5분 대기
2단계  백업        전화, 5분 대기
3단계  #infra-alert 채널 @here + 전원 전화    ← 필수
```

사람이 아니라 채널이면 부재 개념이 없다.

## 8.5 오탐 폭주 시 롤백 절차

> ⚠️ **v1 정정 — SNS에 구독 "비활성" 기능은 없다.** 삭제만 가능하고, 삭제하면 Datadog 구독을 다시 만들면서 새벽에 API 키를 재입력해야 한다. 실수 확률이 높다.
>
> **필터 정책으로 교체한다** — 구독을 유지한 채 메시지만 차단.

```bash
# 1) Datadog On-Call 에서 해당 팀 override / mute   ← 가장 빠름. 이걸 먼저.

# 2) 문제 알람 식별 후 액션만 비활성
aws cloudwatch disable-alarm-actions \
  --alarm-names composite-l2-redis-incident

# 3) 최악의 경우 — SNS 구독에 전부 거부 필터 적용 (구독 유지)
aws sns set-subscription-attributes \
  --subscription-arn <p1-datadog-sub-arn> \
  --attribute-name FilterPolicy \
  --attribute-value '{"__mute":["true"]}'
# 발행 메시지에 __mute 속성이 없으므로 전부 걸러진다

# 4) 해제
aws sns set-subscription-attributes \
  --subscription-arn <p1-datadog-sub-arn> \
  --attribute-name FilterPolicy --attribute-value '{}'

aws cloudwatch enable-alarm-actions --alarm-names <...>
```

⚠️ **2번 또는 3번을 쓰면 반드시 티켓을 남긴다.** 비활성 상태를 잊으면 실제 장애를 놓친다. 다음 업무시간에 Terraform으로 정식 수정 후 재활성한다.

---

# 9. Terraform 구성

## 9.1 왜 알람이 첫 IaC 대상으로 안전한가

현재 Terraform 없이 수동 관리 중이다. **알람만 Terraform으로 도입하는 것은 타협이 아니라 정석적인 점진 도입이다.**

| 근거 | 설명 |
| --- | --- |
| **참조만 하고 생성하지 않음** | 알람은 기존 리소스를 dimension 문자열로만 가리킨다. `data` 소스조차 불필요. **기존 인프라를 `import`할 필요가 전혀 없다** |
| **State에 없는 리소스는 무시** | 콘솔로 만든 VPC/SG/RDS/ECS와 완전히 격리된다 |
| **실패 비용이 0** | 최악의 결과가 "알림이 안 옴" = 현재 상태. SG나 RDS를 첫 대상으로 하면 서비스 중단 위험 |
| **반복 구조** | `for_each`로 145개. IaC 이득이 가장 큰 형태 |

## 9.2 관리 경계

**"알람만"이 아니라 "알럿 스택"이 단위다.** 알람 → 토픽 ARN → 토픽 정책 → KMS 키가 사슬로 엮여 있어서, 중간을 수동으로 두면 7.3의 조용한 실패를 Terraform이 검증해줄 수 없다.

| | 리소스 | Terraform | 비고 |
| --- | --- | --- | --- |
| ✅ | `aws_cloudwatch_metric_alarm` | 넣음 | 약 145개 |
| ✅ | `aws_cloudwatch_composite_alarm` | 넣음 | 페이지 경로 12개 + 억제 계층 |
| ✅ | `aws_sns_topic` × 5 | 넣음 | 알람이 ARN 참조 |
| ✅ | `aws_sns_topic_policy` | 넣음 | 서비스 프린시펄 |
| ✅ | `aws_kms_key` × 2 (리전별) | 넣음 | 7.3의 CMK |
| ✅ | `aws_cloudwatch_event_rule` / `_target` | 넣음 | EventBridge도 참조만 함 |
| ✅ | `aws_scheduler_schedule` (하트비트) | 넣음 | 8.3 (a) |
| ✅ | `aws_sqs_queue` (구독 DLQ) | 넣음 | 7.5 |
| ⚠️ | `aws_sns_topic_subscription` (Datadog HTTPS) | **수동** | API 키가 state에 평문 저장됨. 구독은 리전당 1~2개뿐이라 IaC 이득 0, 리스크만 발생 |
| ❌ | VPC, SG, ALB, RDS, ECS, IAM | **절대 안 넣음** | 수동 관리 유지 |
| ⏭ | Datadog 리소스 (6.9 모니터 포함) | 2단계 | `datadog` provider로 별도 state. 초기엔 UI로 생성 |

## 9.3 디렉토리 구조

```
infra-alerting/
├── backend.tf                  # S3 state (알럿 전용)
├── providers.tf                # ap-northeast-2 + us-east-1 alias
├── locals.tf                   # topic_arns 등 공통값
├── kms.tf                      # 리전별 CMK 2개
├── sns.tf                      # 리전별 토픽
├── alarms-vpn.tf               # Metric Math
├── alarms-rds.tf
├── alarms-elasticache.tf
├── alarms-sqs.tf
├── alarms-nat.tf
├── alarms-alb.tf
├── alarms-lambda.tf
├── alarms-use1.tf              # us-east-1 전용 (ACM 등)
├── eventbridge.tf
├── heartbeat.tf                # 8.3 (a)
├── composite.tf                # 페이지 경로 12개 + 억제 계층
├── terraform.tfvars
└── modules/
    ├── cw-alarm/               # 단순 알람 (약 130개)
    └── cw-alarm-math/          # Metric Math 알람 (약 15개)
```

## 9.4 backend

```hcl
terraform {
  required_version = ">= 1.10"
  backend "s3" {
    bucket       = "{상태버킷}"
    key          = "alerting/terraform.tfstate"
    region       = "ap-northeast-2"
    encrypt      = true
    use_lockfile = true          # Terraform 1.10+ — DynamoDB 불필요
  }
}
```

1.10 미만이면 `dynamodb_table`로 락을 잡는다.

### State 버킷 부트스트랩 (수동 — 닭과 달걀)

```bash
aws s3api create-bucket --bucket {상태버킷} \
  --region ap-northeast-2 \
  --create-bucket-configuration LocationConstraint=ap-northeast-2

aws s3api put-bucket-versioning --bucket {상태버킷} \
  --versioning-configuration Status=Enabled

aws s3api put-bucket-encryption --bucket {상태버킷} \
  --server-side-encryption-configuration \
  '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"aws:kms"}}]}'

aws s3api put-public-access-block --bucket {상태버킷} \
  --public-access-block-configuration \
  BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
```

**버전관리를 반드시 켠다.** state가 깨졌을 때 되돌릴 유일한 수단이다.

## 9.5 providers

```hcl
provider "aws" {
  region = "ap-northeast-2"
}

provider "aws" {
  alias  = "use1"
  region = "us-east-1"
}
```

## 9.6 KMS — 리전별 2개 ⚠️ v1 누락

**KMS 키는 리전 리소스다.** us-east-1 토픽을 ap-northeast-2 키로 암호화할 수 없다. v1은 키를 1개만 정의해서 us-east-1 세트가 apply되지 않았다.

```hcl
data "aws_caller_identity" "me" {}

locals {
  kms_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "AllowRootAccountAdmin"
        Effect    = "Allow"
        Principal = { AWS = "arn:aws:iam::${data.aws_caller_identity.me.account_id}:root" }
        Action    = "kms:*"
        Resource  = "*"
      },
      {
        Sid    = "AllowAwsServicesToEncrypt"
        Effect = "Allow"
        Principal = {
          Service = [
            "cloudwatch.amazonaws.com",
            "events.amazonaws.com",
            "scheduler.amazonaws.com",
            "rds.amazonaws.com",
          ]
        }
        Action   = ["kms:GenerateDataKey*", "kms:Decrypt"]
        Resource = "*"
      },
    ]
  })
}

# ap-northeast-2
resource "aws_kms_key" "alerts" {
  description         = "SNS alert topics encryption (ap-northeast-2)"
  enable_key_rotation = true
  policy              = local.kms_policy
}

resource "aws_kms_alias" "alerts" {
  name          = "alias/{알림토픽}"
  target_key_id = aws_kms_key.alerts.key_id
}

# us-east-1  ← v1 누락
resource "aws_kms_key" "alerts_use1" {
  provider            = aws.use1
  description         = "SNS alert topics encryption (us-east-1)"
  enable_key_rotation = true
  policy              = local.kms_policy
}

resource "aws_kms_alias" "alerts_use1" {
  provider      = aws.use1
  name          = "alias/{알림토픽}"
  target_key_id = aws_kms_key.alerts_use1.key_id
}
```

## 9.7 SNS — 리전별

```hcl
locals {
  tiers      = ["p1", "p2", "p3"]
  tiers_use1 = ["p1", "p2"]      # us-east-1 에는 P3 불필요
}

# ── ap-northeast-2 ──────────────────────────────
resource "aws_sns_topic" "alerts" {
  for_each          = toset(local.tiers)
  name              = "{알림토픽}-${each.key}"
  kms_master_key_id = aws_kms_key.alerts.id
}

resource "aws_sns_topic_policy" "alerts" {
  for_each = aws_sns_topic.alerts
  arn      = each.value.arn
  policy   = data.aws_iam_policy_document.topic[each.key].json
}

# ── us-east-1  ← v1 누락 ────────────────────────
resource "aws_sns_topic" "alerts_use1" {
  provider          = aws.use1
  for_each          = toset(local.tiers_use1)
  name              = "{알림토픽}-${each.key}-use1"
  kms_master_key_id = aws_kms_key.alerts_use1.id
}

resource "aws_sns_topic_policy" "alerts_use1" {
  provider = aws.use1
  for_each = aws_sns_topic.alerts_use1
  arn      = each.value.arn
  policy   = data.aws_iam_policy_document.topic_use1[each.key].json
}

data "aws_iam_policy_document" "topic" {
  for_each = aws_sns_topic.alerts
  statement {
    effect  = "Allow"
    actions = ["SNS:Publish"]
    principals {
      type = "Service"
      identifiers = [
        "cloudwatch.amazonaws.com",
        "events.amazonaws.com",
        "scheduler.amazonaws.com",
        "rds.amazonaws.com",
      ]
    }
    resources = [each.value.arn]
    condition {
      test     = "StringEquals"
      variable = "AWS:SourceAccount"
      values   = [data.aws_caller_identity.me.account_id]
    }
  }
}

data "aws_iam_policy_document" "topic_use1" {
  for_each = aws_sns_topic.alerts_use1
  # 위와 동일 구조
  statement {
    effect  = "Allow"
    actions = ["SNS:Publish"]
    principals {
      type        = "Service"
      identifiers = ["cloudwatch.amazonaws.com", "events.amazonaws.com"]
    }
    resources = [each.value.arn]
    condition {
      test     = "StringEquals"
      variable = "AWS:SourceAccount"
      values   = [data.aws_caller_identity.me.account_id]
    }
  }
}
```

## 9.8 locals — 공통값

v1은 `{ for k, v in aws_sns_topic.alerts : k => v.arn }` 를 파일마다 반복했다. 한 번만 정의한다.

```hcl
# locals.tf
locals {
  topic_arns      = { for k, v in aws_sns_topic.alerts      : k => v.arn }
  topic_arns_use1 = { for k, v in aws_sns_topic.alerts_use1 : k => v.arn }

  runbook_base = "https://<노션-런북-URL>"

  common_tags = {
    env        = "prod"
    managed_by = "terraform"
    stack      = "alerting"
  }
}
```

## 9.9 모듈 1 — 단순 알람 (약 130개)

```hcl
# modules/cw-alarm/variables.tf
variable "name"         { type = string }
variable "namespace"    { type = string }
variable "metric_name"  { type = string }
variable "dimensions"   { type = map(string) }
variable "statistic"    { type = string  default = "Average" }
variable "extended_statistic" { type = string default = null }   # p95 등
variable "period"       { type = number  default = 60 }
variable "threshold"    { type = number }
variable "comparison"   { type = string  default = "GreaterThanThreshold" }
variable "eval_periods" { type = number  default = 5 }
variable "datapoints"   { type = number  default = 3 }
variable "missing_data" { type = string }              # 기본값 없음 — 판단 강제
variable "tier"         { type = string }
variable "env"          { type = string }
variable "layer"        { type = string  default = null }   # l1~l4, app, sec, meta
variable "paged"        { type = bool    default = false }  # true 면 직접 액션 (P2/P3용)
variable "topic_arns"   { type = map(string) }
variable "runbook_url"  { type = string }
variable "tags"         { type = map(string) default = {} }

variable "tier_env_rule" {
  type    = bool
  default = true
  validation {
    condition     = var.tier_env_rule
    error_message = "placeholder"
  }
}
```

```hcl
# modules/cw-alarm/main.tf

# 5.4 환경별 티어 규칙 강제
locals {
  tier_allowed = {
    prod = ["p1", "p2", "p3"]
    stg  = ["p2", "p3"]
    dev  = ["p3"]
  }
}

resource "null_resource" "validate_tier" {
  lifecycle {
    precondition {
      condition     = contains(local.tier_allowed[var.env], var.tier)
      error_message = "환경 ${var.env} 에서 티어 ${var.tier} 는 허용되지 않습니다. (5.4 참조)"
    }
    precondition {
      condition     = var.runbook_url != null && var.runbook_url != ""
      error_message = "런북 없는 알람은 만들 수 없습니다. (3.6 / D9)"
    }
  }
}

resource "aws_cloudwatch_metric_alarm" "this" {
  alarm_name          = var.name
  namespace           = var.namespace
  metric_name         = var.metric_name
  dimensions          = var.dimensions
  statistic           = var.extended_statistic == null ? var.statistic : null
  extended_statistic  = var.extended_statistic
  period              = var.period
  threshold           = var.threshold
  comparison_operator = var.comparison
  evaluation_periods  = var.eval_periods
  datapoints_to_alarm = var.datapoints
  treat_missing_data  = var.missing_data

  # P1 개별 알람은 액션 없음 — 복합 알람이 대표 발화 (3.4)
  alarm_actions = var.tier == "p1" && !var.paged ? [] : [var.topic_arns[var.tier]]
  ok_actions    = var.tier == "p1" && !var.paged ? [] : [var.topic_arns[var.tier == "p1" ? "p2" : var.tier]]

  alarm_description = "runbook: ${var.runbook_url}"
  tags = merge(var.tags, {
    tier  = var.tier
    env   = var.env
    layer = var.layer
  })
}
```

```hcl
# modules/cw-alarm/outputs.tf   ← v1 누락. 복합 알람이 이름을 참조해야 함
output "alarm_name" { value = aws_cloudwatch_metric_alarm.this.alarm_name }
output "alarm_arn"  { value = aws_cloudwatch_metric_alarm.this.arn }
```

**설계 결정이 코드에 강제된다.**

| 코드 | 강제하는 것 |
| --- | --- |
| `missing_data` 기본값 없음 | 알람 추가 시마다 상태 게이지 / 카운터 판단 강제 (6.1) |
| `validate_tier` precondition | stg/dev에 P1 생성 불가 (5.4) |
| `runbook_url` precondition | 런북 없는 알람 생성 불가 (3.6 / D9) |
| `alarm_actions` 삼항 | P1 개별 알람은 액션 없음 → 전화 폭주 방지 (3.4) |
| `ok_actions` 삼항 | P1 복구 시 전화 재발신 방지 (7.6) |
| `outputs` | 복합 알람이 이름을 문자열이 아니라 참조로 받음 (13.2) |

## 9.10 모듈 2 — Metric Math 알람 ⚠️ v1 누락

v1은 VPN만 raw 리소스로 다뤘다. 그런데 Math 알람은 **6종**이고, 그중 5종이 P1이다.

```
#1    desired - running                       (PG-05)
#10   GroupDesiredCapacity - GroupInService
#15   Errors / Invocations
#22   VPN 터널 합산 (이중화)
#26b  HTTPCode_Target_5XX / RequestCount      (PG-07)
#30   DatabaseConnections / max_connections   (PG-03)
```

**raw 리소스로 흩어지면 9.9 모듈이 강제하던 규칙이 전부 깨진다.** 가장 중요한 알람이 가장 느슨하게 관리된다.

```hcl
# modules/cw-alarm-math/variables.tf
variable "name"        { type = string }
variable "expression"  { type = string }              # "m0 - m1" / "m0 / m1"
variable "metrics" {
  type = list(object({
    namespace   = string
    metric_name = string
    dimensions  = map(string)
    stat        = string
    period      = number
  }))
}
variable "threshold"    { type = number }
variable "comparison"   { type = string default = "GreaterThanThreshold" }
variable "eval_periods" { type = number default = 5 }
variable "datapoints"   { type = number default = 3 }
variable "missing_data" { type = string }
variable "tier"         { type = string }
variable "env"          { type = string }
variable "layer"        { type = string default = null }
variable "paged"        { type = bool   default = false }
variable "topic_arns"   { type = map(string) }
variable "runbook_url"  { type = string }
variable "tags"         { type = map(string) default = {} }
```

```hcl
# modules/cw-alarm-math/main.tf
locals {
  tier_allowed = {
    prod = ["p1", "p2", "p3"]
    stg  = ["p2", "p3"]
    dev  = ["p3"]
  }
}

resource "null_resource" "validate" {
  lifecycle {
    precondition {
      condition     = contains(local.tier_allowed[var.env], var.tier)
      error_message = "환경 ${var.env} 에서 티어 ${var.tier} 는 허용되지 않습니다."
    }
    precondition {
      condition     = var.runbook_url != ""
      error_message = "런북 없는 알람은 만들 수 없습니다."
    }
  }
}

resource "aws_cloudwatch_metric_alarm" "this" {
  alarm_name          = var.name
  comparison_operator = var.comparison
  threshold           = var.threshold
  evaluation_periods  = var.eval_periods
  datapoints_to_alarm = var.datapoints
  treat_missing_data  = var.missing_data

  metric_query {
    id          = "result"
    expression  = var.expression
    label       = var.name
    return_data = true
  }

  dynamic "metric_query" {
    for_each = var.metrics
    content {
      id = "m${metric_query.key}"
      metric {
        namespace   = metric_query.value.namespace
        metric_name = metric_query.value.metric_name
        dimensions  = metric_query.value.dimensions
        stat        = metric_query.value.stat
        period      = metric_query.value.period
      }
    }
  }

  alarm_actions = var.tier == "p1" && !var.paged ? [] : [var.topic_arns[var.tier]]
  ok_actions    = var.tier == "p1" && !var.paged ? [] : [var.topic_arns[var.tier == "p1" ? "p2" : var.tier]]

  alarm_description = "runbook: ${var.runbook_url}"
  tags = merge(var.tags, { tier = var.tier, env = var.env, layer = var.layer })
}

output "alarm_name" { value = aws_cloudwatch_metric_alarm.this.alarm_name }
```

⚠️ **Math 알람은 식에 포함된 메트릭 수만큼 과금된다.** `m0 - m1` 알람은 $0.10이 아니라 $0.20이다.

## 9.11 사용 예 — ElastiCache

```hcl
locals {
  redis_nodes = var.elasticache_node_ids   # 예: ["prod-redis-001", ...]

  redis_alarms = {
    rejected-conn  = { metric = "RejectedConnections",                  threshold = 0,        tier = "p1", missing = "notBreaching", stat = "Sum",     cmp = "GreaterThanThreshold" }
    engine-cpu-crit= { metric = "EngineCPUUtilization",                 threshold = 99,       tier = "p1", missing = "breaching",    stat = "Average", cmp = "GreaterThanThreshold" }
    evictions      = { metric = "Evictions",                            threshold = 0,        tier = "p2", missing = "notBreaching", stat = "Sum",     cmp = "GreaterThanThreshold" }  # Q2: noeviction 이면 p1
    engine-cpu     = { metric = "EngineCPUUtilization",                 threshold = 90,       tier = "p2", missing = "breaching",    stat = "Average", cmp = "GreaterThanThreshold" }
    link-unhealthy = { metric = "MasterLinkHealthStatus",               threshold = 1,        tier = "p2", missing = "breaching",    stat = "Minimum", cmp = "LessThanThreshold" }
    memory-usage   = { metric = "DatabaseMemoryUsagePercentage",         threshold = 85,       tier = "p2", missing = "breaching",    stat = "Average", cmp = "GreaterThanThreshold" }
    swap           = { metric = "SwapUsage",                            threshold = 52428800, tier = "p2", missing = "breaching",    stat = "Average", cmp = "GreaterThanThreshold" }
    repl-lag       = { metric = "ReplicationLag",                       threshold = 5,        tier = "p2", missing = "breaching",    stat = "Average", cmp = "GreaterThanThreshold" }
    net-bw-out     = { metric = "NetworkBandwidthOutAllowanceExceeded",  threshold = 0,       tier = "p2", missing = "notBreaching", stat = "Sum",     cmp = "GreaterThanThreshold" }
    conntrack      = { metric = "NetworkConntrackAllowanceExceeded",     threshold = 0,       tier = "p2", missing = "notBreaching", stat = "Sum",     cmp = "GreaterThanThreshold" }
    fragmentation  = { metric = "MemoryFragmentationRatio",              threshold = 1.5,     tier = "p2", missing = "breaching",    stat = "Average", cmp = "GreaterThanThreshold" }
  }

  redis_matrix = {
    for pair in setproduct(local.redis_nodes, keys(local.redis_alarms)) :
    "${pair[0]}-${pair[1]}" => { node = pair[0], key = pair[1] }
  }
}

module "redis_alarms" {
  source   = "./modules/cw-alarm"
  for_each = local.redis_matrix

  name         = "prod-core-redis-${each.value.node}-${each.value.key}"
  namespace    = "AWS/ElastiCache"
  metric_name  = local.redis_alarms[each.value.key].metric
  dimensions   = { CacheClusterId = each.value.node }
  statistic    = local.redis_alarms[each.value.key].stat
  threshold    = local.redis_alarms[each.value.key].threshold
  comparison   = local.redis_alarms[each.value.key].cmp
  missing_data = local.redis_alarms[each.value.key].missing
  tier         = local.redis_alarms[each.value.key].tier
  env          = "prod"
  layer        = "l2"
  topic_arns   = local.topic_arns
  runbook_url  = "${local.runbook_base}/redis-${each.value.key}"
  tags         = merge(local.common_tags, { service = "core" })
}
```

**노드 N개 × 11항목 = 11N개 알람이 이 블록 하나다.**

## 9.12 사용 예 — VPN (Math 모듈)

```hcl
variable "vpn_connections" {
  type = map(object({
    vpn_id     = string
    tunnel_ips = list(string)
  }))
  # {기관A}      = { vpn_id = "vpn-xxxx", tunnel_ips = ["a.b.c.d", "e.f.g.h"] }
  # {기관B}         = { ... }
  # {기관C} = { ... }
}

module "vpn_both_down" {
  source   = "./modules/cw-alarm-math"
  for_each = var.vpn_connections

  name       = "prod-claim-vpn-${each.key}-tunnel-down"
  expression = "m0 + m1"
  metrics = [
    for ip in each.value.tunnel_ips : {
      namespace   = "AWS/VPN"
      metric_name = "TunnelState"
      dimensions  = { VpnId = each.value.vpn_id, TunnelIpAddress = ip }
      stat        = "Minimum"
      period      = 60
    }
  ]
  threshold    = 0
  comparison   = "LessThanOrEqualToThreshold"
  eval_periods = 3
  datapoints   = 3
  missing_data = "breaching"
  tier         = "p1"
  env          = "prod"
  layer        = "l1"
  topic_arns   = local.topic_arns
  runbook_url  = "${local.runbook_base}/vpn-down"
  tags         = merge(local.common_tags, { service = "claim" })
}

module "vpn_redundancy_lost" {
  source   = "./modules/cw-alarm-math"
  for_each = var.vpn_connections

  name         = "prod-claim-vpn-${each.key}-redundancy-lost"
  expression   = "m0 + m1"
  metrics      = module.vpn_both_down[each.key] != null ? [] : []   # 동일 metrics 블록 재사용
  threshold    = 1
  comparison   = "LessThanOrEqualToThreshold"
  eval_periods = 5
  datapoints   = 3
  missing_data = "breaching"
  tier         = "p2"
  env          = "prod"
  layer        = "l1"
  topic_arns   = local.topic_arns
  runbook_url  = "${local.runbook_base}/vpn-redundancy"
  tags         = merge(local.common_tags, { service = "claim" })
}
```

> `metrics` 블록은 두 모듈 호출에서 동일하므로 `locals`로 추출해 공유한다. (위 코드는 개념 표현이며, 실제로는 `local.vpn_metrics[each.key]` 형태로 정리한다.)

## 9.13 us-east-1 알람 — 모듈에 provider 넘기기 ⚠️ v1 누락

```hcl
# alarms-use1.tf
module "acm_expiry_critical" {
  source    = "./modules/cw-alarm"
  providers = { aws = aws.use1 }        # ← 이 문법이 v1에 없었다
  for_each  = toset(var.cloudfront_cert_arns)

  name         = "prod-edge-acm-${substr(sha1(each.key), 0, 8)}-expiry-critical"
  namespace    = "AWS/CertificateManager"
  metric_name  = "DaysToExpiry"
  dimensions   = { CertificateArn = each.key }
  statistic    = "Minimum"
  period       = 86400
  threshold    = 3
  comparison   = "LessThanThreshold"
  eval_periods = 1
  datapoints   = 1
  missing_data = "breaching"
  tier         = "p1"
  env          = "prod"
  layer        = "l4"
  paged        = true                   # us-east-1 은 복합 알람 없이 직접 발화
  topic_arns   = local.topic_arns_use1  # ← us-east-1 토픽
  runbook_url  = "${local.runbook_base}/acm-expiry"
  tags         = local.common_tags
}
```

⚠️ **모듈에 `providers`를 넘기지 않으면 기본 provider(ap-northeast-2)로 만들어진다.** 그러면 알람은 생성되지만 메트릭이 없어서 영구히 `INSUFFICIENT_DATA`가 되고, `treat_missing_data: breaching` 때문에 계속 ALARM 상태가 된다.

## 9.14 함정

| # | 함정 | 대응 |
| --- | --- | --- |
| 1 | State 버킷은 Terraform으로 만들 수 없다 | 9.4의 CLI로 수동 생성. 예외로 문서에 기록 |
| 2 | **Datadog API 키가 state에 평문 저장** | `sensitive = true`나 SSM `data`로도 막히지 않는다(Terraform의 알려진 한계). **구독만 수동 생성**으로 회피 |
| 3 | 콘솔로 만든 알람과 이름 충돌 | `terraform import` 권장 (히스토리 유지) |
| 4 | 콘솔에서 수정하면 다음 apply가 원복 | **버그가 아니라 기능.** 팀 규칙: "알람은 콘솔에서 수정하지 않는다. 급하면 `disable-alarm-actions` 후 PR" |
| 5 | `terraform destroy` | **이 디렉토리에서 절대 실행 금지.** 알람이 전부 사라지고, 그 사실을 알려줄 알람도 함께 사라진다 |
| 6 | **모듈에 provider 미지정** | us-east-1 알람이 조용히 잘못된 리전에 생성됨 (9.13) |
| 7 | 복합 알람이 참조하는 알람 이름 오타 | plan·apply 모두 통과하고 **억제만 조용히 안 된다.** 모듈 output 참조로 회피 (13.2) |

```bash
# 함정 3 — 기존 알람 확인
aws cloudwatch describe-alarms --query "MetricAlarms[].AlarmName" --output table

# import 예시
terraform import \
  'module.redis_alarms["prod-redis-001-evictions"].aws_cloudwatch_metric_alarm.this' \
  <기존-알람-이름>
```

---

# 10. Datadog 측 계층

## 10.1 두 종류의 Datadog 모니터

| 종류 | 지연 | 용도 | 티어 |
| --- | --- | --- | --- |
| **앱 메트릭** (DogStatsD 직접 수집) | 1~2분 | 6.9 애플리케이션 계층 (PG-09, PG-10) | **P1 가능** |
| **AWS 메트릭** (인테그레이션 폴링) | 10~20분 | 추세·이상탐지 (#35f, #44g) | P2 이하 |

## 10.2 AWS 인테그레이션 네임스페이스 활성화

메트릭 목록 기준 현재 활성 네임스페이스가 제한적이다.

| 활성 | 비활성 |
| --- | --- |
| `AWS/ApplicationELB` | `AWS/VPN` |
| `AWS/RDS` | `AWS/NATGateway` |
| `AWS/ElastiCache` | `AWS/Lambda` |
| `AWS/ECS` | `AWS/SQS` |
| `AWS/S3` | `AWS/AutoScaling` |
| `AWS/SecretsManager` | `AWS/CertificateManager` |
| `AWS/EC2` (`host_ok`만) | **`AWS/SNS`** |
| | **`AWS/Events`** |

P1 감지는 CloudWatch가 담당하므로 치명적이지는 않다. 하지만 다음이 불가능하다.

- 8.2 #51a `NumberOfNotificationsFailed` 를 Datadog에서 보기 (`AWS/SNS`)
- 8.2 #51c/#51d EventBridge 실패 감시 (`AWS/Events`)
- VPN / Lambda / SQS의 추세·이상탐지

**조치**: Datadog → Integrations → AWS → 해당 계정 → Metric Collection에서 다음 활성화.

```
AWS/SNS            ← 8.2 #51a
AWS/Events         ← 8.2 #51c/#51d
AWS/VPN
AWS/NATGateway
AWS/Lambda
AWS/SQS
AWS/AutoScaling
AWS/CertificateManager
AWS/EC2
```

⚠️ **인테그레이션 메트릭은 커스텀 메트릭이 아니므로 무과금이다.** 비용 고려 없이 활성화해도 된다.

## 10.3 Datadog 담당 항목 정리

| 항목 | 지연 | 티어 |
| --- | --- | --- |
| 6.9 #61~63 기관 연동 (PG-09) | 1~2분 | **P1** |
| 6.9 #65~66 리소스 포화 (PG-10) | 1~2분 | **P1** |
| 6.9 #64, #67 계열 | 1~2분 | P2 |
| 8.3 (a) 하트비트 no-data (PG-12) | 45분 | **P1** |
| 8.1 ② Event Monitor (필요 시) | 1분 | **P1** |
| 6.6 #35f RDS `queries` 급락 | 10~20분 | P2 |
| 6.7 #44g `CacheHitRate` 급락 | 10~20분 | P2 |
| 전 모니터 `notify_no_data: true` | — | P2 |

**초기에는 UI로 생성하고, 안정화 후 `datadog` provider로 IaC 전환한다** (9.2 참조).

## 10.4 앱 계층 경로는 SNS를 경유하지 않는다 ⚠️

**애플리케이션 메트릭은 앱 → DogStatsD → Datadog Agent → Datadog 으로 직접 들어온다.** CloudWatch도, SNS도, EventBridge도 거치지 않는다.

```
[AWS 경로]
CloudWatch/EventBridge → SNS → Datadog intake → Event → Monitor → 전화
                          ↑
                    8.2/8.3 이 감시하는 구간

[앱 경로]
앱 → DogStatsD(UDP) → DD Agent → Datadog 메트릭 → Monitor → 전화
      ↑
   8.2/8.3 이 감시하지 않는 구간
```

**결과: PG-09·PG-10은 8장 파이프라인 감시의 보호를 받지 못한다.** 실패 모드가 다르므로 별도 감시가 필요하다.

| 실패 모드 | AWS 경로 | 앱 경로 | 감지 수단 |
| --- | --- | --- | --- |
| 메트릭/이벤트 발행 중단 | #51h 하트비트 | **앱이 죽거나 계측이 빠짐** | 전 모니터 `notify_no_data: true` (#51f) |
| 전송 유실 | #51a SNS 배달 실패, #51b DLQ | **DogStatsD UDP 유실** | **#68** (6.9.3) |
| 에이전트 중단 | 해당 없음 | **DD Agent 컨테이너 죽음** | `datadog.agent.running` no-data |
| Datadog 자체 장애 | 감지 불가 | 감지 불가 | 공통 리스크. 수용 |

### 앱 경로 전용 감시 3종 (전부 무과금)

```python
# (1) DogStatsD 유실 — #68
sum(last_10m):sum:datadog.dogstatsd.client.packets_dropped{*} by {host}.as_count() > 0

# (2) Datadog Agent 중단
avg(last_5m):avg:datadog.agent.running{*} by {host} < 1
# notify_no_data: true, no_data_timeframe: 10

# (3) 앱 메트릭 전면 침묵 (앱 죽음 / 계측 제거 / 배포 사고)
sum(last_15m):sum:auth.dozen.count{*}.as_count() < 1
# notify_no_data: true, no_data_timeframe: 20
# → 6.9 #62 와 유사하지만 기관 단위가 아니라 서비스 전체 단위
```

> **(3)이 필요한 이유**: 누군가 리팩터링하면서 `auth.dozen.count` 계측을 빼면, PG-09의 모든 모니터가 **조용히 무력화된다.** 값이 0이 아니라 데이터 자체가 없어지므로 임계값 기반 모니터는 발화하지 않는다. `notify_no_data`만이 이걸 잡는다.
>
> 커스텀 메트릭 148개 중 145개가 방치된 상태(6.9.2)라는 건, **계측이 사라져도 아무도 모르는 환경**이라는 뜻이다.

### 지연 요약

| 경로 | 지연 | P1 가능 |
| --- | --- | --- |
| CloudWatch 알람 → SNS → Datadog | 1~2분 | ✅ |
| 앱 → DogStatsD → Datadog | **1~2분** | ✅ |
| AWS 인테그레이션 폴링 → Datadog | 10~20분 | ❌ |

**앞 두 경로는 지연이 같다.** 앱 계층을 P1에 쓸 수 있는 근거이며, 3.2 표의 3번 행이 v1에서 누락되어 6.9 전체가 빠졌던 원인이다.

---

# 11. 비용

## 11.1 알람 개수 산정

> **감지 항목 ≠ 알람 개수.** CloudWatch 알람은 차원(dimension) 조합마다 1개다.

| 대상 | 항목 수 | 리소스 수 | 알람 수 |
| --- | --- | --- | --- |
| VPN (터널 합산 + 이중화) | 2 | 3세트 | 6 (Math) |
| ALB + 타깃그룹 | 5 + 3 | ALB 2 / TG 6 | 28 |
| RDS | 11 | 인스턴스 3 | 33 |
| ElastiCache | 11 | 노드 N (**Q7**) | 11N |
| ECS 서비스 | 1 | 서비스 15 | 15 (Math) |
| **Lambda** | 감축 (6.4) | 동기 4 / DLQ 6 / 스트림 2 | **21** |
| NAT / SQS / ACM / 기타 | — | — | 20 |
| 메타 (8.2) | 5 | — | 8 |
| us-east-1 | 2 | — | 4 |
| **개별 알람 소계** (N=3 가정) | | | **약 168** |
| **복합 알람** | 페이지 12개 + 억제 계층 5개 | | **17** |

**v1 대비 감소 요인**: Lambda 120 → 21 (**-99개**)

## 11.2 비용

| 항목 | 단가 | 월 실비 |
| --- | --- | --- |
| CloudWatch 표준 알람 (약 145개) | 개당 $0.10 | $14.50 |
| CloudWatch Math 알람 (약 23개 × 평균 2메트릭) | 메트릭 수 × $0.10 | $4.60 |
| Composite 알람 (17개) | **개당** $0.50 | $8.50 |
| KMS CMK × 2 (리전별) | 키당 $1.00 + 요청 요금 | $2 |
| EventBridge (AWS 서비스 이벤트) | 무료 | $0 |
| EventBridge Scheduler (하트비트, 월 ~2,900회) | 100만 호출 무료 | $0 |
| SNS | 100만 요청 무료 | $0 |
| AWS Chatbot | 무료 | $0 |
| SQS (DLQ) | 100만 요청 무료 | $0 |
| **Datadog 모니터 (6.9 앱 계층)** | 이미 수집 중인 메트릭 | **$0** |
| **AWS 합계** | | **약 $30** |

**v1 대비 정정 사항**

| | v1 원안 | v1 리뷰 | v2 |
| --- | --- | --- | --- |
| 알람 무료 티어 | 10개 무료 가정 | 신규 계정 12개월 한정 지적 | 무료 티어 미가정 |
| 알람 개수 | 54개 | 250~300개 | **약 168개** (Lambda 감축) |
| Math 알람 | 개당 $0.10 | 식의 메트릭 수만큼 | 반영 |
| Composite | 월 $0.50 | 개당 $0.50 | 17개 = $8.50 |
| KMS | 1개 | — | **2개** (리전별) |
| **합계** | 약 $3 | $30~40 | **약 $30** |

## 11.3 별도 확인 필요

| 항목 | 확인 방법 |
| --- | --- |
| Datadog On-Call 2시트 | Plan and Usage → On-Call SKU 단가 |
| **전화 발신(voice) 사용량 초과 요금** | 시트 포함 한도 확인. 페이지가 많으면 초과 가능 (**Q8**) |
| 기존 Datadog 폴링 비용 (GMD-Metrics) | Cost Explorer → `CW:GMD-Metrics` |
| Container Insights (6.2 #1 필요 시) | 켜면 컨테이너 수 기반 과금 발생 (**Q3**) |

---

# 12. 도입 순서

## 12.1 1주차 (7/31 ~ 8/5) — 진행 중

- [x] Cost Explorer에서 GMD-Metrics 현재 지출 확인
- [x] SSM Incident Manager 기존 가입 여부 확인
- [x] Datadog Plan and Usage에서 On-Call SKU 사용 가능 여부 확인
- [x] Slack 워크스페이스 관리자에게 Chatbot OAuth 승인 요청
- [ ] **State 버킷 수동 생성** (9.4) — 10분
- [ ] **기존 알람 목록 확인** — 이름 충돌 여부 (9.14 #3) — 5분
- [ ] **`providers.tf` + `locals.tf` + `kms.tf`(2개) + `sns.tf`(2리전) apply** — 40분
- [ ] **Datadog 구독 3개 수동 생성** (p1, p3-하트비트, p1-use1) — 15분
- [ ] 🔴 **P1 경로 4단계 검증** (8.1) — 30분
      → ② 실패 시 Datadog Event Monitor 생성
- [ ] **1차 런북 8개 작성** (부록 C) — 1시간
      → 알람보다 먼저. `runbook_url` precondition이 이걸 강제한다
- [ ] `modules/cw-alarm/` + `modules/cw-alarm-math/` 작성 — 1.5시간
- [ ] **1차 대상 알람 apply** (6.12) — 1~2시간
- [ ] ⭐ **6.9 앱 계층 모니터 5개 UI 생성** (PG-09, PG-10) — 1시간, 비용 0
- [ ] ⭐ **10.4 앱 경로 감시 3개** (DogStatsD 유실 / Agent 중단 / 앱 메트릭 침묵) — 20분, 비용 0
- [ ] `set-alarm-state`로 ALARM/OK 양방향 전달 재확인

> ⚠️ **순서가 중요하다**
>
> 1. **P1 경로 검증(8.1)이 알람 대량 생성보다 먼저.** 여기서 막히면 이후 작업이 무의미하다.
> 2. **런북 작성이 알람 생성보다 먼저.** v1은 런북을 3주차에 뒀는데, 그러면 1주차 알람의 `alarm_description` 링크가 2주 동안 404다. 새벽에 깬 사람이 404를 본다.

## 12.2 2주차 (8/6 ~ 8/12)

- [ ] Datadog AWS 인테그레이션 네임스페이스 활성화 (10.2)
- [ ] 8.2 파이프라인 감시 알람 8개 + PG-12
- [ ] Dead man's switch 구축 (8.3 a) — EventBridge Scheduler + Datadog no-data
- [ ] ECS ERROR 이벤트 룰 생성 후 슬랙으로 흘리기 (알림 없이 관찰만)
- [ ] Container Insights 확인 후 #1 알람 추가 (Q3)
- [ ] On-Call 팀 생성, **에스컬레이션 3단계 구성** (8.4)
- [ ] 첫 호출 훈련 실시
- [ ] 노이즈 실측 → P2 승격/강등 대상 결정 (태그 수정)

## 12.3 3주차

- [ ] Composite 억제 계층 구축 (13.2)
- [ ] 배포 중 억제 + 자동 해제 안전장치 (13.3)
- [ ] 보안 항목 전체를 P3로 걸어 발생량 측정 시작
- [ ] 나머지 런북 작성 (P2 항목)
- [ ] **월 1회 호출 훈련 캘린더 반복 등록** (8.3 b)
- [ ] 오탐 폭주 롤백 절차 팀 공유 (8.5)

## 12.4 4주차 이후

- [ ] P3 발생량 실측 결과로 승격 판단
- [ ] P2 확장 (6장 잔여 항목)
- [ ] `datadog` provider로 Datadog 모니터 IaC 전환
- [ ] 커스텀 메트릭 정리 (6.9.4 — 별도 과제)

---

# 13. 억제 계층 설계

## 13.1 왜 필요한가 — RDS 페일오버 1건의 파급

```
RDS failover 발생
├─ #31  RDS 이벤트 구독 failover
├─ #30  DatabaseConnections 급변
├─ #35e EngineUptime 급락
├─ #33  AuroraReplicaLag
├─ #35  DiskQueueDepth
├─ #26b 앱 5XX 급증 (커넥션 상실)
├─ #25  HealthyHostCount 0 (헬스체크가 DB 검사)
├─ #1   running < desired (태스크 재시작)
├─ #39  Redis RejectedConnections (폴백 부하)
├─ #65  hikaricp.connections.pending 급증
├─ #36  SQS DLQ 유입
└─ #27  TargetResponseTime p95
```

3.4의 페이지 단위 정의로 **P1 알람이 개별 발화하지 않으므로 전화는 최대 6통**(PG-03, 04, 05, 06, 07, 08, 10)이다. 억제 계층으로 이를 **1통**으로 만든다.

## 13.2 억제 계층 — 모듈 output 참조 방식

```
Layer 0  aws.health (리전 장애)      ← 최상위. 모든 것을 억제
Layer 1  VPN / NAT / 네트워크
Layer 2  RDS / ElastiCache
Layer 3  ECS / ASG
Layer 4  ALB / SQS / Lambda          ← 최하위. 대부분 결과지 원인이 아님
APP      기관 연동 / 리소스 포화      ← Layer 2 에 종속
```

⚠️ **v1은 알람 이름을 문자열로 나열했다.** 오타가 나면 plan·apply 모두 통과하고 **억제만 조용히 안 된다.** 모듈 output을 참조한다.

```hcl
# composite.tf
locals {
  # 모듈 output 참조 — 오타가 불가능해진다
  l2_rds_alarms = [
    module.rds_alarms["prod-db-01-connections-critical"].alarm_name,
    module.rds_alarms["prod-db-01-local-storage"].alarm_name,
    module.rds_alarms["prod-db-01-engine-restart"].alarm_name,
  ]

  l2_redis_alarms = [
    for k, m in module.redis_alarms : m.alarm_name
    if endswith(k, "-rejected-conn") || endswith(k, "-engine-cpu-crit")
  ]

  l4_app_alarms = [
    module.alb_alarms["prod-claim-alb-elb-5xx"].alarm_name,
    module.alb_math_alarms["prod-claim-alb-target-5xx-rate"].alarm_name,
  ]
}

# ── PG-03 ────────────────────────────────────────
resource "aws_cloudwatch_composite_alarm" "l2_rds_incident" {
  alarm_name        = "composite-l2-rds-incident"
  alarm_description = "runbook: ${local.runbook_base}/rds-incident"
  alarm_rule        = join(" OR ", [for a in local.l2_rds_alarms : "ALARM(\"${a}\")"])

  alarm_actions = [local.topic_arns["p1"]]
  ok_actions    = [local.topic_arns["p2"]]   # 7.8 — 복구는 p2 로

  actions_suppressor                  = aws_cloudwatch_composite_alarm.l0_region.alarm_name
  actions_suppressor_wait_period      = 120
  actions_suppressor_extension_period = 300

  tags = merge(local.common_tags, { tier = "p1", layer = "l2", page = "PG-03" })
}

# ── PG-07 (Layer 4 — 상위 레이어에 억제됨) ───────
resource "aws_cloudwatch_composite_alarm" "l4_app_5xx" {
  alarm_name        = "composite-l4-app-5xx"
  alarm_description = "runbook: ${local.runbook_base}/app-5xx"
  alarm_rule        = join(" OR ", [for a in local.l4_app_alarms : "ALARM(\"${a}\")"])

  alarm_actions = [local.topic_arns["p1"]]
  ok_actions    = [local.topic_arns["p2"]]

  # 상위 레이어 중 하나라도 ALARM 이면 억제
  actions_suppressor                  = aws_cloudwatch_composite_alarm.upstream_any.alarm_name
  actions_suppressor_wait_period      = 120
  actions_suppressor_extension_period = 300

  tags = merge(local.common_tags, { tier = "p1", layer = "l4", page = "PG-07" })
}

# 상위 레이어 집합 (억제용 — 액션 없음)
resource "aws_cloudwatch_composite_alarm" "upstream_any" {
  alarm_name = "composite-suppressor-upstream"
  alarm_rule = join(" OR ", [
    "ALARM(\"${aws_cloudwatch_composite_alarm.l0_region.alarm_name}\")",
    "ALARM(\"${aws_cloudwatch_composite_alarm.l1_vpn_down.alarm_name}\")",
    "ALARM(\"${aws_cloudwatch_composite_alarm.l1_nat_exhaustion.alarm_name}\")",
    "ALARM(\"${aws_cloudwatch_composite_alarm.l2_rds_incident.alarm_name}\")",
    "ALARM(\"${aws_cloudwatch_composite_alarm.l2_redis_incident.alarm_name}\")",
  ])
  # alarm_actions 없음 — 억제 판단 전용
  tags = merge(local.common_tags, { purpose = "suppressor" })
}
```

**결과**: RDS 페일오버 시 전화 1통(PG-03). 하위 레이어는 ALARM 상태로 기록되지만 액션이 억제된다. 원인이 DB가 아니었다면 `wait_period` 120초 후 하위 레이어가 정상 발화한다.

⚠️ **`alarm_rule`에는 길이 제한이 있다.** 레이어별로 수십 개를 나열하는 방식은 확장되지 않는다. 개별 알람을 직접 나열하지 말고, **레이어별 중간 복합 알람을 만들어 2단 계층**으로 구성한다(위 `upstream_any` 패턴).

## 13.3 배포 중 억제 + 자동 해제 ⚠️ v1 미해결 항목

배포 중에는 태스크가 뜨고 지므로 #1, #8, #27이 정상적으로 튄다. 억제 알람을 CI에서 토글한다.

```bash
# 배포 시작
aws cloudwatch set-alarm-state --alarm-name suppressor-deploying \
  --state-value ALARM --state-reason "deploy in progress: $GITHUB_RUN_ID"

# 배포 완료
aws cloudwatch set-alarm-state --alarm-name suppressor-deploying \
  --state-value OK --state-reason "deploy finished"
```

> ⚠️ **v1의 미해결 문제**: 배포가 실패해서 CI가 중단되면 억제가 풀리지 않는다. → 그날 밤 진짜 장애가 억제된다.
>
> `actions_suppressor_extension_period`는 억제를 **연장**하는 값이며, CloudWatch에 "억제 자동 만료" 기능은 없다.

**해법 — (a)와 (b)를 둘 다 넣는다.**

### (a) CI 정리 단계 (정상 경로)

```yaml
# .github/workflows/deploy.yml
jobs:
  deploy:
    steps:
      - name: Suppress alarms
        run: aws cloudwatch set-alarm-state --alarm-name suppressor-deploying
             --state-value ALARM --state-reason "deploy ${{ github.run_id }}"

      - name: Deploy
        run: ./deploy.sh

      - name: Release suppression
        if: always()          # ← 실패·취소해도 반드시 실행
        run: aws cloudwatch set-alarm-state --alarm-name suppressor-deploying
             --state-value OK --state-reason "deploy finished or failed"
```

### (b) 시간 기반 자동 해제 (안전망)

(a)가 실패하는 경우 — CI 런너가 강제 종료되거나, `always()` 단계 자체가 권한 오류로 실패 — 를 대비한다.

```
1. 배포 시작 시 커스텀 메트릭 발행
   aws cloudwatch put-metric-data --namespace Deploy \
     --metric-name InProgress --value 1

2. suppressor-deploying 을 이 메트릭 기반 알람으로 정의
   Deploy/InProgress, Sum, 300s, >= 1, treat_missing_data = notBreaching

3. 배포 시작 후 메트릭 발행이 멈추면 → 5분 뒤 자동 OK → 억제 자동 해제
```

**즉 억제는 "메트릭이 계속 들어오는 동안만" 유지된다.** CI가 죽으면 발행이 멈추고 5분 후 자동 해제된다. 긴 배포는 파이프라인 중간중간 메트릭을 재발행하면 된다.

```hcl
module "suppressor_deploying" {
  source = "./modules/cw-alarm"

  name         = "suppressor-deploying"
  namespace    = "Deploy"
  metric_name  = "InProgress"
  dimensions   = {}
  statistic    = "Sum"
  period       = 300
  threshold    = 1
  comparison   = "GreaterThanOrEqualToThreshold"
  eval_periods = 1
  datapoints   = 1
  missing_data = "notBreaching"      # ← 발행이 멈추면 OK 로
  tier         = "p3"                # 액션 없음. 억제 판단 전용
  env          = "prod"
  topic_arns   = local.topic_arns
  runbook_url  = "${local.runbook_base}/deploy-suppression"
  tags         = merge(local.common_tags, { purpose = "suppressor" })
}
```

---

# 14. 미해결 / 확인 필요 항목

| # | 항목 | 영향 | 현재 기본값 | 담당 |
| --- | --- | --- | --- | --- |
| **Q1** | `oncall_team` 파라미터가 실제로 페이지를 발생시키는가 | 아니라면 Datadog Event Monitor 필요 | Event Monitor를 만드는 것으로 가정 | 8.1 ② |
| **Q2** | Redis `maxmemory-policy` 값 | #40 Evictions 티어 | **P2** (`allkeys-lru` 가정) | 6.7 |
| **Q3** | Container Insights 활성화 여부 | 6.2 #1 구현 방법 | 비활성 가정 → 이벤트 기반 우선 | 12.2 |
| **Q4** | Lambda 함수 중 **동기 호출** 개수 | 알람 21개 산정 근거 | 4개 가정 | 6.4 |
| **Q5** | RDS `max_connections` 실제 값 | #30 임계값 | 인스턴스 클래스별 조회 필요 | 6.6 |
| **Q6** | `AWS/Usage` 로 감시 가능한 쿼터 목록 | #14, #53 실현 가능성 | 불가 시 P3 + 주간 수동 확인 | 6.11 |
| **Q7** | ElastiCache 노드 수 | 알람 11N개 산정 | 3개 가정 | 11.1 |
| **Q8** | Datadog On-Call 전화 발신 한도/초과 요금 | 비용 | — | 11.3 |
| **Q9** | 외부 기관 3곳({기관A}/{기관B}/{기관C}) **야간 연락 채널** | **PG-01의 P1 자격** | 있다고 가정. 없으면 **P2로 강등** | 3.6 / 부록 C-1 |
| **Q10** | OK 이벤트가 페이지를 자동 종료하는가 | 7.8 정책 | 자동 종료 안 됨으로 가정 (`ok_actions` = p2) | 8.1 ④ |

> ⚠️ **Q9는 기술 문제가 아니라 운영·계약 문제다.**
>
> 3.6 원칙에 따라 "할 수 있는 일이 없으면 P1이 아니다." VPN 터널 양쪽이 내려갔고 원인이 상대 기관 측이면, 온콜은 새벽에 깨서 확인하고 다시 잘 수밖에 없다. 그게 3번 반복되면 그 알럿을 무시한다.
>
> **야간 연락 채널이 없으면 PG-01은 P2로 내려야 한다.** 대신 부록 C-1에 "CS 공지"와 "재시도 큐 정지" 같은 우리가 할 수 있는 일이 있으면 P1을 유지할 수 있다.

---

# 15. 변경 이력

## v1 → v2 (패널 리뷰 반영)

### 오류 정정

| # | 변경 | 이유 |
| --- | --- | --- |
| F1 | 4.1, 7.1에서 **`SNS → CloudWatch Logs` 제거** | SNS는 CloudWatch Logs를 구독할 수 없다. 지원 프로토콜: HTTP/HTTPS, Email, SMS, SQS, Lambda, 플랫폼 엔드포인트, Firehose |
| F2 | 9.6 **KMS 키를 리전별 2개**로, 9.7 **us-east-1 SNS 추가**, 9.13 **모듈 `providers` 문법 추가** | KMS는 리전 리소스. v1은 us-east-1 세트가 apply되지 않았다 |
| F3 | 8.5 롤백 3번을 **SNS 필터 정책**으로 교체 | SNS에 구독 "비활성" 기능이 없다. 삭제하면 API 키 재입력이 필요하다 |

### 원칙 위반 시정

| # | 변경 | 이유 |
| --- | --- | --- |
| F4 | **P1을 "알람 개수" → "페이지 경로 수"로 재정의.** 5.2에 PG-01~13 명시 | v1은 P1 목표 8~10을 선언하고 6장에서 31개를 만들었다 (원안 25개보다 증가) |
| F5 | 3.4 신설 — **P1 개별 알람은 액션 없음.** 복합 알람만 발화 | 장애 1건에 전화 8통 방지 |
| F6 | 5.3 **P1 → P2 강등 11개** (ElastiCache 5개, ACM 2개, Lambda 1개 등) | 포화 경고(80~90%)와 실제 영향 발생을 구분 |
| F7 | 3.6 / D9 신설 — **런북 없는 P1은 만들지 않는다** | 전화를 받은 사람이 할 일이 없으면 P1 자격이 없다 |
| F8 | **런북 작성을 3주차 → 1주차로 이동.** 부록 C에 1차 8개 작성 | v1은 1주차 알람의 `alarm_description` 링크가 2주간 404였다 |
| F9 | 5.4 신설 — **환경별 티어 규칙** (stg는 P1 금지) + Terraform validation | `prod`만 예시로 두면 나중에 stg P1 알람이 생긴다 |

### 공백 보완

| # | 변경 | 이유 |
| --- | --- | --- |
| F10 | **6.9 애플리케이션 계층 신설** (#61~67e, PG-09/PG-10) | v1 1,351줄 전부가 AWS 리소스였다. 2장이 문제로 든 "외부 기관 연동 단절"의 실제 원인 대부분(API 인증 만료, 응답 포맷 변경, 기관 점검)을 감지하지 못했다. **비용 0** |
| F11 | 3.2 표에 **"앱 메트릭(DogStatsD) 1~2분" 행 추가** | "Datadog = 느림"으로 뭉뚱그린 것이 F10 공백의 원인이었다 |
| F12 | 6.9.2에 **커스텀 메트릭 148개 중 3개만 사용 중** 사실 기록 | 145개가 방치. 지울 것과 알럿 걸 것을 구분해야 한다 |
| F13 | 2장 배경 표에 **기관 API 인증 실패 / 커넥션 풀 고갈** 2행 추가 | 문서가 감지하려는 문제와 감지 수단의 정합성 확보 |
| F14 | 8.3에 **us-east-1 세트 ↔ 하트비트 보완 관계** 명시 | 하트비트는 "경로가 죽었다", `aws.health`는 "무엇 때문인지"를 알려준다 |
| F15 | 13.3에 **배포 억제 자동 해제 (a)+(b)** 해법 | v1은 "안전장치가 필요하다"로 끝나 있었다 |
| F29 | **10.4 신설 — 앱 계층 경로는 SNS를 경유하지 않음** + 전용 감시 3종 | 앱 메트릭은 DogStatsD로 Datadog에 직접 들어오므로 8.2/8.3 파이프라인 감시가 커버하지 않는다. 실패 모드가 다르다 |
| F30 | 6.9.3 **#68 DogStatsD 유실 감시** 추가 | UDP는 유실되면 조용히 사라진다. PG-09·PG-10의 침묵이 "문제 없음"인지 "메트릭 유실"인지 구분할 수 없다. 6.9 전체가 여기 의존한다 |

### 확장성·구조

| # | 변경 | 이유 |
| --- | --- | --- |
| F16 | **`modules/cw-alarm-math/` 신설** | Math 알람 6종 중 5종이 P1인데 모듈 밖 raw 리소스였다. 모듈이 강제하던 규칙(missing_data, ok_actions, tags, runbook)이 P1에만 적용되지 않았다 |
| F17 | 모듈에 **`outputs.tf` 추가**, 13.2를 **참조 방식**으로 변경 | 알람 이름 오타 시 plan·apply 통과하고 억제만 조용히 안 된다 |
| F18 | 9.8 **`locals.tf` 신설** (`topic_arns`, `runbook_base`, `common_tags`) | v1은 파일마다 반복했다 |
| F19 | **6.4 Lambda 알람 120개 → 21개** (동기/비동기 함수 구분) | 전체 알람의 40%인데 가치가 가장 낮았다. 비동기 함수는 DLQ 알람 하나가 더 정확하다 |
| F20 | 13.2에 **`alarm_rule` 길이 제한** 및 2단 계층 패턴 명시 | 수십 개 나열은 확장되지 않는다 |
| F21 | 9.14에 함정 6·7(**모듈 provider 미지정**, **복합 알람 이름 오타**) 추가 | 둘 다 조용히 실패한다 |

### 세부 조정

| # | 변경 | 이유 |
| --- | --- | --- |
| F22 | 6.5 **#29 ACM을 4단계로 분할** (45일 P3 / 14일 P2 / 갱신실패 P2 / 3일 P1) | v1 21일 단일 P2는 갱신 실패를 늦게 감지하고 임박을 놓친다 |
| F23 | 6.7 **#41b `EngineCPU > 99` 신설** | 90%는 경고, 99% 지속이 실제 포화 |
| F24 | 6.11 **`AWS/Usage` 실현 가능성 경고** 추가 (Q6) | v1이 낙관적으로 서술했다 |
| F25 | 8.3에 **EventBridge Scheduler 단일 장애점** 및 오탐 판단 절차 (부록 C-12) | 하트비트 알럿 수신 시 과잉 대응 방지 |
| F26 | 8.4 에스컬레이션 3단계 유지 + 강조 | 2시트 모두 부재 시 페이지가 갈 곳이 없다 |
| F27 | 11장 **비용 $30~40 → 약 $30** 재산정 | Lambda 감축(-99개) 반영, KMS 2개 반영 |
| F28 | 14장 **Q1~Q10 + 각 항목의 현재 기본값** 명시 | 미확인 항목이 진행을 막지 않도록 보수적 기본값 설정 |

## v0(원안) → v1

| # | 변경 |
| --- | --- |
| C1 | P1 25개 → 목표 축소 |
| C2 | `treat_missing_data` 메트릭 성격별 분기 |
| C3 | 티어를 알람 이름 → 태그 |
| C4 | ElastiCache 섹션 신설 |
| C5 | Terraform 도입 |
| C6 | Datadog 구독 수동 생성 |
| C7 | 비용 $3 → $30~40 |
| C8 | P1 경로 4단계 검증 절차 |
| C9 | 해제(resolve) 경로 정의 |
| C10 | Dead man's switch |
| C11 | 에스컬레이션 3단계 |
| C12 | EventBridge 실패 감시 |
| C13 | 오탐 폭주 롤백 절차 |
| C14 | ELB 5xx / 앱 5xx 분리 |
| C15 | ACM 3단 분할 |
| C16 | `aws.health` 3분할 |
| C17 | Fargate Spot 중단 P2 → P3 |
| C18 | 1차 구축 4개 → 6개 |
| C19 | RDS CPU/Memory/Swap/Uptime/Queries 추가 |
| C20 | Datadog 인테그레이션 네임스페이스 활성화 |

---

# 부록 A. 유용한 명령어

```bash
# 알람 전체 목록
aws cloudwatch describe-alarms \
  --query "MetricAlarms[].{Name:AlarmName,State:StateValue,Missing:TreatMissingData,Action:AlarmActions[0]}" \
  --output table

# 페이지 경로 (복합 알람 중 액션 있는 것) — 12~13개여야 한다
aws cloudwatch describe-alarms --alarm-types CompositeAlarm \
  --query "CompositeAlarms[?AlarmActions[0]!=null].AlarmName" --output table

# 3.4 위반 탐지 — 개별 알람에 p1 액션이 걸린 것. 결과가 비어 있어야 한다
aws cloudwatch describe-alarms --alarm-types MetricAlarm \
  --query "MetricAlarms[?contains(AlarmActions[0],'p1')].AlarmName"

# 티어별 알람 (태그 기반)
aws resourcegroupstaggingapi get-resources \
  --tag-filters Key=tier,Values=p1 \
  --resource-type-filters cloudwatch:alarm \
  --query "ResourceTagMappingList[].ResourceARN"

# 6.1 검증 — 카운터성 메트릭에 breaching 이 걸린 것 찾기
aws cloudwatch describe-alarms \
  --query "MetricAlarms[?TreatMissingData=='breaching'].{Name:AlarmName,Metric:MetricName}" \
  --output table

# D9 검증 — 런북 링크 없는 알람
aws cloudwatch describe-alarms \
  --query "MetricAlarms[?AlarmDescription==null].AlarmName"

# 7.6 검증 — P1 알람의 ok_actions 가 p1 인 것 (p2 여야 한다)
aws cloudwatch describe-alarms \
  --query "MetricAlarms[?contains(OkActions[0],'p1')].AlarmName"

# 전달 테스트 (8.1)
aws cloudwatch set-alarm-state --alarm-name delivery-test-dummy \
  --state-value ALARM --state-reason "delivery test"
aws cloudwatch set-alarm-state --alarm-name delivery-test-dummy \
  --state-value OK --state-reason "delivery test resolved"

# 8.5 롤백 — 알람 액션 비활성
aws cloudwatch disable-alarm-actions --alarm-names <name1> <name2>
aws cloudwatch enable-alarm-actions  --alarm-names <name1> <name2>

# 8.5 롤백 — SNS 구독 전면 차단 (구독 유지)
aws sns set-subscription-attributes --subscription-arn <arn> \
  --attribute-name FilterPolicy --attribute-value '{"__mute":["true"]}'
aws sns set-subscription-attributes --subscription-arn <arn> \
  --attribute-name FilterPolicy --attribute-value '{}'

# SNS 구독 확인 (API 키 마스킹)
aws sns list-subscriptions-by-topic --topic-arn <arn> \
  --query "Subscriptions[].[Protocol,Endpoint]" --output text \
  | sed 's/api_key=[^&]*/api_key=***/'

# Q5 — RDS max_connections 실제 값
aws rds describe-db-parameters --db-parameter-group-name <pg-name> \
  --query "Parameters[?ParameterName=='max_connections']"

# Q7 — ElastiCache 노드 목록
aws elasticache describe-cache-clusters --show-cache-node-info \
  --query "CacheClusters[].{Id:CacheClusterId,Nodes:NumCacheNodes,Type:CacheNodeType}"

# Q2 — Redis maxmemory-policy
aws elasticache describe-cache-parameters --cache-parameter-group-name <pg-name> \
  --query "Parameters[?ParameterName=='maxmemory-policy']"

# Q3 — Container Insights 활성화 여부
aws ecs describe-clusters --clusters <cluster> --include SETTINGS \
  --query "clusters[].settings"
```

# 부록 B. EventBridge 이벤트 패턴

```json
// GuardDuty High/Critical (severity 는 숫자)
{
  "source": ["aws.guardduty"],
  "detail-type": ["GuardDuty Finding"],
  "detail": { "severity": [{ "numeric": [">=", 7] }] }
}
```

```json
// 루트 계정 콘솔 로그인 — 반드시 us-east-1 에 생성
{
  "source": ["aws.signin"],
  "detail-type": ["AWS Console Sign In via CloudTrail"],
  "detail": { "userIdentity": { "type": ["Root"] } }
}
```

```json
// AWS Health — 진행 중 장애만 P1
{
  "source": ["aws.health"],
  "detail-type": ["AWS Health Event"],
  "detail": { "eventTypeCategory": ["issue"] }
}
```

```json
// ECS 컨테이너 OOM
{
  "source": ["aws.ecs"],
  "detail-type": ["ECS Task State Change"],
  "detail": {
    "lastStatus": ["STOPPED"],
    "stoppedReason": [{ "prefix": "OutOfMemoryError" }]
  }
}
```

```json
// ECS 배포 실패
{
  "source": ["aws.ecs"],
  "detail-type": ["ECS Deployment State Change"],
  "detail": { "eventName": ["SERVICE_DEPLOYMENT_FAILED"] }
}
```

```json
// ECS 서비스 액션 (배치 실패 등)
{
  "source": ["aws.ecs"],
  "detail-type": ["ECS Service Action"],
  "detail": {
    "eventName": [
      "SERVICE_TASK_START_IMPAIRED",
      "SERVICE_TASK_CONFIGURATION_FAILURE",
      "SERVICE_TASK_PLACEMENT_FAILURE",
      "SERVICE_DISCOVERY_INSTANCE_UNHEALTHY",
      "ECS_OPERATION_THROTTLED"
    ]
  }
}
```

```json
// CloudTrail 감사 로그 무력화 시도
{
  "source": ["aws.cloudtrail"],
  "detail-type": ["AWS API Call via CloudTrail"],
  "detail": {
    "eventSource": ["cloudtrail.amazonaws.com"],
    "eventName": ["DeleteTrail", "StopLogging", "PutEventSelectors"]
  }
}
```

```json
// KMS 키 무력화 시도
{
  "source": ["aws.kms"],
  "detail-type": ["AWS API Call via CloudTrail"],
  "detail": {
    "eventName": ["DisableKey", "ScheduleKeyDeletion"]
  }
}
```

---

# 부록 C. 런북 (1차 8개)

> **작성 원칙**: 새벽 3시에 깬 사람이 **5줄 안에 다음 행동**을 찾을 수 있어야 한다. 원인 분석은 아래로 미룬다.
>
> **각 런북에는 "우리가 할 수 있는 일"이 반드시 있어야 한다** (3.6 / D9).

## C-1. PG-01 — VPN 터널 단절

```
[즉시]
1. 어느 기관인가 확인 (알람 이름: {기관A} / {기관B} / {기관C})
2. AWS 콘솔 → Site-to-Site VPN → 해당 연결 → 터널 상태 확인
3. 최근 우리 측 변경 확인 (SG, 라우팅, Terraform 이력)
   → 변경 있었으면 롤백
   → 변경 없었으면 상대측 원인 가능성 높음

[우리가 할 수 있는 일]
4. 해당 기관 재시도 큐 정지 (무의미한 재시도로 큐 적재 방지)
   → <정지 방법 / 명령어>
5. CS 채널에 연동 중단 공지
   → <공지 템플릿 링크>
6. 외부 기관 야간 연락:
   · {기관A}      : <연락처>      ⚠️ Q9 — 미확인
   · {기관B}         : <연락처>      ⚠️ Q9 — 미확인
   · {기관C} : <연락처>      ⚠️ Q9 — 미확인

[에스컬레이션]
7. 30분 내 미해결 → <담당자>

⚠️ 6번 연락처가 확보되지 않으면 이 항목은 P2로 강등한다 (Q9).
```

## C-2. PG-02 — NAT 포트 고갈

```
[즉시]
1. 어느 NAT Gateway인가, 어느 AZ인가 확인
2. 증상: 아웃바운드 연결이 간헐적으로 타임아웃

[우리가 할 수 있는 일]
3. 원인 후보 확인 — 특정 대상으로의 커넥션 폭증
   CloudWatch → NAT GW → ActiveConnectionCount, PacketsOutToDestination
4. 앱에서 커넥션을 재사용하지 않는 코드/설정 의심
   → HTTP 클라이언트 keep-alive, 커넥션 풀 설정
5. 긴급 완화: NAT Gateway 추가 (AZ별로 분산)
   → 서브넷 라우팅 테이블 수정. 5~10분 소요
6. 원인이 특정 파드/서비스면 해당 서비스 스케일 다운

[사후]
7. 포트 고갈은 같은 5-tuple로 65,535개 한도. 대상별 분산 필요
```

## C-3. PG-03 — RDS 장애

```
[즉시]
1. 어느 알람이 발화했는지 확인 (커넥션 / failover / 로컬스토리지 / 재시작)
2. RDS 콘솔 → 이벤트 탭 → 최근 5분 이벤트

[커넥션 95% 인 경우]
3. 현재 커넥션 확인: SELECT * FROM performance_schema.processlist
4. 장시간 실행 쿼리 kill
5. 앱 커넥션 풀 설정 확인 (PG-10 도 함께 발화했는지 확인)
   → PG-10 도 발화했으면 앱이 커넥션을 반납하지 않는 상황

[failover 인 경우]
6. 자동 복구된다. 앱 재연결 확인 (보통 30~60초)
7. 2분 내 복구 안 되면 → 앱 재시작

[로컬 스토리지 고갈]
8. temp table 을 쓰는 쿼리 확인. 클러스터 볼륨과 별개다
9. 긴급: 인스턴스 재시작으로 로컬 스토리지 초기화

[에스컬레이션]
10. 10분 내 미복구 → <담당자>
```

## C-4. PG-04 — Redis 장애

```
[즉시]
1. 어느 알람인지 확인 (RejectedConnections / EngineCPU 99%)

[RejectedConnections]
2. 노드별 CurrConnections 확인
3. 앱의 Redis 커넥션 풀 설정 확인 — 풀 크기 × 파드 수 > 노드 한도?
4. 긴급: 파드 수 축소 또는 노드 타입 업그레이드

[EngineCPU 99%]
5. slowlog 확인 — KEYS, SMEMBERS 등 O(N) 명령 의심
   redis-cli SLOWLOG GET 10
6. 긴급: 해당 명령을 쓰는 서비스 스케일 다운

[영향 판단]
7. 세션 저장소인가? → 사용자 로그아웃 발생 중
8. 캐시 전용인가? → DB 폴백 부하 확인 (PG-03 도 발화했는지)

[에스컬레이션]
9. 15분 내 미복구 → <담당자>
```

## C-5. PG-05 — 용량 부족 (ECS / ASG)

```
[즉시]
1. running < desired 인가, ASG InService == 0 인가

[ECS]
2. ECS 콘솔 → 서비스 → 이벤트 탭
3. 배치 실패 이유 확인:
   RESOURCE:MEMORY / RESOURCE:CPU → 클러스터 용량 부족
   RESOURCE:FARGATE              → Fargate 쿼터
   CannotPullContainerError      → ECR / 네트워크
   task configuration failure    → Secrets / IAM

[우리가 할 수 있는 일]
4. 용량 부족: ASG 희망 용량 증가 또는 Fargate 로 전환
5. Fargate 쿼터: Service Quotas 에서 증설 요청 (즉시 반영 안 됨)
6. 이미지 pull 실패: ECR 권한 / VPC 엔드포인트 확인
7. 최악: 이전 태스크 정의로 롤백

[에스컬레이션]
8. 10분 내 미복구 → <담당자>
```

## C-6. PG-06 — ALB 타깃 전멸 / 인증서 임박

```
[HealthyHostCount == 0]
1. 타깃 그룹 → 타깃 상태 및 실패 이유 확인
2. 헬스체크 경로가 DB/Redis 를 검사하는가?
   → 그렇다면 PG-03 / PG-04 가 근본 원인. 그쪽 먼저
3. 태스크가 아예 없는가? → PG-05 확인
4. 태스크는 있는데 unhealthy? → 앱 로그 확인, 헬스체크 타임아웃 조정

[DaysToExpiry < 3]
5. ACM 콘솔 → 인증서 → 갱신 상태
6. DNS 검증 CNAME 이 살아있는지 확인 (가장 흔한 원인)
7. 수동 갱신 불가 시 → 새 인증서 발급 후 리스너 교체

[에스컬레이션]
8. 5분 내 미복구 → <담당자>  ← 전면 중단이므로 가장 짧게
```

## C-7. PG-07 — 5xx 급증

```
[즉시]
1. ELB 5xx 인가, Target 5xx 인가 확인 — 원인이 다르다

[ELB 5xx (502/503/504)]
2. 타깃이 커넥션을 거부/타임아웃. PG-06, PG-05 확인
3. 502: 앱이 잘못된 응답. 앱 크래시 의심
4. 503: 타깃 없음 → PG-05
5. 504: 타깃 응답 지연 → PG-03 / PG-04 / PG-10

[Target 5xx (앱이 반환)]
6. Datadog APM → trace.servlet.request → 에러 스팬 확인
7. 최근 배포 확인 → 롤백 판단
8. 특정 엔드포인트에 집중되어 있나? → 해당 기능 비활성 검토

[에스컬레이션]
9. 10분 내 미완화 → <담당자>
```

## C-8. PG-08 — SQS DLQ 적재

```
[즉시]
1. 어느 DLQ 인가 확인
2. 메시지 1건 peek (삭제하지 않고 조회)
   aws sqs receive-message --queue-url <dlq> --max-number-of-messages 1

[판단]
3. 특정 메시지만의 문제인가, 전체 처리 실패인가
4. 원본 큐의 ApproximateAgeOfOldestMessage 도 함께 확인

[우리가 할 수 있는 일]
5. 처리 로직 문제 → 원인 수정 후 redrive
   aws sqs start-message-move-task --source-arn <dlq-arn>
6. 데이터 문제 (파싱 불가 등) → 해당 메시지 격리 후 나머지 redrive
7. 외부 의존 문제 → PG-01 / PG-09 확인 후 복구 뒤 redrive

⚠️ 데이터 유실과 직결된다. 조사 전에 DLQ 메시지를 삭제하지 않는다.

[에스컬레이션]
8. 30분 내 판단 불가 → <담당자>
```

## C-9. PG-09 — 기관 연동 실패 (앱 계층)

```
[즉시]
1. 어느 기관인가, 어느 모니터인가 확인
   실패율 / 호출 침묵 / integration.status.issue

2. ⚠️ PG-01(VPN) 이 함께 발화했는가?
   → 발화했으면 C-1 로. 터널 문제다.
   → 발화하지 않았으면 터널은 정상. 아래 진행.

[터널은 정상인데 연동 실패 — 원인 후보]
3. 기관 API 인증 토큰/인증서 만료
   → 만료일 확인. 갱신 절차: <링크>
4. 기관 측 정기 점검
   → 기관 공지 확인: <링크>
5. 기관 측 응답 포맷 변경
   → 앱 로그에서 파싱 에러 확인
6. 기관 측 rate limit
   → 429 응답 여부, 최근 호출량 급증 확인

[우리가 할 수 있는 일]
7. 해당 기관 재시도 큐 정지 (C-1 4번과 동일)
8. CS 공지
9. 기관 담당자 연락 (C-1 6번)

[호출 침묵(#62)인 경우 — 추가 확인]
10. 우리 쪽이 호출을 아예 안 하고 있을 수 있다
    → 스케줄러 죽음? 큐 컨슈머 중단? 배포 사고?
    → tasks.scheduled.execution, executor.active 확인
```

## C-10. PG-10 — 리소스 포화 (앱 계층)

```
[즉시]
1. 어느 모니터인가 (커넥션 풀 대기 / 스레드 WAITING)

2. RDS 지표를 함께 확인
   CPU 15% + 커넥션 평시 + 데드락 0  → DB 는 정상
   → 앱이 커넥션을 쥐고 다른 것을 기다리는 상황

[전형적 원인]
3. 트랜잭션 안에서 외부 API 호출
   → PG-09 도 발화했는가? 기관 API 지연이 원인일 수 있다
4. jvm.threads.states{state:waiting} 값 확인
   → 급증했으면 스레드가 외부 응답 대기 중
5. Datadog APM → 느린 트레이스에서 span 확인
   → DB span 은 짧고 HTTP client span 이 긴가?

[우리가 할 수 있는 일]
6. 긴급: 외부 호출 타임아웃 단축 (설정 변경 후 재배포)
7. 긴급: 해당 기관 재시도 큐 정지 → 커넥션 압력 감소
8. 파드 수 증설은 커넥션 풀을 더 소진시킬 수 있다. 신중히
9. 커넥션 풀 크기 확인 — hikaricp.connections.max × 파드 수 vs RDS max_connections

[사후]
10. 트랜잭션 경계 밖으로 외부 호출을 빼는 리팩터링 티켓 생성
```

## C-11. PG-11 — 보안 위협

```
[즉시 — 5분 내]
1. 어느 이벤트인가 확인

[GuardDuty High/Critical]
2. GuardDuty 콘솔 → finding 상세 → 영향받은 리소스
3. 자격증명 침해 유형이면 → 해당 키/역할 즉시 무효화
4. EC2 침해 유형이면 → 해당 인스턴스 격리 (SG 를 격리용으로 교체)

[루트 계정 로그인 (#46)]
5. 본인/팀원의 정당한 로그인인가 즉시 확인 (슬랙 @here)
6. 아니면 → 루트 비밀번호 즉시 변경, MFA 확인, 세션 무효화

[루트 액세스 키 생성 (#48)]
7. 정당한 작업이 아니면 → 즉시 삭제
   ⚠️ 루트 액세스 키는 원칙적으로 존재해서는 안 된다

[CloudTrail 무력화 (#49b) / KMS 무력화 (#49c)]
8. ⚠️ 침해 진행 중 신호다. 공격자가 흔적을 지우고 있다
9. 즉시 에스컬레이션 — <보안 담당자> + <경영진>
10. CloudTrail 재활성화, KMS 삭제 예약 취소
11. 최근 24시간 CloudTrail 이벤트 전수 검토

[에스컬레이션]
12. 8~11 항목은 즉시 에스컬레이션. 혼자 판단하지 않는다
```

## C-12. PG-12 — 알럿 파이프라인 장애

```
⚠️ 이 알럿은 "알럿이 안 오고 있다" 는 뜻이다. 다른 장애가 숨어 있을 수 있다.

[판단 순서 — 이 순서를 지킨다]
1. 실제로 알럿이 안 오고 있는가?
   → Datadog Events Explorer 에서 최근 30분 이벤트 확인
   → 이벤트가 있으면 경로는 살아있다. 하트비트만 문제 → 3번으로

2. AWS 리전 장애인가?
   → us-east-1 의 aws.health 이벤트 확인 (PG-13)
   → https://health.aws.amazon.com/health/status
   → 리전 장애면 → 리전 장애 대응 절차로 (별도 문서)

3. EventBridge Scheduler 만 죽었는가?
   aws scheduler get-schedule --name heartbeat
   → 이것만 문제면 P3 로 강등. 아침에 처리
   → ⚠️ 8.3 에 명시된 "허용되는 오탐" 이다

4. SNS 배달 실패인가? (#51a)
   → NumberOfNotificationsFailed 확인
   → Datadog API 키 만료/로테이션 의심 → 구독 URL 갱신

5. 구독 DLQ 에 적재되었는가? (#51b)
   → 메시지 peek 해서 실패 원인 확인 (403/401/타임아웃)

6. 위 어느 것도 아니면
   → On-Call 스케줄이 비어 있을 가능성
   → Datadog On-Call → 스케줄 확인
   → 이 경우 200 OK 로 응답되므로 DLQ 에 안 잡힌다

[복구 후]
7. 알럿이 끊긴 구간에 놓친 장애가 있는지 확인
   → CloudWatch 알람 히스토리 (알람 상태는 기록된다)
   → aws cloudwatch describe-alarm-history --start-date <끊긴시각>
```

## C-13. PG-13 — AWS Health 진행 중 장애

```
[즉시]
1. EventBridge 이벤트 상세에서 영향 서비스·리전·리소스 확인
2. https://health.aws.amazon.com/health/status 확인

[판단]
3. 우리 리전(ap-northeast-2)인가?
4. 우리가 쓰는 서비스인가?
5. 영향받는 리소스 ID 가 명시되어 있는가?

[우리가 할 수 있는 일]
6. AZ 단위 장애면 → 다른 AZ 로 트래픽 이동 (ASG/ECS 재배치)
7. 서비스 단위 장애면 → 해당 기능 degrade 모드로 전환
8. CS 공지 (AWS 장애임을 명시)
9. AWS 복구를 기다리는 것 외에 할 일이 없으면 → 상황 공유 후 대기

[중요]
10. 이 알럿이 발화하면 다른 모든 P1 이 억제된다 (Layer 0)
    → 억제된 알람 목록을 확인해서 우리 문제가 섞여 있지 않은지 검토
    aws cloudwatch describe-alarms --state-value ALARM \
      --query "MetricAlarms[].AlarmName"
```

## C-14. 런북 템플릿 (신규 P1 추가 시)

```markdown
## PG-nn — <제목>

[즉시]
1. <무엇이 발화했는지 특정하는 방법>
2. <상위 레이어 알람이 함께 발화했는지 확인 — 근본 원인 판별>

[판단]
3. <원인 후보 2~4개와 각각의 확인 방법>

[우리가 할 수 있는 일]      ← 이 섹션이 비면 P1 자격이 없다 (3.6 / D9)
4. <긴급 완화>
5. <영향 축소>
6. <외부 연락 필요 시 연락처>

[에스컬레이션]
7. <N분> 내 미복구 → <담당자>

[사후]
8. <재발 방지 티켓 생성 기준>
```
