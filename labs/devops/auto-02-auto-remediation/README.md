# auto-02-auto-remediation: 경고를 받아 스스로 고치는 스크립트에 상한을 건다

운영 자동화 시리즈 실습-2 의 코드. 가동 시간에 비례해 나빠지는 장애(누수)를 일으키고,
경고 웹훅을 받아 app 을 재시작하는 자동 복구기를 두 모드로 돌려 차이를 센다.

| 모드 | 동작 |
|---|---|
| `MODE=unbounded` | 새 경고(같은 fingerprint + startsAt 은 한 번)마다 재시작. 횟수 제한 없음 |
| `MODE=capped` | 같은 일을 하되 `WINDOW_S`(1800초) 안에서 `MAX_ACTIONS`(3)번까지만. 그 뒤 다시 울리면 `escalate` 를 한 번 남기고 멈춘다 |

`RUNBOOK.md` 는 경고의 `runbook_url` 이 가리키는 실습 소품(사람이 불렸을 때 볼 절차서)이다.

## 구성

```
load(초당 20건) → app ← Prometheus(스크레이프 5s, 평가 5s) → Alertmanager → remediator(웹훅)
                   ↑                                                      │ POST /admin/restart
                   └──────────────────────────────────────────────────────┘
app 은 /admin/restart 를 받으면 종료하고, restart: always 로 Docker 가 다시 띄운다.
장애 원인(state/leak 파일)은 볼륨에 있어서 재시작해도 남는다.
```

- app: `state/leak` 가 있으면 가동 45초(`GRACE_S`) 뒤부터 15초(`RAMP_S`)에 걸쳐 실패 확률 0 → 100%
- 경고 `AppErrorRatioHigh`: `app:error_ratio:30s > 0.05` 가 15초(`for`) 이어지면 firing
- Alertmanager: `alertmanager/alertmanager.yml` 은 실험용으로 줄인 간격(group_wait 5s, group_interval 30s, repeat_interval 1m).
  `alertmanager/alertmanager.default.yml` 은 기본값(30s, 5m, 4h)
- remediator 의 "효과 확인"(`EFFECT_S`, 직전 조치 600초 안에 재발하면 `no_effect`)은 **기록만 한다.** 상한 판단에는 쓰지 않는다.
  대상이 app 하나뿐이라 "범위 상한"은 구현하지 않았다

## 돌리는 법

포트는 36100번대만 쓴다(app 36180, Prometheus 36190, Alertmanager 36193).

```bash
cd labs/devops/auto-02-auto-remediation
./scripts/run.sh unbounded 600 unbounded
HUMAN_DELAY=120 ./scripts/run.sh capped 600 capped
AM_CONF=alertmanager.default.yml ./scripts/run.sh unbounded 600 unbounded-amdefault
python3 scripts/analyze.py out/unbounded        # → results/unbounded/summary.md (다른 둘도 같은 식)
docker compose down -v
```

- `run.sh <모드> <장애 지속 초> [결과 이름]`: 스택을 새로 띄우고 75초 기준 구간 뒤 `state/leak` 를 만든다(이때 app 가동 시간이 이미 60초를 넘어 실패율이 곧바로 100%).
  지속 시간이 끝나면 ALERTS, 실패율 기록 규칙, remediator 기록, 부하 결과, app 로그를 `out/<결과 이름>/` 에 모은다
- `HUMAN_DELAY=초`: `escalate` 가 찍히고 이만큼 뒤에 사람 대신 `state/leak` 를 지운다(RUNBOOK 3단계). 없으면 아무도 오지 않는다
- `AM_CONF=파일 이름`: Alertmanager 설정 파일을 고른다
- 필요한 것: Docker, Python 3, curl. 이미지: `python:3.13-alpine`, `prom/prometheus:v3.15.0`, `prom/alertmanager:v0.34.1`

`out/` 에는 유닉스 시각이 들어 있어 커밋하지 않는다. `results/*/summary.md` 는 장애 시작 기준 상대 초만 남긴다(경고 `startsAt` 은 원문 그대로).

## 결과 (2026-10-16, Docker Desktop 29.5.3, Apple M5 Pro, 전원 연결, 실행 중 호스트 정지 0회)

장애 지속 600초, 초당 20건(요청 약 12,000건). 실패에는 500 응답과 재시작 중 연결 오류(실행마다 6~40건)가 함께 들어 있다.

| 실행 | 재시작 | 간격(초) | 사람 호출 | 실패 | 경고가 꺼져 있던 시간 |
|---|---|---|---|---|---|
| unbounded (줄인 간격) | 8번 | 75~80 | 없음 | 4,012 (33.4%) | 359초 / 599초 |
| capped (줄인 간격, 사람 120초 뒤 도착) | 3번 | 80, 80 | T+266.2 | 4,565 (호출 전 2,158, 호출~조치 2,407, 조치 뒤 0) | 171초 / 385초(원인 제거까지) |
| unbounded (Alertmanager 기본값) | 1번 | - | 없음 | 10,956 (91.3%) | 68초 / 599초 |

- 줄인 간격에서는 매 순환마다 resolved 알림이 다음 firing 보다 먼저 나가서, 새 firing 이 새 알림이 됐다(알림 16건 = firing 8 + resolved 8)
- 기본값에서는 T+52.9 첫 알림 뒤로 알림이 한 건도 오지 않았다. 경고는 T+123 부터 끝까지 firing 이었다.
  첫 순환의 해결과 재발 사이에 group_interval(5분) 틱이 없어서 resolved 가 나가지 못했고, Alertmanager 는 같은 라벨의 경고가 계속 울리는 것으로 보고 repeat_interval(4h)까지 다시 보내지 않는다(`notify/dedup_stage.go` 의 `needsUpdate`, 경고 해시는 라벨만으로 만든다)
- capped 의 반복 알림(`repeat_interval: 1m`)은 firing 뒤 90초에 왔다. 반복 여부는 group_interval(30초) 틱에서만 보고, 비교 기준 "지금"은 틱 시각(`dispatch.go` 의 `notify.WithNow(ctx, now)`)이고 마지막 전송 시각은 보낸 뒤 `nflog.Log` 가 `l.now()` 로 기록하므로, 60초 틱에서는 `entry.Timestamp.AsTime().Before(now.Add(-repeat))` 가 아직 거짓이다

## 돌리다 만난 함정

- **Prometheus 3 가 app 을 스크레이프하지 못했다.** 처음 실행에서 경고가 10분 동안 한 번도 울리지 않았다. 타깃 상태가 `down`, 오류는
  `non-compliant scrape target sending blank Content-Type and no fallback_scrape_protocol specified for target`.
  app 의 응답에 `Content-Type: text/plain; version=0.0.4` 를 붙여 고쳤다. 그 실행은 버렸다
