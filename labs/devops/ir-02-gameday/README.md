# ir-02-gameday: 장애를 일으키고 타임라인과 사후 분석을 남긴다

장애 대응 시리즈 실습-2 의 코드. 작은 주문 서비스 앞의 재고 경로에 Toxiproxy 로 지연을 넣고,
경고 → 운영 절차서대로 진단·완화 → 원인 제거 → 복구를 실제로 진행한다. 명령마다 시각을 남기고,
그 기록과 Prometheus·Alertmanager 기록을 합쳐 타임라인을 자동으로 만든 뒤 사후 분석 문서를 쓴다.

## 구성

```
load(초당 20건) → order ──(Toxiproxy :28666)──→ inventory
                    │ fallback 스위치(재고 확인 보류)
Prometheus(스크레이프 5s, 규칙 평가 10s) → Alertmanager(group_wait 30s, group_interval 5m) → webhook(raw/ 에 기록)
Grafana: 주문 게임데이 대시보드(사건 주석 포함)
```

| 경로 | 내용 |
|---|---|
| `app/service.py` | 표준 라이브러리만 쓴 파이썬 서비스. `ROLE=order` 는 재고를 묻고(타임아웃 1초), `ROLE=inventory` 는 바로 답한다. `/metrics` 를 직접 낸다 |
| `load/load.py` | 일정 속도 부하기 (`RATE`, 기본 20) |
| `prometheus/rules.yml` | `OrderErrorRatioHigh`(실패율 > 5%, for 1m, page), `OrderLatencyHigh`(p99 > 500ms, for 2m, ticket). 둘 다 `summary`, `runbook_url` 주석 |
| `alertmanager/alertmanager.yml` | 라우팅 하나. 기본값(30s / 5m / 4h)을 일부러 그대로 적었다 |
| `webhook/receiver.py` | 받은 알림을 `raw/notifications.jsonl` 에 쌓는다 |
| `RUNBOOK.md` | 두 경고의 운영 절차서. 경고의 `runbook_url` 이 가리킨다 |
| `scripts/gd.py` | 게임데이 도구: `event`, `inject`, `heal`, `fallback on/off`, `diag`, `wait`, `settle`. 명령 시각을 `raw/events.jsonl` 과 Grafana 주석에 남긴다 |
| `scripts/timeline.py` | 한 실행의 타임라인과 TTD/TTM/TTR 을 `results/<run>/` 에 쓴다(시각은 주입 기준 상대 시간) |
| `scripts/ttd-trials.sh`, `scripts/summarize-trials.py` | 같은 장애를 N번 주입해 탐지 시간이 얼마나 흔들리는지 잰다 |
| `scripts/toxi-remove-repro.py` | 지연 독을 걸고 걷을 때 Toxiproxy 경로가 멈추는지 되풀이한다 |
| `postmortem.md` | `run-1` 의 실제 타임라인으로 쓴 사후 분석 |
| `results/` | 커밋하는 원자료. `raw/` 는 유닉스 시각이 들어 있어 커밋하지 않는다(.gitignore) |

## 버전

| 구성 요소 | 버전 | 메모 |
|---|---|---|
| Prometheus | 3.15.0 | 저장소의 다른 실습과 같은 버전 |
| Alertmanager | 0.34.1 | 2026-09 최신 안정판 |
| Toxiproxy | 2.12.0 | 2025-03 릴리스, 이후 안정판 없음 |
| Grafana | 13.2.3 | 익명 Admin |
| Python | 3.13 (alpine) | 서비스, 부하기, 웹훅. 호스트 스크립트는 3.9 이상 표준 라이브러리만 |

## 돌리는 법

포트는 28000번대만 쓴다(order 28080, Prometheus 28090, Alertmanager 28093, Grafana 28030, Toxiproxy API 28474).

```bash
cd labs/devops/ir-02-gameday
mkdir -p raw                                  # 웹훅 기록 자리. 없으면 Linux 에서 Docker 가 root 로 만들어 쓸 수 없다
docker compose up -d
sleep 60                                      # 1분 창이 찰 때까지
python3 scripts/gd.py diag                    # 평상시 값 확인

# 게임데이 한 번 (run-1 과 같은 순서, 이벤트 문구도 그대로. 끝의 settle 은 run-1 뒤에 만든 명령이다.
# run-1 에서는 resolved 알림 두 개가 다 온 뒤 timeline.py 를 다시 돌려 같은 결과를 얻었다)
python3 scripts/gd.py event start run-1
sleep 30
python3 scripts/gd.py inject 900 300          # 재고 경로 600~1200ms
python3 scripts/gd.py wait OrderErrorRatioHigh firing
python3 scripts/gd.py event declare "OrderErrorRatioHigh page 수신. 장애 선언, IC 겸 운영 담당 1인"
python3 scripts/gd.py diag
python3 scripts/gd.py event decide "절차서 2단계 표 1행: 재고 서버는 5ms인데 order가 본 호출은 1.5s. 가는 길이 느림 → 3-A 완화"
python3 scripts/gd.py fallback on
python3 scripts/gd.py event comms "[조사 중] 주문 일부가 실패하고 있습니다. 재고 확인을 보류하는 완화를 적용했고, 주문은 '확인 보류' 상태로 접수됩니다. 다음 공지 15분 뒤."
sleep 75 && python3 scripts/gd.py diag
python3 scripts/gd.py event note "완화 후 재고 호출이 0건이라 절차서 5단계의 'order가 본 재고 호출 p99' 를 볼 수 없음. 경로를 직접 찔러 확인하기로"
# 원인 제거 + 경로 직접 확인 (아래 "경로 직접 확인" 명령)
python3 scripts/gd.py fallback off
sleep 90 && python3 scripts/gd.py diag
python3 scripts/gd.py event resolved "fallback 끄고 90초간 실패율 0. 정상 경로 복귀"
python3 scripts/gd.py settle                  # 울린 경고가 모두 resolved 알림을 받을 때까지 (run-1 은 주입 뒤 약 7분 44초)
python3 scripts/timeline.py run-1             # results/run-1/timeline.md

# 같은 장애 반복 (회당 약 8분: 주입부터 page 까지 약 2분, resolved 알림까지 group_interval 5분). 이번엔 결과를 버렸다(아래 함정)
caffeinate -dimsu ./scripts/ttd-trials.sh 6 rep
python3 scripts/summarize-trials.py rep 6     # results/trials-summary.md

docker compose down -v
```

### 경로 직접 확인 (fallback 중에는 재고 호출 지표가 비므로, run-1 에서 친 그대로)

```bash
python3 scripts/gd.py heal && docker compose exec -T order python -c "
import urllib.request,time
r=[]
for i in range(10):
    t=time.time(); urllib.request.urlopen('http://toxiproxy:28666/stock/A',timeout=3).read(); r.append(round((time.time()-t)*1000,1))
print('경로 직접 호출 10건(ms):',r)" | tee /dev/stderr | xargs -0 python3 scripts/gd.py event probe
```

Grafana: http://localhost:28030/d/gameday (빨간 점선이 `gd.py` 가 남긴 사건)

## 돌리다 만난 함정

- **첫 주입에서 Toxiproxy 가 멈췄다.** 독을 거는 API 호출이 10초 동안 응답하지 않았고, 그 뒤 독 목록은 비어 있는데 프록시 경유 경로만 5초 타임아웃이 났다(재고 직접 호출은 7ms). `docker compose restart toxiproxy` 로 풀렸다. 같은 조건으로 독 추가·삭제를 되풀이한 3회(`results/toxiproxy-remove/delete.jsonl`)와 이후 게임데이 실행에서는 다시 나지 않았다. Toxiproxy 의 열린 이슈 #558, #428 과 같은 계열의 증상이다. 기록은 `results/toxiproxy-remove/first-incident.md`.
- **완화를 켜면 진단 지표가 사라진다.** fallback 중에는 주문이 재고를 부르지 않아 재고 호출 지표가 비어 있다. 원인 제거를 확인하려면 경로를 직접 불러야 한다(`postmortem.md` 조치 항목 1).
- **resolved 알림은 `group_interval` 타이머를 따른다.** 실패율 경고가 끝난 시각(endsAt)보다 resolved 수신이 3분 51초 늦었다(run-1). 복구 시각은 알림 수신이 아니라 `ALERTS` 시계열과 503 카운터로 잰다.
- **resolved 알림의 `summary` 에는 마지막으로 참이었던 평가의 값이 남는다.** Prometheus `rules/alerting.go` 는 경고 식이 참일 때만 주석을 다시 계산한다.
- **`urllib` 의 timeout 은 요청 전체가 아니라 소켓 동작마다 걸린다.** 타임아웃 1초인데 1초 넘게 걸리고도 성공한 응답이 많았다.
- **p99 1.489s 는 버킷 보간값이다.** 주문 응답은 1.0~1.5초 버킷에 몰려 있었고 1.5초를 넘은 건 0건이었다.
- **호스트(또는 Docker VM)가 멈추면 실행 전체를 버린다.** 반복 주입(`ttd-trials.sh`)은 두 번 시도했고 둘 다 버렸다. 노트북 덮개가 닫힌 채 배터리로 돌아 `caffeinate` 를 걸어도 시스템이 잠들었다. 첫 세트는 세 번째 회차에서 스크레이프가 기대 460개 중 92개만 남았고, 두 번째 세트는 resolved 알림이 오지 않거나(그래서 `settle` 에 8분 제한과 Alertmanager 재생성을 넣었다) page 가 10분 안에 오지 않았다. 주입부터 page 까지는 온전했던 두 회차도 그 뒤 시계가 몇 분씩 건너뛰어 함께 버렸다. 그래서 커밋한 숫자는 `run-1` 하나다. 반복 측정은 전원 연결 상태에서 `pmset -g batt`, `ioreg -r -k AppleClamshellState -d 4 | grep AppleClamshellState` 로 확인한 뒤 다시 돌린다. `timeline.py` 는 실행마다 스크레이프 수, 부하 최저치, 탐지 구간 스크레이프 수를 적으니 그 줄부터 본다.
- 처음엔 실패율 기록 규칙이 5xx 가 하나도 없을 때 값 없음이 됐다. 분자에 `or vector(0)` 을 붙였다.
- 컨테이너에 고정 이름을 주지 않았으니 compose 프로젝트 이름(`ir-02-gameday`)으로 찾는다.
