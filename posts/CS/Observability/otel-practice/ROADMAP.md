# OpenTelemetry 운영 실습

실제 작은 서비스·관측 스택·실행 출력·화면 캡처를 포함한 네 편이다. 티스토리에 비공개 업로드했다. [실행 안내](../../../../labs/observability/otel-practice/README.md)와 각 실습의 원자료를 함께 읽는다.

| 편 | 글 | 실습 |
|---|---|---|
| 1 | [Collector가 받았다고 한 스팬은 정말 저장됐을까](01_1편%20-%20Collector가%20받았다고%20한%20스팬은%20정말%20저장됐을까.html) | `collector-loss` |
| 2 | [에러 트레이스만 남기면 장애를 놓치지 않을까](02_2편%20-%20에러%20트레이스만%20남기면%20장애를%20놓치지%20않을까.html) | `tail-sampling` |
| 3 | [Java agent와 Micrometer Tracing을 같이 켜면 어떻게 될까](03_3편%20-%20Java%20agent와%20Micrometer%20Tracing을%20같이%20켜면%20어떻게%20될까.html) | `dual-instrumentation` |
| 4 | [Collector에서 지운 개인정보는 어디까지 사라졌을까](04_4편%20-%20Collector에서%20지운%20개인정보는%20어디까지%20사라졌을까.html) | `sensitive-data` |

시리즈 접두어는 `OpenTelemetry 운영 실습`, 카테고리는 `Observability/OpenTelemetry`다. 기존 `otel/`의 구조·설계 읽기와 분리하며 기존 글 경로와 매니페스트 항목은 유지하고 새 네 편의 업로드 결과를 추가했다.

실행 결과와 캡처는 동일 실행의 증거로 묶어 둔다. 이미지 9개는 먼저 GitHub에 push했고 글은 해당 고정 커밋의 jsDelivr URL을 사용한다. 이미지 URL을 제외한 본문은 독립 감사 때와 같다. 업로드·이미지 접근 검증은 [발행 기록](../../../../labs/observability/otel-practice/validation/publication.json)에 남겼다.

티스토리 비공개 글: [1편](https://dding-shark.tistory.com/700), [2편](https://dding-shark.tistory.com/701), [3편](https://dding-shark.tistory.com/702), [4편](https://dding-shark.tistory.com/703). 소유자 로그인 상태에서 확인할 수 있다.

## 후속 글감: 배포를 관측하고 실험을 판정하기

사용자가 후속 진행을 요청해 [배포 관측과 A/B 실험](../../DevOps/deployment-experiments/ROADMAP.md)으로 착수했다. 아래는 착수 때 정한 요구사항이며, 구현·검수 결과는 해당 시리즈에 기록한다.

- 『SRE를 위한 마이크로서비스』와 연결해 Netflix 계열 도구를 직접 사용하는 배포 시각화: Spinnaker, Kayenta, 메트릭 파이프라인 후보 Atlas/Spectator. 실제 실행 가능 버전·구성은 착수할 때 공식 문서로 확인한다.
- 카나리 화면은 **A / A′ / B** 세 집단으로 구성한다. A는 기존 운영본, A′는 A와 같은 버전·설정을 새로 배포한 베이스라인, B는 변경 버전이다. A′와 B의 생성 시점·자원·워밍업·부하 조건을 맞추고 같은 관측 구간에서 비교한다. A와 A′는 재배포에 따른 차이를 확인하는 데 사용한다. 그래프에는 버전과 집단을 모두 표시한다.
- 기존 `delivery-safety` 실습은 Kayenta 분류기를 Python으로 옮긴 판정 서버다. 후속에서는 실제 Kayenta의 분석 결과와 Spinnaker 파이프라인 화면을 연결하는 것을 목표로 삼는다.
- 배포 안전성 판정과 기능 A/B 실험을 구분한다. 기능 실험은 사용자 할당 유지, 노출 이벤트와 전환의 분모, 표본 부족, 할당 비율 이상, 에러·지연 가드레일을 다룬다. 샘플링한 트레이스 수를 사용자 수나 전환율의 분모로 쓰지 않는다. 모의 전환 데이터는 방법 검증으로 한정한다.

세 그룹을 설명하는 공개 근거: [Netflix의 Kayenta 소개](https://medium.com/netflix-techblog/automated-canary-analysis-at-netflix-with-kayenta-3260bc7acc69). 이는 공개된 당시 설계의 근거이며 현재 Netflix 내부 운영 전체를 재현했다는 뜻은 아니다.

### 실제로 연결한 후속 실습

후속 세 편과 실제 화면 8장을 작성했다. 공식 Spinnaker Deck·Gate·Kayenta·Front50와 Prometheus·Grafana를 실행해 새 A′와 B를 비교했다. 같은 v1은 Kayenta Pass100, 지연40ms를 주입한 B는 Fail0으로 판정됐다. A의 프로세스 나이·캐시와 A′/B의 재시작도 Grafana에서 확인했다. Atlas/Spectator는 이번 구성에 추가하지 않았다.

실제 Deck 화면은 Kayenta 분석 보고서다. 복제본 재생성은 Compose 실행기가 담당하고, 분석 단계는 Kayenta 내장 Orca가 실행했다. 외부 Spinnaker 배포 파이프라인·트래픽 승격·자동 롤백은 구현하지 않았다. 사용자 고정 할당과 노출·전환, 고정 표본 판정은 별도 두 실습으로 확인했다. 합성 데이터의 숫자를 운영 배포 안전성이나 제품 효과의 증명으로 확대하지 않는다.
